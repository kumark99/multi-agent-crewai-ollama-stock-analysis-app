import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from config import settings
from crew import StockAnalysisCrew


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.reports_dir, exist_ok=True)
    yield


app = FastAPI(
    title="Stock Analysis Multi-Agent API",
    description="CrewAI-powered multi-agent stock analysis with local LLMs via Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Connection Manager ───────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, session_id: str):
        await ws.accept()
        self.active[session_id] = ws

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(session_id)


manager = ConnectionManager()


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Stock Analysis Multi-Agent API"}


@app.get("/api/models")
async def get_models(base_url: str = settings.ollama_base_url):
    """Fetch available models from the Ollama instance."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models, "connected": True}
    except Exception:
        return {
            "models": ["llama3.2", "llama3.1", "mistral", "gemma2", "codellama"],
            "connected": False,
            "error": f"Cannot reach Ollama at {base_url}",
        }


@app.get("/api/report/{session_id}")
async def download_report(session_id: str):
    """Download the generated PDF report."""
    path = os.path.join(settings.reports_dir, f"{session_id}_report.pdf")
    if os.path.exists(path):
        return FileResponse(
            path,
            media_type="application/pdf",
            filename="stock_analysis_report.pdf",
            headers={"Content-Disposition": "attachment; filename=stock_analysis_report.pdf"},
        )
    return JSONResponse(status_code=404, content={"error": "Report not found"})


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            raw = await websocket.receive_text()
            request = json.loads(raw)

            symbol = request.get("symbol", "").strip().upper()
            llm_model = request.get("llm_model", settings.default_llm_model)
            ollama_base_url = request.get("ollama_base_url", settings.ollama_base_url)

            if not symbol:
                await manager.send(session_id, {"type": "error", "message": "Stock symbol is required"})
                continue

            async def send_update(event: dict):
                await manager.send(session_id, event)

            crew = StockAnalysisCrew(
                symbol=symbol,
                llm_model=llm_model,
                ollama_base_url=ollama_base_url,
                session_id=session_id,
                update_callback=send_update,
            )

            await crew.run()

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send(session_id, {"type": "error", "message": str(e)})
        manager.disconnect(session_id)

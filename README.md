# 🤖 StockMind AI – CrewAI Multi-Agent Stock Analysis System

> **AI-powered stock analysis with local LLMs via Ollama** — 3 specialised CrewAI agents working in
> concert to deliver institutional-grade fundamental analysis, technical analysis, news research, and
> a downloadable PDF investment report.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [How It Works](#how-it-works)
- [Agent Pipeline](#agent-pipeline)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Windows Setup](#windows-setup)
- [What's New](#whats-new)
- [Troubleshooting](#troubleshooting)

---

## Overview

**StockMind AI** is a full-stack AI application that orchestrates **3 specialised CrewAI agents** to
produce a comprehensive stock analysis report. All LLM inference runs **100% locally** using
[Ollama](https://ollama.ai/) — no API keys, no cloud costs, full privacy.

Enter any stock ticker (US or Indian markets), select your preferred local LLM model, and watch the
agents collaborate in real time to produce a professional PDF report.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STOCKMIND AI ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────┐    WebSocket     ┌──────────────────────────────────────┐
  │                  │◄────────────────►│            FastAPI Backend            │
  │   React Frontend │                  │                                      │
  │   (Bootstrap 5)  │    REST API      │  ┌────────────────────────────────┐  │
  │                  │◄────────────────►│  │        CrewAI Orchestrator      │  │
  │  ┌────────────┐  │                  │  │                                │  │
  │  │ LLM Config │  │                  │  │  ┌──────────────────────────┐  │  │
  │  └────────────┘  │                  │  │  │  Agent 1: Stock Analyst  │  │  │
  │  ┌────────────┐  │                  │  │  │  • Fundamental Analysis  │  │  │
  │  │ Stock Input│  │                  │  │  │  • Technical Indicators  │  │  │
  │  └────────────┘  │                  │  │  └──────────┬───────────────┘  │  │
  │  ┌────────────┐  │                  │  │             │                  │  │
  │  │ Agent Flow │  │                  │  │  ┌──────────▼───────────────┐  │  │
  │  │  Diagram   │  │  Real-time       │  │  │ Agent 2: News Researcher │  │  │
  │  └────────────┘  │  Events via      │  │  │  • Latest News Articles  │  │  │
  │  ┌────────────┐  │  WebSocket       │  │  │  • Market Sentiment      │  │  │
  │  │ Activity   │  │                  │  │  └──────────┬───────────────┘  │  │
  │  │    Log     │  │                  │  │             │                  │  │
  │  └────────────┘  │                  │  │  ┌──────────▼───────────────┐  │  │
  │  ┌────────────┐  │                  │  │  │ Agent 3: Inv. Strategist │  │  │
  │  │PDF Download│  │                  │  │  │  • Report Synthesis      │  │  │
  │  └────────────┘  │                  │  │  │  • Recommendations       │  │  │
  └──────────────────┘                  │  │  └──────────┬───────────────┘  │  │
                                        │  └─────────────┼──────────────────┘  │
                                        │                │                      │
                                        │  ┌─────────────▼──────────────────┐  │
                                        │  │       PDF Generator             │  │
                                        │  │     (ReportLab)                 │  │
                                        │  └────────────────────────────────┘  │
                                        └──────────────────────────────────────┘
                                                         │
                                        ┌────────────────▼─────────────────────┐
                                        │            Ollama Server              │
                                        │   llama3.2 / mistral / gemma2 / ...  │
                                        └──────────────────────────────────────┘

  Tools Used by Agents:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Agent 1 Tools        │  Agent 2 Tools         │  Agent 3 Tools        │
  │  • yfinance 1.2.x     │  • Zerodha Pulse (.NS) │  • (none – uses       │
  │  • ta 0.11.0          │  • DuckDuckGo News     │    context from       │
  │  • TTL cache 5 min    │  • yfinance sentiment  │    Agents 1 & 2)     │
  └─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (Stock Symbol)
        │
        ▼
FastAPI WebSocket ──► CrewAI Crew (sequential process)
        │                    │
        │                    ├─► Task 1: Fundamental + Technical Analysis
        │                    │         └─► Tools: StockDataTool, TechnicalAnalysisTool
        │                    │
        │                    ├─► Task 2: News & Sentiment Research
        │                    │         └─► Tools: StockNewsTool, MarketSentimentTool
        │                    │
        │                    └─► Task 3: Investment Report Generation
        │                              └─► Context: Tasks 1 & 2 outputs
        │
        ▼
PDF Generation (ReportLab) ──► /reports/{session_id}_report.pdf
        │
        ▼
WebSocket Event ──► Frontend ──► Download Button
```

---

## Features

### 🤖 Multi-Agent System
- **3 specialised CrewAI agents** working sequentially
- **Dynamic LLM selection** – switch between any Ollama model at runtime
- **Real-time streaming** – watch agent activities as they happen

### 📊 Stock Analysis
- **Fundamental Analysis**: P/E, PEG, P/B, EV/EBITDA, ROE, ROA, margins, debt/equity, FCF
- **Technical Analysis**: RSI, MACD, Bollinger Bands, SMA/EMA (20/50/200), ATR, Stochastic
- **Volume Analysis**: current vs. 20-day average, volume ratio
- **Performance**: 1W/1M/3M/6M/YTD returns
- **Analyst Consensus**: target prices, recommendations

### 📰 News Intelligence
- **Indian stocks (`.NS` / `.BO`)** — [Zerodha Pulse](https://pulse.zerodha.com/) scraper with 50+ NSE ticker aliases; auto-falls back to DuckDuckGo with Indian-context queries if no results
- **Global stocks** — DuckDuckGo News API with targeted search queries
- Analyst upgrades/downgrades detection
- Market sentiment scoring (region-aware: Moneycontrol / ET / NDTV Profit for Indian stocks)
- Catalyst identification (positive/negative)

### 📄 PDF Report
- **Professional institutional-grade** PDF with cover page
- **Key Metrics Banner** — Current Price, Day Change %, Market Cap, P/E TTM, 52-Week High/Low (sourced from Agent 1 cache — zero extra network cost)
- Recommendation badge (BUY / HOLD / SELL)
- All analysis sections clearly formatted
- Risk factors with severity ratings
- Bull/Bear case breakdown
- Price targets (base/bull/bear)
- Disclaimer

### 🖥️ Professional UI
- Dark theme with purple/teal gradient aesthetic
- Animated agent flow diagram with real-time status
- Live activity log with typed messages
- One-click PDF download
- Popular stocks quick-pick

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn      |
| **AI**      | CrewAI 0.80+, Ollama (local LLMs)   |
| **Data**    | yfinance ≥1.0.0 (1.2.x), ta 0.11.0, numpy ≥2.1.0, pandas ≥2.2.3   |
| **News**    | duckduckgo-search 6.3.7, beautifulsoup4 ≥4.12.0 (Zerodha Pulse)    |
| **PDF**     | ReportLab                           |
| **Frontend**| React 18, Bootstrap 5.3             |
| **Comms**   | WebSocket (native), REST API        |
| **Fonts**   | Inter, JetBrains Mono               |

---

## Prerequisites

Before you begin, ensure you have:

| Requirement   | Version         | Notes                                                                  |
|---------------|-----------------|------------------------------------------------------------------------|
| Python        | 3.11+ (3.13 ✓)  | numpy ≥2.1.0 required for Python 3.13; add to PATH on Windows          |
| Node.js       | 18+             | Frontend build; add to PATH on Windows                                 |
| npm           | 9+              | Bundled with Node.js                                                   |
| Ollama        | Latest          | [ollama.com/download](https://ollama.com/download) — Win/macOS/Linux  |
| Git           | Any             | Clone the repository                                                   |

> **Windows users**: During Python and Node.js installation, check **"Add to PATH"**.
> Open a **new** terminal and verify: `python --version` and `node --version`.

---

## Installation

### 1. Clone / Navigate to the project

```bash
cd crewai-multiagent-ollama
```

### 2. Install and start Ollama

**macOS / Linux**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows**
Download and run the installer: [https://ollama.com/download/windows](https://ollama.com/download/windows)
Ollama registers as a **Windows background service** — starts automatically at login.

```bash
# Pull a model — same command on all platforms
ollama pull llama3.2          # Recommended – fast & capable
ollama pull llama3.1          # Larger, more capable
ollama pull mistral           # Great alternative
ollama pull gemma2            # Google's model
ollama pull phi3              # Microsoft's compact model

# Start server (macOS / Linux only — Windows runs Ollama as a service automatically)
ollama serve
```

### 3. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate — macOS / Linux
source venv/bin/activate

# Activate — Windows (Command Prompt)
# venv\Scripts\activate

# Activate — Windows (PowerShell)
# venv\Scripts\Activate.ps1
# First-time only — if blocked by execution policy:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env if needed (default settings work for local Ollama)
```

### 4. Frontend setup

```bash
cd frontend

# Install dependencies
npm install
```

---

## Running the Application

### Terminal 1 – Start Ollama (if not already running)

**macOS / Linux**
```bash
ollama serve
```

**Windows** — Ollama runs as a background service; no manual start needed.
To verify it is running:
```cmd
ollama list
```

### Terminal 2 – Start Backend

**macOS / Linux**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows (Command Prompt)**
```cmd
cd backend
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows (PowerShell)**
```powershell
cd backend
venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Terminal 3 – Start Frontend

```bash
# macOS / Linux / Windows — same command
cd frontend
npm start
```

Frontend will open at: `http://localhost:3000`

---

## How It Works

### Step-by-Step Flow

```
1. User opens http://localhost:3000
2. Configure LLM: select Ollama URL and model
3. Enter stock ticker (e.g., AAPL, TSLA, TCS.NS)
4. Click "Analyse" button
5. Browser opens WebSocket to /ws/{session_id}
6. Backend creates StockAnalysisCrew and runs it in a thread pool
7. Agent 1 fetches fundamental + technical data via yfinance & ta
8. Real-time events stream to UI (tool calls, thinking, completions)
9. Agent 2 searches for latest news + analyst sentiment
10. Agent 3 synthesises everything into a comprehensive report
11. Backend generates PDF using ReportLab
12. Frontend receives pdf_url and shows download button
```

---

## Agent Pipeline

### 🟣 Agent 1 – Senior Stock Market Analyst

**Role**: Fundamental & Technical Analysis

**Tools**:
- `Get Stock Fundamental Data` — yfinance 1.2.x: P/E, PEG, P/B, EV/EBITDA, revenue, margins, ROE, ROA, D/E, beta, analyst targets; **5-minute TTL cache**
- `Get Technical Analysis Indicators` — ta 0.11.0: RSI(14), MACD(12/26/9), Bollinger Bands(20/2σ), SMA-20/50/200, EMA-20, Stochastic, ATR(14); **5-minute TTL cache** on OHLCV data
- `max_iter`: **8** (graceful exit with best partial output if limit reached)

**Output**: Structured report with fundamental score (1–10) and technical score (1–10)

### 🟡 Agent 2 – Financial News Researcher & Sentiment Analyst

**Role**: News Research & Market Sentiment

**Tools**:
- `Get Stock News` — smart routing by exchange suffix:
  - 🇮🇳 **Indian (`.NS` / `.BO`)** → [Zerodha Pulse](https://pulse.zerodha.com/) (BeautifulSoup4 HTML scraper, 50+ NSE ticker aliases, SSL fallback); auto-falls back to DuckDuckGo on empty results
  - 🌐 **Global** → DuckDuckGo News API (`max_results=12`)
- `Get Market Sentiment` — DuckDuckGo text search + yfinance analyst consensus; Indian stocks use region-specific queries (Moneycontrol, Economic Times, NDTV Profit)
- `max_iter`: **8**

**Output**: News summary, corporate events, analyst sentiment, news score (1–10)

### 🟢 Agent 3 – Senior Investment Strategist & Report Writer

**Role**: Report Synthesis & Recommendations

**Input**: Full context from Agents 1 & 2 (CrewAI task context chaining)
- `max_iter`: **6** (no tool calls — pure LLM synthesis; 800–1,200 word target)

**Output**: 8-section investment report with BUY/HOLD/SELL recommendation, price targets, bull/bear case, risks

---

## Configuration

### Backend `.env`

```env
OLLAMA_BASE_URL=http://localhost:11434   # Ollama server URL
DEFAULT_LLM_MODEL=llama3.2              # Default model if none selected
REPORTS_DIR=reports                     # PDF output directory
```

### Frontend `.env`

```env
REACT_APP_WS_URL=ws://localhost:8000    # WebSocket URL
REACT_APP_API_URL=http://localhost:8000 # REST API URL
```

### Dynamically Configurable via UI

| Setting   | Description                      | Where                |
|-----------|----------------------------------|----------------------|
| LLM Model | Select from available Ollama models | LLM Config panel  |
| Ollama URL| Custom Ollama server URL         | LLM Config panel     |

Settings are **persisted in localStorage** between sessions.

---

## API Reference

### REST Endpoints

| Method | Endpoint                   | Description                  |
|--------|----------------------------|------------------------------|
| `GET`  | `/api/health`              | Health check                 |
| `GET`  | `/api/models?base_url=...` | List available Ollama models |
| `GET`  | `/api/report/{session_id}` | Download PDF report          |

### WebSocket `/ws/{session_id}`

**Client → Server** (JSON):
```json
{
  "symbol": "AAPL",
  "llm_model": "llama3.2",
  "ollama_base_url": "http://localhost:11434"
}
```

**Server → Client** event types:

| Type             | Description                                  |
|------------------|----------------------------------------------|
| `started`        | Analysis pipeline initiated                  |
| `agent_start`    | An agent has begun its task                  |
| `tool_use`       | Agent is using a specific tool               |
| `thinking`       | Agent reasoning / processing                 |
| `task_complete`  | An agent finished its task                   |
| `generating_pdf` | PDF generation in progress                   |
| `crew_complete`  | All agents done, PDF ready                   |
| `error`          | Error occurred                               |

---

## Project Structure

```
crewai-multiagent-ollama/
├── README.md
├── docs/
│   └── architecture.html        # Complete code-flow & architecture reference
│
├── backend/
│   ├── main.py              # FastAPI app, WebSocket, REST endpoints
│   ├── crew.py              # CrewAI orchestration with async event streaming
│   ├── config.py            # Pydantic settings
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── agents/
│   │   ├── stock_analyst.py     # Agent 1: Fundamental + Technical
│   │   ├── news_researcher.py   # Agent 2: News + Sentiment
│   │   └── report_writer.py     # Agent 3: Report + Recommendations
│   │
│   ├── tasks/
│   │   ├── analysis_tasks.py    # Task for Agent 1
│   │   ├── news_tasks.py        # Task for Agent 2
│   │   └── report_tasks.py      # Task for Agent 3 (with context chaining)
│   │
│   └── tools/
│       ├── stock_tools.py       # StockDataTool, TechnicalAnalysisTool
│       ├── news_tools.py        # StockNewsTool, MarketSentimentTool
│       └── pdf_generator.py     # ReportLab PDF generation
│
└── frontend/
    ├── package.json
    ├── .env
    ├── public/
    │   └── index.html           # Bootstrap 5, Google Fonts
    └── src/
        ├── index.js
        ├── App.js               # Main app, state management, WebSocket
        ├── App.css              # Dark theme, animations, custom styles
        ├── components/
        │   ├── Header.jsx           # Brand, Ollama status indicator
        │   ├── LLMConfig.jsx        # Ollama URL + model selector
        │   ├── StockInput.jsx       # Symbol input + quick-pick chips
        │   ├── AgentFlowDiagram.jsx # Animated pipeline visualization
        │   ├── ActivityLog.jsx      # Real-time streaming log
        │   └── ReportViewer.jsx     # Download + view PDF panel
        ├── hooks/
        │   └── useWebSocket.js      # WebSocket lifecycle hook
        └── services/
            └── api.js               # REST API helpers
```

---

## What's New

### v1.3.0 — March 2026

#### 🇮🇳 Indian Stock News via Zerodha Pulse
- Agent 2 now routes `.NS` / `.BO` news requests to [Zerodha Pulse](https://pulse.zerodha.com/) instead of DuckDuckGo
- Curated dictionary of **50+ NSE ticker aliases** (e.g. `HINDUNILVR → HUL / Hindustan Unilever`) for accurate article matching
- Automatic SSL certificate fallback on macOS; falls back to DuckDuckGo with Indian-context queries on empty results
- Market sentiment queries now use Indian financial media: Moneycontrol, Economic Times, NDTV Profit

#### 📄 PDF Key Metrics Banner
- The PDF cover page now shows a **6-cell Key Metrics Banner**: Current Price, Day Change %, Market Cap, P/E TTM, 52-Week High, 52-Week Low
- Sourced from Agent 1's in-process TTL cache — **zero extra network requests** during PDF generation

#### 📦 Dependency Updates

| Package       | Before    | After             | Reason                                                            |
|---------------|-----------|-------------------|-------------------------------------------------------------------|
| yfinance      | 0.2.44    | ≥1.0.0 (1.2.x)    | Rewritten HTTP layer — eliminates 429 rate-limit errors           |
| numpy         | 1.26.4    | ≥2.1.0 (2.4.x)    | Python 3.13 compatibility (no wheel for numpy 1.x on Python 3.13) |
| pandas        | 2.1.x     | ≥2.2.3 (3.0.x)    | Matches numpy 2.x API                                             |
| beautifulsoup4| —         | ≥4.12.0           | Zerodha Pulse HTML scraping                                       |

#### 📚 Documentation
- Added `docs/architecture.html` — complete code-flow, file-by-file reference, WebSocket event table, and end-to-end flow diagram

---

## Troubleshooting

### Ollama not connecting
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Ensure you've pulled at least one model
ollama list
ollama pull llama3.2
```

### Backend fails to start
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Re-install dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Must be 3.11+
```

### `ta` library import error
```bash
pip install ta
# Note: 'ta' is a pure-Python library — it does NOT require the C TA-Lib library
# The separate 'TA-Lib' package (capital letters) requires a C library — this project uses 'ta'
```

### Yahoo Finance 429 – Too Many Requests
The project uses **yfinance ≥1.0.0** (1.2.x) which has a rewritten HTTP layer with automatic 429 recovery.
If you still encounter this error:
```bash
pip install --upgrade "yfinance>=1.0.0"
```
Ensure `requirements.txt` contains `yfinance>=1.0.0` and not a pinned old version like `yfinance==0.2.44`.

### Windows – PowerShell execution policy error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then re-run `venv\Scripts\Activate.ps1`.

### Windows – `python` command not found
```cmd
REM Try the Python Launcher
py --version
py -m venv venv
py -m pip install -r requirements.txt
```
If `py` also fails, reinstall Python from [python.org](https://www.python.org/downloads/windows/) with **"Add Python to PATH"** checked.

### Windows – numpy install fails
Python 3.13 requires numpy ≥2.1.0. The `requirements.txt` already pins this correctly:
```bash
pip install "numpy>=2.1.0"
```

### Windows – Port 8000 already in use
```cmd
netstat -ano | findstr :8000
taskkill /PID <pid_from_above> /F
```

### Windows – Ollama not found after install
Ollama is added to PATH only for **new** terminal windows opened after installation.
Close your current terminal, open a new one, then run `ollama list`.

### Analysis takes too long
- Use a smaller/faster model: `phi3`, `gemma2:2b`, `llama3.2:1b`
- Reduce `max_iter` in agent definitions
- Ensure Ollama has enough RAM (8GB+ recommended for 7B models)

### Frontend not connecting to backend
```bash
# Verify backend is running
curl http://localhost:8000/api/health

# Check CORS – frontend runs on :3000, backend on :8000
# Both are whitelisted by default
```

### PDF not generating
```bash
pip install reportlab Pillow
```

### News tools returning no results
- DuckDuckGo occasionally rate-limits; retry after a minute
- For production, consider integrating a paid news API (NewsAPI, Alpha Vantage)

---

## Windows Setup

A complete step-by-step guide for running **StockMind AI on Windows 10 / 11**.

### Step 1 — Install Python 3.11+

1. Download from [python.org/downloads/windows](https://www.python.org/downloads/windows/) (Python 3.11.x or 3.13.x)
2. Run the installer and **check "Add Python to PATH"** on the first screen
3. Open a new terminal and verify:
```cmd
python --version
pip --version
```

### Step 2 — Install Node.js 18+

1. Download the LTS installer from [nodejs.org](https://nodejs.org/)
2. The installer adds `node` and `npm` to PATH automatically
3. Verify:
```cmd
node --version
npm --version
```

### Step 3 — Install Ollama

1. Download from [ollama.com/download/windows](https://ollama.com/download/windows) and run the installer
2. Ollama registers as a **Windows background service** — starts automatically with Windows
3. Open a **new** terminal and pull a model:
```cmd
ollama pull llama3.2
ollama list
```

### Step 4 — Backend Setup

**Command Prompt:**
```cmd
cd crewai-multiagent-ollama\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

**PowerShell** (enable scripts first — one-time only):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd crewai-multiagent-ollama\backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Step 5 — Frontend Setup

```cmd
cd crewai-multiagent-ollama\frontend
npm install
```

### Step 6 — Run (3 windows)

| Window | Commands |
|--------|----------|
| **1 – Ollama** | Service runs automatically; verify with `ollama list` |
| **2 – Backend** | `cd backend` → `venv\Scripts\activate` → `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` |
| **3 – Frontend** | `cd frontend` → `npm start` |

Visit [http://localhost:3000](http://localhost:3000) in your browser.

### Windows Quick-Fix Reference

| Problem | Solution |
|---------|----------|
| `venv\Scripts\activate` blocked | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `python` not found | Reinstall Python with "Add to PATH" checked, or use `py` |
| `npm` not found | Reinstall Node.js or add `C:\Program Files\nodejs` to PATH |
| Port 8000 in use | `netstat -ano \| findstr :8000` → `taskkill /PID <pid> /F` |
| Ollama not found | Open a **new** terminal after install; run `ollama list` |
| `ta` install fails | `pip install ta` (pure Python — no C library needed) |
| numpy install fails | `pip install "numpy>=2.1.0"` |

---

## Performance Tips

| Model           | Speed   | Quality | RAM Required |
|----------------|---------|---------|--------------|
| `llama3.2:1b`  | ⚡⚡⚡  | ★★★     | 2GB          |
| `llama3.2`     | ⚡⚡    | ★★★★    | 4GB          |
| `mistral`      | ⚡⚡    | ★★★★    | 4GB          |
| `llama3.1`     | ⚡      | ★★★★★   | 8GB          |
| `gemma2`       | ⚡⚡    | ★★★★    | 5GB          |

---

## Supported Stock Exchanges

| Exchange          | Example Symbols                                      | News Source    |
|-------------------|------------------------------------------------------|----------------|
| NASDAQ / NYSE     | `AAPL`, `TSLA`, `NVDA`, `MSFT`                       | DuckDuckGo     |
| NSE India (`.NS`) | `TCS.NS`, `RELIANCE.NS`, `COALINDIA.NS`, `INFY.NS`   | Zerodha Pulse  |
| BSE India (`.BO`) | `TCS.BO`, `WIPRO.BO`                                 | Zerodha Pulse  |
| London            | `HSBA.L`, `BP.L`                                     | DuckDuckGo     |
| Frankfurt         | `BMW.DE`, `SAP.DE`                                   | DuckDuckGo     |

---

## License

MIT License – free to use, modify, and distribute.

---

## Disclaimer

> This application is for **educational and informational purposes only**. The AI-generated analysis
> does not constitute financial advice. Always conduct your own research and consult a qualified
> financial advisor before making investment decisions. Past performance is not indicative of future
> results.

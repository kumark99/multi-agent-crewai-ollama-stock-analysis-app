"""
crew.py – Orchestrates the CrewAI multi-agent stock analysis pipeline.

Architecture
────────────
  Agent 1  –  Stock Analyst        → Fundamental + Technical Analysis
  Agent 2  –  News Researcher      → Recent News + Market Sentiment
  Agent 3  –  Investment Strategist → Comprehensive Report + PDF

The CrewAI execution is synchronous; we run it inside a thread-pool executor
and bridge events back to the async WebSocket via a thread-safe Queue.
"""

from __future__ import annotations

import asyncio
import json
import queue
from datetime import datetime
from typing import Any, Callable, Coroutine

from crewai import Agent, Crew, LLM, Process, Task

from agents.news_researcher import create_news_researcher
from agents.report_writer import create_report_writer
from agents.stock_analyst import create_stock_analyst
from config import settings
from tasks.analysis_tasks import create_analysis_task
from tasks.news_tasks import create_news_task
from tasks.report_tasks import create_report_task
from tools.pdf_generator import generate_pdf_report
from tools.stock_tools import _get_info as _fetch_stock_info


class StockAnalysisCrew:
    """Manages the complete CrewAI-powered stock analysis pipeline."""

    def __init__(
        self,
        symbol: str,
        llm_model: str,
        ollama_base_url: str,
        session_id: str,
        update_callback: Callable[[dict], Coroutine],
    ):
        self.symbol = symbol
        self.llm_model = llm_model
        self.ollama_base_url = ollama_base_url
        self.session_id = session_id
        self.update_callback = update_callback
        self._event_queue: queue.Queue = queue.Queue()
        self._running = False
        self._completed_tasks = 0
        self._current_agent_id = 1
        self._current_agent_name = "Stock Analyst"
        self._final_report: str = ""

    # ── Callbacks (called from CrewAI thread) ─────────────────────────────────

    def _step_callback(self, step_output: Any) -> None:
        """Called by CrewAI after every agent step (tool use / reasoning)."""
        try:
            output_str = str(step_output)

            # Detect tool usage patterns in CrewAI output
            tool_name = None
            if hasattr(step_output, "tool"):
                tool_name = str(step_output.tool)
            elif "Action:" in output_str:
                lines = output_str.split("\n")
                for line in lines:
                    if line.strip().startswith("Action:"):
                        tool_name = line.split("Action:")[-1].strip()
                        break

            if tool_name:
                event = {
                    "type": "tool_use",
                    "agent_id": self._current_agent_id,
                    "agent_name": self._current_agent_name,
                    "tool": tool_name,
                    "message": f"🔧 Using tool: {tool_name}",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                snippet = output_str.strip()[:300]
                event = {
                    "type": "thinking",
                    "agent_id": self._current_agent_id,
                    "agent_name": self._current_agent_name,
                    "message": snippet or "Processing…",
                    "timestamp": datetime.now().isoformat(),
                }

            self._event_queue.put(event)
        except Exception:
            pass

    def _task_callback(self, task_output: Any) -> None:
        """Called by CrewAI after each task completes."""
        try:
            self._completed_tasks += 1
            raw = getattr(task_output, "raw", str(task_output))

            # If this is the last task, save the full report text
            if self._completed_tasks == 3:
                self._final_report = raw

            event = {
                "type": "task_complete",
                "agent_id": self._current_agent_id,
                "agent_name": self._current_agent_name,
                "summary": raw[:400],
                "timestamp": datetime.now().isoformat(),
            }
            self._event_queue.put(event)

            # Announce the next agent
            _next = {
                1: (2, "News Researcher", "🔍 Starting news research and market sentiment analysis…"),
                2: (3, "Investment Strategist", "📋 Synthesizing data and preparing investment report…"),
            }
            if self._completed_tasks in _next:
                nid, nname, nmsg = _next[self._completed_tasks]
                self._current_agent_id = nid
                self._current_agent_name = nname
                self._event_queue.put(
                    {
                        "type": "agent_start",
                        "agent_id": nid,
                        "agent_name": nname,
                        "message": nmsg,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception:
            pass

    # ── Sync crew execution (runs in thread pool) ─────────────────────────────

    def _run_crew_sync(self) -> str:
        """Build and execute the CrewAI crew synchronously."""
        llm = LLM(
            model=f"ollama/{self.llm_model}",
            base_url=self.ollama_base_url,
            temperature=0.4,
        )

        # Announce Agent 1 start
        self._event_queue.put(
            {
                "type": "agent_start",
                "agent_id": 1,
                "agent_name": "Stock Analyst",
                "message": f"📊 Starting fundamental & technical analysis for {self.symbol}…",
                "timestamp": datetime.now().isoformat(),
            }
        )

        analyst = create_stock_analyst(llm)
        researcher = create_news_researcher(llm)
        writer = create_report_writer(llm)

        analysis_task = create_analysis_task(analyst, self.symbol)
        news_task = create_news_task(researcher, analysis_task, self.symbol)
        report_task = create_report_task(
            writer,
            analysis_task,
            news_task,
            self.symbol,
            self.session_id,
        )

        crew = Crew(
            agents=[analyst, researcher, writer],
            tasks=[analysis_task, news_task, report_task],
            process=Process.sequential,
            step_callback=self._step_callback,
            task_callback=self._task_callback,
            verbose=False,
        )

        result = crew.kickoff()
        return str(getattr(result, "raw", result))

    # ── Async orchestration ───────────────────────────────────────────────────

    async def _drain_queue(self):
        """Drain all pending events from the queue and send to WebSocket."""
        drained = 0
        while True:
            try:
                event = self._event_queue.get_nowait()
                await self.update_callback(event)
                drained += 1
            except queue.Empty:
                break
        return drained

    async def run(self):
        """Main entry-point – run crew in thread pool, stream events via WS."""
        self._running = True

        await self.update_callback(
            {
                "type": "started",
                "symbol": self.symbol,
                "llm_model": self.llm_model,
                "message": f"🚀 Analysis pipeline started for {self.symbol}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self._run_crew_sync)

        # Stream events while crew is running
        while not future.done():
            await self._drain_queue()
            await asyncio.sleep(0.15)

        # Drain any remaining events
        await self._drain_queue()

        try:
            final_output = await future
        except Exception as exc:
            await self.update_callback(
                {
                    "type": "error",
                    "message": f"Analysis failed: {str(exc)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return

        self._running = False

        # Generate PDF from the final report
        await self.update_callback(
            {
                "type": "generating_pdf",
                "message": "📄 Generating PDF report…",
                "timestamp": datetime.now().isoformat(),
            }
        )

        report_text = self._final_report or final_output

        # Fetch cached stock data from Agent 1's earlier call (5-min TTL cache,
        # so this is instant — no extra network request).
        try:
            raw_stock_info = _fetch_stock_info(self.symbol)
        except Exception:
            raw_stock_info = {}

        pdf_path = generate_pdf_report(
            report_text=report_text,
            symbol=self.symbol,
            session_id=self.session_id,
            output_dir=settings.reports_dir,
            stock_data=raw_stock_info,
        )

        await self.update_callback(
            {
                "type": "crew_complete",
                "symbol": self.symbol,
                "session_id": self.session_id,
                "pdf_url": f"/api/report/{self.session_id}",
                "message": f"✅ Analysis complete for {self.symbol}! PDF report is ready.",
                "timestamp": datetime.now().isoformat(),
            }
        )

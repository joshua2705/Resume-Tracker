"""Agent control surface: status, manual Gmail scan, scan log, moves refresh.

These let the frontend (the Tracker's "Auto-Track with Gmail" toggle and the
dashboard) drive the agents on demand, and let you trigger/inspect the daily
Gmail scan without waiting for the schedule."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import store
from ..agents import agents_importable, orchestrator
from ..config import get_settings

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/status")
def status() -> dict:
    s = get_settings()
    return {
        "agents_enabled": s.agents_enabled,
        "agents_ready": orchestrator.agents_ready(),
        "langgraph_installed": agents_importable(),
        "gemini": s.gemini_enabled,
        "langsmith": {"enabled": s.langsmith_enabled, "project": s.langsmith_project},
        "gmail": {
            "mcp_enabled": s.gmail_mcp_enabled,
            "daily_scan": s.gmail_daily_scan,
            "lookback_days": s.gmail_scan_lookback_days,
        },
        "guardrails": {
            "max_input_chars": s.coach_max_input_chars,
            "daily_token_budget": s.coach_daily_token_budget,
            "max_requests_per_min": s.coach_max_requests_per_min,
        },
    }


@router.post("/gmail/scan")
async def gmail_scan(lookback_days: int | None = None) -> dict:
    """Run the Gmail agent now and apply any tracker updates it proposes."""
    s = get_settings()
    if not s.gmail_mcp_enabled:
        raise HTTPException(400, "GMAIL_MCP_ENABLED is false — enable it in .env first.")
    if not orchestrator.agents_ready():
        raise HTTPException(400, "Agents not ready (need GEMINI_API_KEY + langgraph installed).")
    from ..agents import gmail_agent
    env = await gmail_agent.run(lookback_days)
    return env.model_dump()


@router.get("/gmail/log")
def gmail_log() -> dict:
    return {"runs": store.get_agent_state("gmail_log") or []}


@router.post("/moves/refresh")
def moves_refresh() -> dict:
    """Force the moves agent to re-evaluate (still no-ops if nothing changed)."""
    texts, changed, env = orchestrator.moves(store.get_profile(), store.list_jobs())
    return {"moves": texts, "changed": changed, "envelope": env}

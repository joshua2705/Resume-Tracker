"""FastAPI entrypoint. Run with: uvicorn app.main:app --reload"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents import agents_importable
from .agents.runtime import configure_langsmith
from .config import get_settings
from .routers import agents as agents_router
from .routers import coach, dashboard, jobs, profile, resume
from .services.llm import gemini_selftest

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Turn on LangSmith tracing (if keyed) and start the daily Gmail scan loop
    # (if enabled). Both are no-ops otherwise, so offline mode is unaffected.
    configure_langsmith()
    started = False
    if agents_importable():
        from .agents import scheduler
        started = scheduler.start()
    yield
    if started:
        from .agents import scheduler
        scheduler.stop()


app = FastAPI(title="Resume Tracker API", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.include_router(coach.router)
app.include_router(agents_router.router)


@app.get("/api/health")
def health() -> dict:
    """Reports config flags AND does a live Gemini ping so you can see whether
    the key actually works (visit http://localhost:8000/api/health)."""
    s = get_settings()
    return {
        "status": "ok",
        "llamaparse_configured": s.llama_enabled,
        "gemini": gemini_selftest(),
        "agents": {
            "enabled": s.agents_enabled,
            "langgraph_installed": agents_importable(),
            "langsmith": s.langsmith_enabled,
            "gmail_mcp": s.gmail_mcp_enabled,
            "daily_scan": s.gmail_daily_scan,
        },
    }

"""FastAPI entrypoint. Run with: uvicorn app.main:app --reload"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import coach, dashboard, jobs, profile, resume
from .services.llm import gemini_selftest

settings = get_settings()
app = FastAPI(title="Resume Tracker API", version="0.3.0")

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


@app.get("/api/health")
def health() -> dict:
    """Reports config flags AND does a live Gemini ping so you can see whether
    the key actually works (visit http://localhost:8000/api/health)."""
    return {
        "status": "ok",
        "llamaparse_configured": settings.llama_enabled,
        "gemini": gemini_selftest(),
    }

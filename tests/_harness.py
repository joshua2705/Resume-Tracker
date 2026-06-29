"""Shared test harness for Deliverable 7 — LIVE mode.

The suite runs ONLINE: the agents call the real Gemini model (GEMINI_API_KEY
from backend/.env) through LangGraph, and every run is traced to LangSmith.
Nothing is mocked or forced offline.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RESULTS = Path(__file__).resolve().parent / "results"
DATA = Path(__file__).resolve().parent / "data"
RESULTS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
sys.path.insert(0, str(BACKEND))

PACE = float(os.getenv("TEST_PACE_SECONDS", "1.5"))
N_JOBS = int(os.getenv("TEST_N_JOBS", "5"))

from app.config import get_settings                                  # noqa: E402
from app.agents import agents_importable                            # noqa: E402
from app.agents.runtime import configure_langsmith                  # noqa: E402
from app.models import (CoachMessage, Experience, Job, JobStatus,    # noqa: E402
                        Profile, ScoreBreakdown, Skill)
from app.catalog import CATALOG                                      # noqa: E402

_S = get_settings()
LIVE = bool(_S.gemini_enabled and agents_importable())
LANGSMITH_ON = configure_langsmith()
MODEL = _S.gemini_model
LANGSMITH_PROJECT = _S.langsmith_project if _S.langsmith_enabled else None


def require_live() -> None:
    if not _S.gemini_enabled:
        raise SystemExit("GEMINI_API_KEY not set in backend/.env — live tests require it.")
    if not agents_importable():
        raise SystemExit("LangGraph/LangChain stack not installed — pip install -r "
                         "backend/requirements.txt")


_TMP_STORE = DATA / "_runtime_store.json"
get_settings().data_file = _TMP_STORE


def reset_store(jobs=None) -> None:
    payload = {"profile": Profile().model_dump(), "resumes": [],
               "jobs": [j.model_dump() for j in (jobs or [])], "agent_state": {}}
    _TMP_STORE.write_text(json.dumps(payload, indent=2), "utf-8")


def seed_profile(profile) -> None:
    data = json.loads(_TMP_STORE.read_text("utf-8")) if _TMP_STORE.exists() else {
        "profile": {}, "resumes": [], "jobs": [], "agent_state": {}}
    data["profile"] = profile.model_dump()
    _TMP_STORE.write_text(json.dumps(data, indent=2), "utf-8")


_QUOTA_MARKERS = ("429", "resourceexhausted", "rate limit", "quota", "exhausted",
                  "too many requests")


def _is_quota(err) -> bool:
    e = (err or "").lower()
    return any(m in e for m in _QUOTA_MARKERS)


def live_run(run_fn, *, label="", retries=5):
    """Run an agent .run() (returns an AgentEnvelope). Agents catch their own
    errors and return a fallback envelope; if it fell back due to quota, back off
    and retry. Paces every call."""
    env = None
    for attempt in range(retries + 1):
        env = run_fn()
        meta = env.meta
        if meta.fallback_used and _is_quota(meta.error or ""):
            wait = min(60, 5 * (2 ** attempt))
            print(f"   [quota] {label}: backing off {wait}s (attempt {attempt+1})")
            time.sleep(wait)
            continue
        break
    time.sleep(PACE)
    return env


def base_profile() -> Profile:
    return Profile(
        summary="Recent CS graduate seeking an entry-level data/software role.",
        skills=[Skill(name=n, category=c, level=l) for n, c, l in [
            ("Python", "Programming", 4), ("SQL", "Data", 3), ("Pandas", "Data", 3),
            ("Git", "Tools", 3), ("REST APIs", "Backend", 2), ("Excel", "Data", 3)]],
        experiences=[
            Experience(role="Data Analyst Intern", company="Acme Corp", start="2024",
                       end="2024", highlights=["Built SQL dashboards",
                                               "Automated reports in Python"]),
            Experience(role="Open-source contributor", company="GitHub", start="2023",
                       end="2024", highlights=["Shipped a FastAPI feature",
                                               "Wrote unit tests"])])


def empty_profile() -> Profile:
    return Profile()


def catalog_jobs():
    return [(c.title, c.description) for c in CATALOG]


def make_job(**kw) -> Job:
    d = dict(title="Software Engineer I", company="Cloudpeak",
             description="Build REST APIs in Python.", status=JobStatus.applied)
    d.update(kw)
    return Job(**d)


def flush_traces() -> None:
    try:
        from langchain_core.tracers.langchain import wait_for_all_tracers
        wait_for_all_tracers()
    except Exception:
        pass


def write_result(name, obj) -> Path:
    obj.setdefault("_meta", {})
    obj["_meta"].update({"mode": "online-live", "model": MODEL,
                         "langsmith_project": LANGSMITH_PROJECT, "live": LIVE})
    p = RESULTS / name
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), "utf-8")
    return p


def pct(numer, denom) -> float:
    return round(100.0 * numer / denom, 1) if denom else 0.0

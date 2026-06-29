"""orchestrator — the one place routers call into the agents.

Why this and not a supervisor agent: the four agents are triggered by
unrelated events (an HTTP request to /score, a dashboard load, a daily
schedule) and never collaborate within a single turn, so there's nothing for a
supervisor to coordinate. A supervisor would add a model round-trip, latency
and cost for zero routing benefit. This module is a plain dispatcher: it checks
whether the agent stack is usable, routes to the right agent, and otherwise
returns the existing heuristic/Gemini path unchanged. Each call returns the
agent's structured envelope so callers can log/inspect it.
"""
from __future__ import annotations

from ..config import get_settings
from ..models import CoachMessage, Job, Profile, ScoreBreakdown
from . import agents_importable


def agents_ready() -> bool:
    """Agents are usable only with the master switch, a Gemini key, and the
    langgraph stack installed."""
    return get_settings().agents_active and agents_importable()


# --- match -------------------------------------------------------------- #
def score(profile: Profile, title: str, description: str) -> tuple[ScoreBreakdown, dict]:
    """Returns (ScoreBreakdown, envelope-dict). Falls back to get_llm() when
    agents aren't ready, so existing behavior is preserved."""
    if agents_ready():
        from . import match_agent
        env = match_agent.run(profile, title, description)
        return match_agent.to_score_breakdown(env), env.model_dump()
    from ..services.llm import get_llm
    return get_llm().score(profile, title, description), {}


# --- moves -------------------------------------------------------------- #
def moves(profile: Profile, jobs) -> tuple[list[str], bool, dict]:
    """Returns (texts, changed, envelope-dict). Empty texts => caller should use
    its own heuristic (keeps the dashboard instant when agents are off)."""
    if agents_ready():
        from . import moves_agent
        env = moves_agent.run(profile, jobs)
        texts = [m["text"] for m in env.data.get("moves", [])][:3]
        return texts, env.data.get("changed", True), env.model_dump()
    return [], True, {}


# --- coach -------------------------------------------------------------- #
def coach(profile: Profile, history: list[CoachMessage], job: Job | None,
          safety=None) -> tuple[str, dict]:
    """Returns (reply, envelope-dict)."""
    if agents_ready():
        from . import coach_agent
        env = coach_agent.run(profile, history, job, safety=safety)
        return env.data.get("reply", ""), env.model_dump()
    from ..services.llm import get_llm
    return get_llm().coach(profile, history, job), {}

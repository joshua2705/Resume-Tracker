"""Structured JSON contracts the agents speak.

Every agent returns an ``AgentEnvelope`` — a stable wrapper with a typed
``data`` payload plus ``meta`` (model, latency, tokens, trace, fallback). This
is what "agents talk in a structured manner using JSONs and not just text"
means in practice: routers, the scheduler, and any agent-to-agent handoff all
exchange these models, never raw strings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Envelope + meta
# --------------------------------------------------------------------------- #
class AgentMeta(BaseModel):
    agent: str
    model: str = ""
    method: Literal["agent", "fallback", "cache"] = "agent"
    fallback_used: bool = False
    latency_ms: int = 0
    tokens_used: int = 0
    trace_project: Optional[str] = None      # LangSmith project (if tracing on)
    error: Optional[str] = None
    at: str = Field(default_factory=_now)


class AgentEnvelope(BaseModel):
    """Uniform wrapper. ``data`` holds one of the typed payloads below."""
    schema_version: str = SCHEMA_VERSION
    agent: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    meta: AgentMeta


def envelope(agent: str, payload: BaseModel, meta: AgentMeta, ok: bool = True) -> AgentEnvelope:
    return AgentEnvelope(agent=agent, ok=ok, data=payload.model_dump(), meta=meta)


# --------------------------------------------------------------------------- #
# match_agent
# --------------------------------------------------------------------------- #
class MatchResult(BaseModel):
    score: int = 0                                   # 0..100
    reasoning: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendation: Literal["strong", "moderate", "stretch", "weak"] = "moderate"
    confidence: float = 0.5                          # 0..1


# --------------------------------------------------------------------------- #
# moves_agent
# --------------------------------------------------------------------------- #
class DailyMove(BaseModel):
    text: str                                        # shown on the dashboard
    rationale: str = ""                              # why (not shown, for logs)
    category: Literal["skills", "applications", "prep", "explore", "profile"] = "explore"
    priority: int = 3                                # 1 (highest) .. 5


class MovesResult(BaseModel):
    moves: list[DailyMove] = Field(default_factory=list)
    changed: bool = True                             # False => returned the cache
    fingerprint: str = ""                            # state hash that produced these


# --------------------------------------------------------------------------- #
# coach_agent
# --------------------------------------------------------------------------- #
class CoachSafety(BaseModel):
    flagged: bool = False
    reason: str = ""


class CoachResult(BaseModel):
    reply: str = ""
    tools_used: list[str] = Field(default_factory=list)
    focus_job_id: Optional[str] = None
    safety: CoachSafety = Field(default_factory=CoachSafety)


# --------------------------------------------------------------------------- #
# gmail_agent
# --------------------------------------------------------------------------- #
class GmailUpdateProposal(BaseModel):
    job_id: str
    company: str
    old_status: str
    new_status: str
    confidence: float = 0.5
    evidence_subject: str = ""
    evidence_snippet: str = ""
    email_date: str = ""
    thread_id: str = ""
    applied: bool = False


class GmailScanResult(BaseModel):
    scanned_companies: list[str] = Field(default_factory=list)
    proposals: list[GmailUpdateProposal] = Field(default_factory=list)
    applied_count: int = 0
    skipped_no_change: int = 0
    errors: list[str] = Field(default_factory=list)
    lookback_days: int = 1

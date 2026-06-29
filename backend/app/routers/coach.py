"""AI Coach chat. Routed through the coach_agent (ReAct, tool-using) when
agents are active, else the existing Gemini/heuristic path. Every request first
passes the chat guardrails: input validation/sanitization and a per-user token
rate limit. Context = the user's data, fetched by the agent's own tools."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from .. import store
from ..agents import orchestrator
from ..agents.runtime import estimate_tokens
from ..config import get_settings
from ..guardrails import (GuardrailError, RateLimitError, coach_rate_limiter,
                          validate_chat_messages)
from ..models import CoachRequest

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.get("/context")
def coach_context() -> dict:
    p = store.get_profile()
    jobs = store.list_jobs()
    resumes = store.list_resumes()
    scores = [j.score.score for j in jobs if j.score]
    facts = []
    if p.skills:
        facts.append(f"{len(p.skills)} skills mapped"
                     + (f" from {len(resumes)} resume(s)" if resumes else ""))
    if p.experiences:
        facts.append(f"{len(p.experiences)} experiences on file")
    facts.append(f"{len(jobs)} job(s) tracked"
                 + (f" · avg fit {round(sum(scores)/len(scores))}%" if scores else ""))
    if not p.skills and not p.experiences:
        facts = ["No resume parsed yet — upload one for tailored coaching."]
    return {"facts": facts, "live": get_settings().gemini_enabled}


@router.post("")
def chat(req: CoachRequest, request: Request) -> dict:
    s = get_settings()

    # 1) Guardrail: validate + sanitize input.
    try:
        validated = validate_chat_messages(req.messages)
    except GuardrailError as e:
        raise HTTPException(400, str(e))

    # 2) Guardrail: per-user token rate limit (reserve an estimate).
    identity = (request.client.host if request.client else "local") + ":coach"
    est = estimate_tokens(" ".join(m.content for m in validated.messages)) + 600
    try:
        coach_rate_limiter.check(identity, est)
    except RateLimitError as e:
        raise HTTPException(429, str(e), headers={"Retry-After": str(e.retry_after)})

    # 3) Run the coach agent (or fallback), then reconcile real token usage.
    job = store.get_job(req.job_id) if req.job_id else None
    reply, env = orchestrator.coach(
        store.get_profile(), validated.messages, job, safety=validated.as_safety())
    actual = env.get("meta", {}).get("tokens_used", 0) if env else 0
    coach_rate_limiter.reconcile(identity, est, actual or est)

    return {
        "reply": reply,
        "live": s.gemini_enabled,
        "safety": validated.as_safety(),
        "agent": env.get("meta") if env else None,
        "tokens_remaining_today": coach_rate_limiter.remaining(identity),
    }

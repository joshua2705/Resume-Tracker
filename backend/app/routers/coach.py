"""AI Coach chat. Gemini-backed when keyed (errors are logged, not hidden).
Context = the aggregate profile (+ an optional focused job)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import store
from ..config import get_settings
from ..models import CoachRequest
from ..services.llm import get_llm

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
def chat(req: CoachRequest) -> dict:
    if not req.messages:
        raise HTTPException(400, "messages required")
    job = store.get_job(req.job_id) if req.job_id else None
    reply = get_llm().coach(store.get_profile(), req.messages, job)
    return {"reply": reply, "live": get_settings().gemini_enabled}

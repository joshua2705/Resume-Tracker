"""Dashboard summary — fast, at-a-glance stats from the aggregate profile.
Uses the offline heuristic for top-match scoring so the landing page is instant."""
from __future__ import annotations

from fastapi import APIRouter

from .. import store
from ..catalog import CATALOG
from ..config import get_settings
from ..services.llm import HeuristicLLM

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard() -> dict:
    s = get_settings()
    profile = store.get_profile()
    jobs = store.list_jobs()
    resumes = store.list_resumes()
    heur = HeuristicLLM()
    has_profile = bool(profile.skills or profile.experiences)

    top_matches = []
    if has_profile:
        scored = [(c, heur.score(profile, c.title, c.description)) for c in CATALOG]
        scored.sort(key=lambda x: x[1].score, reverse=True)
        top_matches = [{"id": c.id, "title": c.title, "company": c.company,
                        "score": sb.score, "missing": sb.missing_skills}
                       for c, sb in scored[:3]]

    tracked = [j.score.score for j in jobs if j.score]
    avg_fit = round(sum(tracked) / len(tracked)) if tracked \
        else (top_matches[0]["score"] if top_matches else 0)

    moves: list[str] = []
    if top_matches and top_matches[0]["missing"]:
        m = top_matches[0]
        moves.append(f"Add {min(2, len(m['missing']))} missing skills to beat the "
                     f"{m['title']} role ({m['score']}% → {min(100, m['score'] + 12)}%).")
    needs_prep = [j for j in jobs if j.status.value in ("Applied", "Interviewing") and not j.prep]
    if needs_prep:
        moves.append(f"Prep interview questions for your {needs_prep[0].company or 'tracked'} role.")
    applied = [j for j in jobs if j.status.value == "Applied"]
    if applied:
        moves.append(f"Follow up on {len(applied)} application(s) sitting in \"Applied\".")
    if not has_profile:
        moves = ["Upload your resume to build your skills mind map.",
                 "Browse the Jobs tab and evaluate your fit.",
                 "Open the AI Coach to plan your search."]
    while len(moves) < 3:
        moves.append(["Browse new roles in the Jobs tab.",
                      "Review your mind map and add any missing skills.",
                      "Run a mock interview with the AI Coach."][len(moves) % 3])

    recent = [f"{j.status.value} · {j.title} at {j.company}" for j in jobs[-4:][::-1]] \
        or ["No activity yet — apply to a job to get started."]

    return {
        "name": s.user_name,
        "has_active_resume": has_profile,
        "resume_parsed": len(resumes) > 0,
        "resume_count": len(resumes),
        "skills_count": len(profile.skills),
        "experiences_count": len(profile.experiences),
        "jobs_count": len(jobs),
        "avg_fit": avg_fit,
        "top_matches": top_matches,
        "moves": moves[:3],
        "recent_activity": recent,
        "providers": {"gemini": s.gemini_enabled, "llamaparse": s.llama_enabled},
    }

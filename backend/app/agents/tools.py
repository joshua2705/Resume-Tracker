"""LangChain tools that expose the user's data to the agents.

Each tool returns a JSON string (not prose) so the agent reasons over
structured data. The coach agent is handed these and decides on its own which
to call — it does NOT receive the whole profile up front, matching the
requirement that it "decide if it needs to access a specific job's description
or the user's skills".

`build_coach_tools()` is a factory (rather than module-level @tool objects) so
the tools close over fresh store reads on every request.
"""
from __future__ import annotations

import json

from .. import store


def _profile_skills() -> list[dict]:
    p = store.get_profile()
    return [{"name": s.name, "category": s.category, "level": s.level} for s in p.skills]


def _profile_experience() -> list[dict]:
    p = store.get_profile()
    return [{"role": e.role, "company": e.company, "start": e.start, "end": e.end,
             "highlights": e.highlights} for e in p.experiences]


def _tracked_jobs() -> list[dict]:
    out = []
    for j in store.list_jobs():
        out.append({
            "id": j.id, "title": j.title, "company": j.company,
            "status": j.status.value,
            "score": j.score.score if j.score else None,
        })
    return out


def _job_description(job_id: str = "", company: str = "", title: str = "") -> dict:
    jobs = store.list_jobs()
    job = None
    if job_id:
        job = next((j for j in jobs if j.id == job_id), None)
    if job is None and (company or title):
        key_c, key_t = company.lower().strip(), title.lower().strip()
        job = next((j for j in jobs
                    if (key_c and key_c in j.company.lower())
                    or (key_t and key_t in j.title.lower())), None)
    if job is None:
        return {"found": False, "hint": "No matching tracked job. Use list_tracked_jobs first."}
    return {
        "found": True, "id": job.id, "title": job.title, "company": job.company,
        "status": job.status.value, "description": job.description,
        "missing_skills": job.score.missing_skills if job.score else [],
        "matched_skills": job.score.matched_skills if job.score else [],
        "score": job.score.score if job.score else None,
    }


def build_coach_tools() -> list:
    """Return langchain tools bound to the current store. Imported lazily."""
    from langchain_core.tools import tool

    @tool
    def get_user_skills() -> str:
        """Return the user's skills (name, category, level 1-5) as JSON.
        Call this when advice depends on what the user can already do."""
        return json.dumps(_profile_skills())

    @tool
    def get_user_experience() -> str:
        """Return the user's work/project experience (role, company, dates,
        highlights) as JSON. Call this for resume/story/STAR-style questions."""
        return json.dumps(_profile_experience())

    @tool
    def list_tracked_jobs() -> str:
        """Return the jobs in the user's tracker (id, title, company, status,
        fit score) as JSON. Call this to learn what roles the user is pursuing
        before discussing a specific one."""
        return json.dumps(_tracked_jobs())

    @tool
    def get_job_description(job_id: str = "", company: str = "", title: str = "") -> str:
        """Return one tracked job's full description and skill gaps as JSON.
        Look it up by job_id (preferred), or by company/title substring.
        Call this only when the user focuses on a specific role."""
        return json.dumps(_job_description(job_id=job_id, company=company, title=title))

    return [get_user_skills, get_user_experience, list_tracked_jobs, get_job_description]

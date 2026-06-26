"""JSON-file persistence. One aggregate Profile + resume metadata + jobs.
Handles migration from earlier shapes (V1 single profile, V2 resumes-with-
embedded-content). Swap for a real DB later without touching routers."""
from __future__ import annotations

import json
import threading
from typing import Optional

from .config import get_settings
from .models import Job, Profile, Resume

_lock = threading.Lock()


def _empty() -> dict:
    return {"profile": Profile().model_dump(), "resumes": [], "jobs": [],
            "agent_state": {}}


def _migrate(data: dict) -> dict:
    if "profile" in data and "resumes" in data and \
            all("skills" not in r for r in data["resumes"]):
        data.setdefault("jobs", [])
        data.setdefault("agent_state", {})  # V4: agent memory (moves cache, gmail log)
        return data  # already V3/V4

    profile = {"summary": "", "skills": [], "experiences": []}
    resumes_meta: list[dict] = []

    old_resumes = data.get("resumes")
    if isinstance(old_resumes, list) and old_resumes and "skills" in old_resumes[0]:
        # V2: each resume embedded its own content -> tag into one profile
        for r in old_resumes:
            rid = r.get("id")
            for s in r.get("skills", []):
                s = {**s, "resume_id": rid, "source": s.get("source", "resume")}
                profile["skills"].append(s)
            for e in r.get("experiences", []):
                e = {**e, "resume_id": rid, "source": e.get("source", "resume")}
                profile["experiences"].append(e)
            if r.get("summary") and not profile["summary"]:
                profile["summary"] = r["summary"]
            resumes_meta.append({
                "id": rid, "name": r.get("name", "Resume"), "filename": r.get("filename", ""),
                "created_at": r.get("created_at", ""), "parser": r.get("parser", ""),
                "skill_count": len(r.get("skills", [])),
                "experience_count": len(r.get("experiences", [])),
            })
    elif isinstance(data.get("profile"), dict):
        # V1: single profile, no resumes
        p = data["profile"]
        profile["summary"] = p.get("summary", "")
        profile["skills"] = p.get("skills", [])
        profile["experiences"] = p.get("experiences", [])

    return {"profile": profile, "resumes": resumes_meta, "jobs": data.get("jobs", []),
            "agent_state": data.get("agent_state", {})}


def _read() -> dict:
    path = get_settings().data_file
    if not path.exists():
        return _empty()
    try:
        return _migrate(json.loads(path.read_text("utf-8")))
    except (json.JSONDecodeError, OSError):
        return _empty()


def _write(data: dict) -> None:
    path = get_settings().data_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), "utf-8")


# --- Profile ------------------------------------------------------------- #
def get_profile() -> Profile:
    with _lock:
        return Profile.model_validate(_read()["profile"])


def save_profile(profile: Profile) -> Profile:
    with _lock:
        data = _read()
        data["profile"] = profile.model_dump()
        _write(data)
        return profile


# --- Resumes ------------------------------------------------------------- #
def list_resumes() -> list[Resume]:
    with _lock:
        return [Resume.model_validate(r) for r in _read()["resumes"]]


def add_resume(resume: Resume, skills: list, experiences: list, summary: str = "") -> Resume:
    """Append a resume's parsed items to the profile (tagged with resume.id),
    record resume metadata, and persist."""
    with _lock:
        data = _read()
        profile = Profile.model_validate(data["profile"])
        existing = {s.name.lower() for s in profile.skills}
        added_s = 0
        for s in skills:
            if s.name.lower() in existing:
                continue
            s.resume_id = resume.id
            s.source = "resume"
            profile.skills.append(s)
            existing.add(s.name.lower())
            added_s += 1
        ex_keys = {(e.role.lower(), e.company.lower()) for e in profile.experiences}
        added_e = 0
        for e in experiences:
            if (e.role.lower(), e.company.lower()) in ex_keys:
                continue
            e.resume_id = resume.id
            e.source = "resume"
            profile.experiences.append(e)
            added_e += 1
        if not profile.summary and summary:
            profile.summary = summary
        resume.skill_count = added_s
        resume.experience_count = added_e
        data["profile"] = profile.model_dump()
        data["resumes"].append(resume.model_dump())
        _write(data)
        return resume


def delete_resume(resume_id: str) -> bool:
    """Remove the resume record AND prune the profile items it contributed."""
    with _lock:
        data = _read()
        before = len(data["resumes"])
        data["resumes"] = [r for r in data["resumes"] if r["id"] != resume_id]
        if len(data["resumes"]) == before:
            return False
        profile = Profile.model_validate(data["profile"])
        profile.skills = [s for s in profile.skills if s.resume_id != resume_id]
        profile.experiences = [e for e in profile.experiences if e.resume_id != resume_id]
        data["profile"] = profile.model_dump()
        _write(data)
        return True


# --- Jobs ---------------------------------------------------------------- #
def list_jobs() -> list[Job]:
    with _lock:
        return [Job.model_validate(j) for j in _read()["jobs"]]


def get_job(job_id: str) -> Optional[Job]:
    return next((j for j in list_jobs() if j.id == job_id), None)


def upsert_job(job: Job) -> Job:
    with _lock:
        data = _read()
        jobs = data["jobs"]
        for i, e in enumerate(jobs):
            if e["id"] == job.id:
                jobs[i] = job.model_dump()
                break
        else:
            jobs.append(job.model_dump())
        _write(data)
        return job


def delete_job(job_id: str) -> bool:
    with _lock:
        data = _read()
        before = len(data["jobs"])
        data["jobs"] = [j for j in data["jobs"] if j["id"] != job_id]
        _write(data)
        return len(data["jobs"]) < before


# --- Agent state --------------------------------------------------------- #
# Small key/value bag the agents use as durable memory: the daily-moves cache
# (last fingerprint + moves) and the Gmail scan log. Kept here so the JSON file
# stays the single source of truth.
def get_agent_state(key: str, default=None):
    with _lock:
        return _read().get("agent_state", {}).get(key, default)


def save_agent_state(key: str, value) -> None:
    with _lock:
        data = _read()
        data.setdefault("agent_state", {})[key] = value
        _write(data)

"""Job catalog (browse + AI evaluate), custom jobs, and the application tracker.
Scoring is against the aggregate profile (the mind map).

To conserve Gemini quota, catalog evaluations are cached per (job, profile)
fingerprint — re-opening the same job, or applying to one you just evaluated,
reuses the cached score instead of making another API call."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Query

from .. import store
from ..agents import orchestrator
from ..catalog import CATALOG, get_catalog_job
from ..models import (CatalogJob, Job, JobIn, JobPatch, Profile, ROUNDS,
                      ScoreBreakdown, ScoreRequest)
from ..services.llm import get_llm

router = APIRouter(prefix="/api", tags=["jobs"])

# Simple in-memory evaluation cache: { "catId:profileFingerprint" -> ScoreBreakdown }
_eval_cache: dict[str, ScoreBreakdown] = {}


def _desc_with_skills(description: str, skills: list[str]) -> str:
    return description + ("\nRequired skills: " + ", ".join(skills) if skills else "")


def _fingerprint(profile: Profile) -> str:
    basis = "|".join(sorted(s.name.lower() for s in profile.skills)) + "#" + \
            "|".join(sorted(e.role.lower() for e in profile.experiences))
    return hashlib.md5(basis.encode()).hexdigest()[:10]


def _score_catalog(cat_id: str, title: str, description: str, profile: Profile) -> ScoreBreakdown:
    key = f"{cat_id}:{_fingerprint(profile)}"
    cached = _eval_cache.get(key)
    if cached is not None:
        return cached
    # Route through the match_agent (falls back to get_llm() when agents are off).
    sb, _ = orchestrator.score(profile, title, description)
    # Cache only real AI results so the app auto-upgrades from the offline
    # fallback to Gemini once quota returns (instead of caching a fallback).
    if sb.method == "llm":
        _eval_cache[key] = sb
    return sb


# --- Catalog + scoring --------------------------------------------------- #
@router.get("/catalog", response_model=list[CatalogJob])
def list_catalog() -> list[CatalogJob]:
    return CATALOG


@router.post("/catalog/{cat_id}/evaluate", response_model=ScoreBreakdown)
def evaluate_catalog(cat_id: str) -> ScoreBreakdown:
    job = get_catalog_job(cat_id)
    if not job:
        raise HTTPException(404, "Catalog job not found")
    return _score_catalog(cat_id, job.title, job.description, store.get_profile())


@router.post("/score", response_model=ScoreBreakdown)
def evaluate_arbitrary(req: ScoreRequest) -> ScoreBreakdown:
    sb, _ = orchestrator.score(store.get_profile(), req.title,
                               _desc_with_skills(req.description, req.skills))
    return sb


# --- Tracker ------------------------------------------------------------- #
@router.get("/jobs", response_model=list[Job])
def list_jobs() -> list[Job]:
    return store.list_jobs()


@router.post("/jobs", response_model=Job)
def apply_to_job(payload: JobIn) -> Job:
    profile = store.get_profile()
    description = _desc_with_skills(payload.description, payload.skills)
    job = Job(title=payload.title, company=payload.company, location=payload.location,
              description=description, catalog_id=payload.catalog_id, status=payload.status)
    # Reuse the score we already computed when the dialog was opened, if available.
    if payload.catalog_id:
        job.score = _score_catalog(payload.catalog_id, payload.title, description, profile)
    else:
        job.score, _ = orchestrator.score(profile, job.title, description)
    return store.upsert_job(job)


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=Job)
def patch_job(job_id: str, patch: JobPatch) -> Job:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if patch.status is not None:
        job.status = patch.status
    if patch.gmail_tracking is not None:
        job.gmail_tracking = patch.gmail_tracking  # PLACEHOLDER (no real Gmail wiring)
    return store.upsert_job(job)


@router.post("/jobs/{job_id}/prep", response_model=Job)
def prep_round(job_id: str, round: str = Query(...)) -> Job:
    if round not in ROUNDS:
        raise HTTPException(400, f"round must be one of {ROUNDS}")
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job.prep[round] = get_llm().questions(store.get_profile(), job, round)
    return store.upsert_job(job)


@router.delete("/jobs/{job_id}")
def remove_job(job_id: str) -> dict:
    if not store.delete_job(job_id):
        raise HTTPException(404, "Job not found")
    return {"ok": True}

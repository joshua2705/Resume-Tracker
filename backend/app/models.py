"""Domain models shared across the API. One source of truth for shapes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Profile = ONE aggregate mind map. Each skill/experience remembers the resume
# that contributed it (resume_id), or None when added manually. Deleting a
# resume prunes exactly the items it added; manual items always persist.
# --------------------------------------------------------------------------- #
class Skill(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    category: str = "General"
    level: Optional[int] = None
    source: str = "manual"            # "resume" | "manual"
    resume_id: Optional[str] = None   # which resume added it (None = manual)


class Experience(BaseModel):
    id: str = Field(default_factory=_id)
    role: str
    company: str = ""
    start: str = ""
    end: str = ""
    highlights: list[str] = Field(default_factory=list)
    source: str = "manual"
    resume_id: Optional[str] = None


class Profile(BaseModel):
    summary: str = ""
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)


class Resume(BaseModel):
    """Upload record (metadata only). Its content lives in the Profile, tagged
    with this resume's id."""
    id: str = Field(default_factory=_id)
    name: str = "Resume"
    filename: str = ""
    created_at: str = Field(default_factory=_now)
    parser: str = ""                  # which parser produced it
    skill_count: int = 0              # contributed counts (computed at write time)
    experience_count: int = 0


# Inbound payloads for manual editing
class SkillIn(BaseModel):
    name: str
    category: str = "General"
    level: Optional[int] = None


class ExperienceIn(BaseModel):
    role: str
    company: str = ""
    start: str = ""
    end: str = ""
    highlights: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Jobs (tracker) + catalog
# --------------------------------------------------------------------------- #
class JobStatus(str, Enum):
    saved = "Saved"
    applied = "Applied"
    interviewing = "Interviewing"
    offer = "Offer"
    rejected = "Rejected"


ROUNDS = ["HR", "Hiring Manager", "Team Fit"]


class ScoreBreakdown(BaseModel):
    score: int = 0
    reasoning: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    method: str = "heuristic"


class CatalogJob(BaseModel):
    id: str
    title: str
    company: str
    location: str = ""
    tags: list[str] = Field(default_factory=list)
    description: str = ""


class Job(BaseModel):
    id: str = Field(default_factory=_id)
    catalog_id: Optional[str] = None
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    created_at: str = Field(default_factory=_now)
    status: JobStatus = JobStatus.applied
    score: Optional[ScoreBreakdown] = None
    prep: dict[str, list[str]] = Field(default_factory=dict)
    gmail_tracking: bool = False


class JobIn(BaseModel):
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    skills: list[str] = Field(default_factory=list)   # for custom jobs
    catalog_id: Optional[str] = None
    status: JobStatus = JobStatus.applied


class JobPatch(BaseModel):
    status: Optional[JobStatus] = None
    gmail_tracking: Optional[bool] = None


class ScoreRequest(BaseModel):
    title: str = ""
    company: str = ""
    description: str = ""
    skills: list[str] = Field(default_factory=list)


class CoachMessage(BaseModel):
    role: str
    content: str


class CoachRequest(BaseModel):
    messages: list[CoachMessage]
    job_id: Optional[str] = None


# --------------------------------------------------------------------------- #
# Parser output
# --------------------------------------------------------------------------- #
class ParsedResume(BaseModel):
    summary: str = ""
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    parser: str = "mock"

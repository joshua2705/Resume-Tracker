"""The aggregate mind map. Manual edits add items with resume_id=None so they
survive resume deletions. Editing a resume-sourced item keeps its tag."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import store
from ..models import Experience, ExperienceIn, Profile, Skill, SkillIn

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=Profile)
def read_profile() -> Profile:
    return store.get_profile()


@router.post("/skills", response_model=Profile)
def add_skill(payload: SkillIn) -> Profile:
    p = store.get_profile()
    p.skills.append(Skill(**payload.model_dump(), source="manual", resume_id=None))
    return store.save_profile(p)


@router.put("/skills/{skill_id}", response_model=Profile)
def edit_skill(skill_id: str, payload: SkillIn) -> Profile:
    p = store.get_profile()
    for s in p.skills:
        if s.id == skill_id:
            s.name, s.category, s.level = payload.name, payload.category, payload.level
            return store.save_profile(p)
    raise HTTPException(404, "Skill not found")


@router.delete("/skills/{skill_id}", response_model=Profile)
def delete_skill(skill_id: str) -> Profile:
    p = store.get_profile()
    p.skills = [s for s in p.skills if s.id != skill_id]
    return store.save_profile(p)


@router.post("/experiences", response_model=Profile)
def add_experience(payload: ExperienceIn) -> Profile:
    p = store.get_profile()
    p.experiences.append(Experience(**payload.model_dump(), source="manual", resume_id=None))
    return store.save_profile(p)


@router.put("/experiences/{exp_id}", response_model=Profile)
def edit_experience(exp_id: str, payload: ExperienceIn) -> Profile:
    p = store.get_profile()
    for e in p.experiences:
        if e.id == exp_id:
            for k, v in payload.model_dump().items():
                setattr(e, k, v)
            return store.save_profile(p)
    raise HTTPException(404, "Experience not found")


@router.delete("/experiences/{exp_id}", response_model=Profile)
def delete_experience(exp_id: str) -> Profile:
    p = store.get_profile()
    p.experiences = [e for e in p.experiences if e.id != exp_id]
    return store.save_profile(p)

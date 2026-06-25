"""Resume uploads. Each upload is parsed; its skills/experiences are added to
the shared mind map tagged with the resume's id. Deleting a resume removes
exactly those tagged items."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .. import store
from ..models import Resume
from ..services.parser import get_parser

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.get("", response_model=list[Resume])
def list_resumes() -> list[Resume]:
    return store.list_resumes()


@router.get("/parser-status")
def parser_status() -> dict:
    return {"parser": get_parser().__class__.__name__}


@router.post("", response_model=Resume)
async def upload_resume(file: UploadFile = File(...), name: str = Form("")) -> Resume:
    content = await file.read()
    parsed = get_parser().parse(content, file.filename or "resume.pdf")
    resume = Resume(
        name=name.strip() or (file.filename or "Resume").rsplit(".", 1)[0],
        filename=file.filename or "",
        parser=parsed.parser,
    )
    return store.add_resume(resume, parsed.skills, parsed.experiences, parsed.summary)


@router.delete("/{resume_id}")
def delete(resume_id: str) -> dict:
    if not store.delete_resume(resume_id):
        raise HTTPException(404, "Resume not found")
    return {"ok": True}

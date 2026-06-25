"""Resume parsing behind one interface.

LlamaParseResumeParser (active when LLAMA_CLOUD_API_KEY is set):
  PDF bytes -> LlamaParse markdown -> Gemini structures it into skills/experiences.
Falls back to the mock on any failure, but prints why so problems are visible.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import traceback
from typing import Protocol

from ..config import get_settings
from ..models import Experience, ParsedResume, Skill


def _log(where: str, err: Exception) -> None:
    print(f"[parser] {where} failed: {type(err).__name__}: {err}", file=sys.stderr)
    traceback.print_exc()


class ResumeParser(Protocol):
    def parse(self, file_bytes: bytes, filename: str) -> ParsedResume: ...


class MockResumeParser:
    name = "mock"

    def parse(self, file_bytes: bytes, filename: str) -> ParsedResume:
        return ParsedResume(
            parser=self.name,
            summary=("Sample profile — set LLAMA_CLOUD_API_KEY (and GEMINI_API_KEY) to "
                     "parse your real resume."),
            skills=[
                Skill(name="Python", category="Technical", level=4),
                Skill(name="SQL", category="Technical", level=4),
                Skill(name="Data Analysis", category="Technical", level=4),
                Skill(name="Tableau", category="Technical", level=3),
                Skill(name="Financial Modeling", category="Business", level=3),
                Skill(name="Stakeholder Communication", category="Soft", level=4),
            ],
            experiences=[
                Experience(role="Business Analyst Intern", company="Acme Consulting",
                           start="2024-06", end="2024-12",
                           highlights=["Built SQL + Python pipelines cutting a report from 6h to 20min."]),
                Experience(role="Data Analytics Project Lead", company="ESSEC Business School",
                           start="2023-09", end="2024-05",
                           highlights=["Led a 4-person team analyzing 100k+ transactions in Tableau."]),
            ],
        )


_EXTRACT_PROMPT = (
    "Extract this resume into JSON with EXACTLY this shape:\n"
    '{"summary": str, "skills": [{"name": str, "category": '
    '"Technical|Business|Soft|Languages|General", "level": int 1-5 or null}], '
    '"experiences": [{"role": str, "company": str, "start": "YYYY-MM", '
    '"end": "YYYY-MM or Present", "highlights": [str]}]}\n'
    "Infer reasonable skill categories and levels. Respond ONLY with the JSON.\n\n"
    "RESUME:\n"
)


class LlamaParseResumeParser:
    name = "llamaparse"

    def _to_markdown(self, file_bytes: bytes, filename: str) -> str:
        from llama_parse import LlamaParse
        s = get_settings()
        parser = LlamaParse(api_key=s.llama_api_key, result_type="markdown")
        suffix = "." + (filename.rsplit(".", 1)[-1] if "." in filename else "pdf")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            docs = parser.load_data(tmp.name)
        return "\n\n".join(getattr(d, "text", "") for d in docs)

    def _structure(self, markdown: str) -> ParsedResume:
        from google import genai
        from google.genai import types
        s = get_settings()
        client = genai.Client(api_key=s.gemini_api_key)
        resp = client.models.generate_content(
            model=s.gemini_model, contents=_EXTRACT_PROMPT + markdown[:20000],
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(re.search(r"\{.*\}", resp.text or "", re.S).group())
        return ParsedResume(
            parser=self.name, summary=data.get("summary", ""),
            skills=[Skill(name=k.get("name", ""), category=k.get("category", "General"),
                          level=k.get("level"))
                    for k in data.get("skills", []) if k.get("name")],
            experiences=[Experience(role=e.get("role", ""), company=e.get("company", ""),
                                    start=e.get("start", ""), end=e.get("end", ""),
                                    highlights=e.get("highlights", []))
                         for e in data.get("experiences", []) if e.get("role")],
        )

    def parse(self, file_bytes: bytes, filename: str) -> ParsedResume:
        s = get_settings()
        try:
            markdown = self._to_markdown(file_bytes, filename)
        except Exception as e:
            _log("llamaparse", e)
            return MockResumeParser().parse(file_bytes, filename)
        if not s.gemini_enabled:
            print("[parser] LlamaParse OK but GEMINI_API_KEY missing — using mock structure.",
                  file=sys.stderr)
            return MockResumeParser().parse(file_bytes, filename)
        try:
            return self._structure(markdown)
        except Exception as e:
            _log("gemini-structure", e)
            return MockResumeParser().parse(file_bytes, filename)


def get_parser() -> ResumeParser:
    if get_settings().llama_enabled:
        return LlamaParseResumeParser()
    return MockResumeParser()

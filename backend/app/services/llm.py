"""Scoring, round-aware interview questions, and AI-coach chat.

`get_llm()` returns GeminiLLM when GEMINI_API_KEY is set, else HeuristicLLM.
Provider failures are printed to the server console (and surfaced via
`gemini_selftest`) instead of being silently swallowed, so misconfiguration is
visible rather than masquerading as a low score.
"""
from __future__ import annotations

import json
import re
import sys
import traceback
from typing import Protocol

from ..config import get_settings
from ..models import CoachMessage, Job, Profile, ScoreBreakdown

_STOPWORDS = {
    "and", "the", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "they", "their", "has", "was", "were", "job", "role",
    "work", "team", "ability", "experience", "years", "strong", "skills", "plus",
    "etc", "including", "such", "must", "should", "able", "who", "what", "into",
    "we", "re", "hiring", "look", "want", "help", "build", "support", "any",
}


def _log(where: str, err: Exception) -> None:
    print(f"[llm] {where} failed: {type(err).__name__}: {err}", file=sys.stderr)
    traceback.print_exc()


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", text.lower())
            if w not in _STOPWORDS}


def _profile_text(p: Profile) -> str:
    skills = ", ".join(s.name for s in p.skills)
    exp = "\n".join(
        f"- {e.role} at {e.company} ({e.start}–{e.end}): " + "; ".join(e.highlights)
        for e in p.experiences)
    return f"Summary: {p.summary}\nSkills: {skills}\nExperience:\n{exp}"


class LLMService(Protocol):
    def score(self, profile: Profile, title: str, description: str) -> ScoreBreakdown: ...
    def questions(self, profile: Profile, job: Job, round_name: str) -> list[str]: ...
    def coach(self, profile: Profile, history: list[CoachMessage], job: Job | None) -> str: ...


# --------------------------------------------------------------------------- #
# Offline heuristic
# --------------------------------------------------------------------------- #
class HeuristicLLM:
    name = "heuristic"

    def score(self, profile: Profile, title: str, description: str) -> ScoreBreakdown:
        jd = _tokens(description + " " + title)
        names = [s.name for s in profile.skills]
        matched = [n for n in names if _tokens(n) & jd]
        pt = _tokens(" ".join(names) + " " + " ".join(
            e.role + " " + " ".join(e.highlights) for e in profile.experiences))
        missing = [kw for kw in sorted(jd - pt) if len(kw) > 4][:6]
        coverage = len(matched) / max(len(jd), 1)
        depth = min(len(matched) / 6, 1.0)
        score = int(round(min(100, 40 * depth + 60 * min(coverage * 4, 1.0))))
        return ScoreBreakdown(
            score=score, method="heuristic", matched_skills=matched, missing_skills=missing,
            reasoning=(f"Matched {len(matched)} of your skills (offline keyword overlap)."))

    def questions(self, profile: Profile, job: Job, round_name: str) -> list[str]:
        c = job.company or "the company"
        by_round = {
            "HR": [f"Why do you want to work at {c}?", "Walk me through your resume in two minutes.",
                   "What are your salary expectations and availability?",
                   "Tell me about a time you handled feedback or conflict."],
            "Hiring Manager": [f"Why are you a fit for {job.title}?",
                   "Describe a project you're most proud of and your specific role.",
                   "Tell me about a time you missed a deadline — what happened?",
                   "Where do you want to grow technically in the next year?"],
            "Team Fit": ["How do you like to receive feedback from teammates?",
                   "Describe a disagreement with a teammate and how you resolved it.",
                   "What kind of team environment helps you do your best work?",
                   "How do you keep others unblocked when you're heads-down?"],
        }
        base = by_round.get(round_name, by_round["Hiring Manager"])[:]
        for kw in list(_tokens(job.description))[:3]:
            base.append(f"How have you used {kw} in your past work?")
        return base[:8]

    def coach(self, profile: Profile, history: list[CoachMessage], job: Job | None) -> str:
        last = history[-1].content if history else ""
        focus = f" for {job.title} at {job.company}" if job else ""
        return (f"(Offline coach — Gemini not connected.) For this{focus}, structure your "
                f"answer as situation → action → result. You said: \"{last[:120]}\". "
                f"Lead with a concrete example and quantify the outcome.")


# --------------------------------------------------------------------------- #
# Gemini (Google)
# --------------------------------------------------------------------------- #
class GeminiLLM:
    name = "gemini"

    def __init__(self) -> None:
        from google import genai
        s = get_settings()
        self._genai = genai
        self._client = genai.Client(api_key=s.gemini_api_key)
        self._model = s.gemini_model

    def _gen(self, prompt: str, as_json: bool = False) -> str:
        cfg = None
        if as_json:
            from google.genai import types
            cfg = types.GenerateContentConfig(response_mime_type="application/json")
        resp = self._client.models.generate_content(
            model=self._model, contents=prompt, config=cfg)
        return resp.text or ""

    def score(self, profile: Profile, title: str, description: str) -> ScoreBreakdown:
        prompt = (
            "You are a technical recruiter. Score how well the candidate fits the job on a "
            "0-100 scale. Respond ONLY with JSON: {\"score\": int, \"reasoning\": str, "
            "\"matched_skills\": [str], \"missing_skills\": [str]}.\n\n"
            f"CANDIDATE:\n{_profile_text(profile)}\n\nJOB: {title}\n{description}")
        try:
            data = json.loads(re.search(r"\{.*\}", self._gen(prompt, as_json=True), re.S).group())
            return ScoreBreakdown(
                score=int(max(0, min(100, data.get("score", 0)))),
                reasoning=data.get("reasoning", ""),
                matched_skills=data.get("matched_skills", []),
                missing_skills=data.get("missing_skills", []),
                method="llm")
        except Exception as e:
            _log("score", e)
            return HeuristicLLM().score(profile, title, description)

    def questions(self, profile: Profile, job: Job, round_name: str) -> list[str]:
        prompt = (
            f"Generate 6 interview questions for a '{round_name}' round, tailored to this job "
            "and candidate. HR = screening/motivation/logistics; Hiring Manager = role-specific "
            "competence; Team Fit = collaboration and culture. Respond ONLY with a JSON array "
            f"of strings.\n\nCANDIDATE:\n{_profile_text(profile)}\n\n"
            f"JOB: {job.title} at {job.company}\n{job.description}")
        try:
            return [str(q) for q in json.loads(
                re.search(r"\[.*\]", self._gen(prompt, as_json=True), re.S).group())][:10]
        except Exception as e:
            _log("questions", e)
            return HeuristicLLM().questions(profile, job, round_name)

    def coach(self, profile: Profile, history: list[CoachMessage], job: Job | None) -> str:
        focus = (f"\nThe candidate is focused on: {job.title} at {job.company}\n{job.description}"
                 if job else "")
        convo = "\n".join(f"{m.role.upper()}: {m.content}" for m in history)
        prompt = (
            "You are an encouraging, sharp career coach. Be concise, specific, and practical. "
            "If running a mock interview, ask one question at a time and give brief feedback.\n\n"
            f"ABOUT THE CANDIDATE:\n{_profile_text(profile)}{focus}\n\n"
            f"CONVERSATION:\n{convo}\n\nReply as the coach:")
        try:
            return self._gen(prompt).strip() or HeuristicLLM().coach(profile, history, job)
        except Exception as e:
            _log("coach", e)
            return HeuristicLLM().coach(profile, history, job)


def get_llm() -> LLMService:
    if get_settings().gemini_enabled:
        try:
            return GeminiLLM()
        except Exception as e:
            _log("init", e)
    return HeuristicLLM()


def gemini_selftest() -> dict:
    """Live ping used by /api/health so the user can see if the key actually works."""
    s = get_settings()
    if not s.gemini_enabled:
        return {"configured": False, "ok": False, "error": "GEMINI_API_KEY not set"}
    try:
        from google import genai
        client = genai.Client(api_key=s.gemini_api_key)
        r = client.models.generate_content(model=s.gemini_model, contents="Reply with: ok")
        return {"configured": True, "ok": True, "model": s.gemini_model, "sample": (r.text or "").strip()[:40]}
    except Exception as e:
        return {"configured": True, "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}

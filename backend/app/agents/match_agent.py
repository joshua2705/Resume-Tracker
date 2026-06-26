"""match_agent — score how well the user's profile fits a job description.

A small LangGraph graph (prepare -> score) that asks Gemini for *structured*
output (MatchResult), so the result is a validated JSON object, never free
text. Falls back to the existing HeuristicLLM on any failure, recording that in
the envelope meta. This is what the /score and catalog-evaluate endpoints call
when agents are active.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional, TypedDict

from ..models import Profile, ScoreBreakdown
from ..services.llm import HeuristicLLM, _profile_text
from .runtime import get_chat_model, make_meta, timer, tokens_from_message
from .schemas import AgentEnvelope, MatchResult, envelope

AGENT = "match_agent"

_SYSTEM = (
    "You are a precise technical recruiter. Score how well a candidate fits a "
    "job on a 0-100 scale. Be calibrated: 80+ means a strong, hireable match; "
    "40-60 means a stretch with real gaps. Base the score only on the evidence "
    "given. Return the structured fields exactly."
)


class _State(TypedDict, total=False):
    profile_text: str
    title: str
    description: str
    tokens: int
    result: MatchResult


def _recommendation(score: int) -> str:
    return ("strong" if score >= 75 else "moderate" if score >= 55
            else "stretch" if score >= 35 else "weak")


@lru_cache(maxsize=1)
def _graph():
    """Compile once. Lazy so importing this module never needs langgraph."""
    from langgraph.graph import END, START, StateGraph

    llm = get_chat_model(temperature=0.1)
    structured = llm.with_structured_output(MatchResult, include_raw=True)

    def score_node(state: _State) -> _State:
        prompt = (
            f"{_SYSTEM}\n\nCANDIDATE PROFILE:\n{state['profile_text']}\n\n"
            f"JOB TITLE: {state['title']}\nJOB DESCRIPTION:\n{state['description']}"
        )
        out = structured.invoke(prompt)
        parsed: MatchResult = out["parsed"]
        parsed.score = max(0, min(100, int(parsed.score)))
        if parsed.recommendation not in ("strong", "moderate", "stretch", "weak"):
            parsed.recommendation = _recommendation(parsed.score)
        return {"result": parsed, "tokens": tokens_from_message(out.get("raw"))}

    g = StateGraph(_State)
    g.add_node("score", score_node)
    g.add_edge(START, "score")
    g.add_edge("score", END)
    return g.compile()


def run(profile: Profile, title: str, description: str) -> AgentEnvelope:
    with timer() as t:
        try:
            state = _graph().invoke({
                "profile_text": _profile_text(profile),
                "title": title,
                "description": description,
            })
            result: MatchResult = state["result"]
            meta = make_meta(AGENT, timer_ms=t.ms, tokens=state.get("tokens", 0))
            return envelope(AGENT, result, meta)
        except Exception as e:  # graceful fallback to the heuristic scorer
            sb = HeuristicLLM().score(profile, title, description)
            result = MatchResult(
                score=sb.score, reasoning=sb.reasoning,
                matched_skills=sb.matched_skills, missing_skills=sb.missing_skills,
                recommendation=_recommendation(sb.score), confidence=0.3)
            meta = make_meta(AGENT, timer_ms=t.ms, method="fallback",
                             fallback=True, error=f"{type(e).__name__}: {e}"[:200])
            return envelope(AGENT, result, meta)


def to_score_breakdown(env: AgentEnvelope) -> ScoreBreakdown:
    """Adapt the agent envelope back to the app's existing ScoreBreakdown so
    routers/frontend are unchanged."""
    d = env.data
    return ScoreBreakdown(
        score=d.get("score", 0), reasoning=d.get("reasoning", ""),
        matched_skills=d.get("matched_skills", []),
        missing_skills=d.get("missing_skills", []),
        method="llm" if not env.meta.fallback_used else "heuristic",
    )

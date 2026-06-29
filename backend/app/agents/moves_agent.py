"""moves_agent — the home-screen "3 moves for today".

LangGraph flow:

    detect_change ──(unchanged)──> return cached moves   (no LLM call)
          │
       (changed)
          ▼
      generate ──> 3 structured moves ──> save cache

"detect_change" is the change-detection tool: it fingerprints the user's
skills, experience, and tracker (ids + statuses + scores). If the fingerprint
matches the last run, the cached moves are returned verbatim and NO model call
happens — satisfying "if there is no change ... no need to change the points".
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import TypedDict

from .. import store
from ..catalog import CATALOG
from ..models import Profile
from ..services.llm import HeuristicLLM
from .runtime import get_chat_model, make_meta, timer, tokens_from_message
from .schemas import AgentEnvelope, DailyMove, MovesResult, envelope

AGENT = "moves_agent"
_CACHE_KEY = "moves"

_SYSTEM = (
    "You are a career-search strategist. Given a candidate's skills, experience "
    "and their job tracker, output EXACTLY 3 concrete, high-leverage actions to "
    "take today. Each must be specific (name the role/company/skill), achievable "
    "in a day, and non-duplicative. Order by priority (1 = do first)."
)


class _State(TypedDict, total=False):
    fingerprint: str
    changed: bool
    context: str
    tokens: int
    result: MovesResult


# --- change-detection tool ----------------------------------------------- #
def state_fingerprint(profile: Profile, jobs) -> str:
    skills = "|".join(sorted(s.name.lower() for s in profile.skills))
    exp = "|".join(sorted(f"{e.role.lower()}@{e.company.lower()}" for e in profile.experiences))
    trk = "|".join(sorted(f"{j.id}:{j.status.value}:{j.score.score if j.score else '-'}"
                          for j in jobs))
    basis = f"S[{skills}]#X[{exp}]#J[{trk}]"
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def _context(profile: Profile, jobs) -> str:
    skills = ", ".join(s.name for s in profile.skills) or "(none yet)"
    exp = "; ".join(f"{e.role} at {e.company}" for e in profile.experiences) or "(none yet)"
    if jobs:
        trk = "\n".join(f"- {j.title} @ {j.company}: status={j.status.value}, "
                        f"fit={j.score.score if j.score else 'n/a'}, "
                        f"missing={', '.join(j.score.missing_skills[:4]) if j.score else ''}"
                        for j in jobs)
    else:
        trk = "(tracker empty — the candidate hasn't applied to anything yet)"
    return f"SKILLS: {skills}\nEXPERIENCE: {exp}\nTRACKER:\n{trk}"


def _heuristic_moves(profile: Profile, jobs) -> list[DailyMove]:
    """Mirror of the dashboard's offline logic, as structured moves."""
    heur = HeuristicLLM()
    has_profile = bool(profile.skills or profile.experiences)
    moves: list[DailyMove] = []
    if not has_profile:
        return [
            DailyMove(text="Upload your resume to build your skills mind map.",
                      category="profile", priority=1),
            DailyMove(text="Browse the Jobs tab and evaluate your fit.",
                      category="explore", priority=2),
            DailyMove(text="Open the AI Coach to plan your search.",
                      category="prep", priority=3),
        ]
    scored = sorted(((c, heur.score(profile, c.title, c.description)) for c in CATALOG),
                    key=lambda x: x[1].score, reverse=True)
    if scored and scored[0][1].missing_skills:
        c, sb = scored[0]
        moves.append(DailyMove(
            text=f"Add {min(2, len(sb.missing_skills))} missing skills to beat the "
                 f"{c.title} role ({sb.score}% → {min(100, sb.score + 12)}%).",
            category="skills", priority=1))
    needs_prep = [j for j in jobs if j.status.value in ("Applied", "Interviewing") and not j.prep]
    if needs_prep:
        moves.append(DailyMove(
            text=f"Prep interview questions for your {needs_prep[0].company or 'tracked'} role.",
            category="prep", priority=2))
    applied = [j for j in jobs if j.status.value == "Applied"]
    if applied:
        moves.append(DailyMove(
            text=f"Follow up on {len(applied)} application(s) sitting in \"Applied\".",
            category="applications", priority=3))
    extras = [
        DailyMove(text="Browse new roles in the Jobs tab.", category="explore", priority=4),
        DailyMove(text="Review your mind map and add any missing skills.",
                  category="profile", priority=4),
        DailyMove(text="Run a mock interview with the AI Coach.", category="prep", priority=4),
    ]
    i = 0
    while len(moves) < 3:
        moves.append(extras[i % len(extras)])
        i += 1
    return moves[:3]


@lru_cache(maxsize=1)
def _graph():
    from langgraph.graph import END, START, StateGraph

    llm = get_chat_model(temperature=0.3)
    structured = llm.with_structured_output(MovesResult, include_raw=True)

    def detect_change(state: _State) -> _State:
        cached = store.get_agent_state(_CACHE_KEY) or {}
        changed = cached.get("fingerprint") != state["fingerprint"]
        st: _State = {"changed": changed}
        if not changed and cached.get("moves"):
            res = MovesResult(moves=[DailyMove(**m) for m in cached["moves"]],
                              changed=False, fingerprint=state["fingerprint"])
            st["result"] = res
        return st

    def generate(state: _State) -> _State:
        prompt = (f"{_SYSTEM}\n\n{state['context']}\n\n"
                  "Return exactly 3 moves.")
        out = structured.invoke(prompt)
        res: MovesResult = out["parsed"]
        res.moves = res.moves[:3]
        res.changed = True
        res.fingerprint = state["fingerprint"]
        store.save_agent_state(_CACHE_KEY, {
            "fingerprint": state["fingerprint"],
            "moves": [m.model_dump() for m in res.moves],
        })
        return {"result": res, "tokens": tokens_from_message(out.get("raw"))}

    def route(state: _State) -> str:
        return "cache" if not state["changed"] else "generate"

    g = StateGraph(_State)
    g.add_node("detect_change", detect_change)
    g.add_node("generate", generate)
    g.add_edge(START, "detect_change")
    g.add_conditional_edges("detect_change", route, {"cache": END, "generate": "generate"})
    g.add_edge("generate", END)
    return g.compile()


def run(profile: Profile, jobs) -> AgentEnvelope:
    fp = state_fingerprint(profile, jobs)
    with timer() as t:
        try:
            state = _graph().invoke({"fingerprint": fp, "context": _context(profile, jobs)})
            result: MovesResult = state["result"]
            method = "cache" if not result.changed else "agent"
            meta = make_meta(AGENT, timer_ms=t.ms, tokens=state.get("tokens", 0),
                             method=method)
            return envelope(AGENT, result, meta)
        except Exception as e:
            result = MovesResult(moves=_heuristic_moves(profile, jobs), changed=True,
                                 fingerprint=fp)
            store.save_agent_state(_CACHE_KEY, {
                "fingerprint": fp, "moves": [m.model_dump() for m in result.moves]})
            meta = make_meta(AGENT, timer_ms=t.ms, method="fallback", fallback=True,
                             error=f"{type(e).__name__}: {e}"[:200])
            return envelope(AGENT, result, meta)

"""Shared runtime for the agents: the Gemini chat model, LangSmith tracing
setup, and small helpers for timing / token accounting / envelope meta.

All langchain imports are lazy so importing this module never breaks the app
when the agent stack isn't installed.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Optional

from ..config import get_settings
from .schemas import AgentMeta

_langsmith_ready = False


def configure_langsmith() -> bool:
    """Enable LangSmith tracing process-wide if a key is configured.

    LangChain/LangGraph auto-trace every run once these env vars are set, so we
    just translate our Settings into the env the SDK expects. Idempotent.
    """
    global _langsmith_ready
    if _langsmith_ready:
        return True
    s = get_settings()
    if not s.langsmith_enabled:
        return False
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ["LANGCHAIN_API_KEY"] = s.langsmith_api_key
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = s.langsmith_project
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    _langsmith_ready = True
    return True


def get_chat_model(temperature: float = 0.2, **kwargs: Any):
    """Return a configured ChatGoogleGenerativeAI (Gemini). Raises if the
    package/key is missing — callers decide whether to fall back."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    configure_langsmith()
    s = get_settings()
    if not s.gemini_enabled:
        raise RuntimeError("GEMINI_API_KEY not set")
    return ChatGoogleGenerativeAI(
        model=s.gemini_model,
        google_api_key=s.gemini_api_key,
        temperature=temperature,
        **kwargs,
    )


def tokens_from_message(message: Any) -> int:
    """Best-effort token count from an AIMessage's usage metadata."""
    try:
        um = getattr(message, "usage_metadata", None)
        if um:
            return int(um.get("total_tokens") or 0)
        meta = getattr(message, "response_metadata", {}) or {}
        usage = meta.get("usage_metadata") or meta.get("token_usage") or {}
        return int(usage.get("total_tokens") or usage.get("total_token_count") or 0)
    except Exception:
        return 0


def estimate_tokens(text: str) -> int:
    """Rough estimate (~4 chars/token) for budgeting before a call is made."""
    return max(1, len(text or "") // 4)


class Timer:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    @property
    def ms(self) -> int:
        return int((time.perf_counter() - self._t0) * 1000)


@contextmanager
def timer():
    t = Timer()
    yield t


def make_meta(agent: str, *, timer_ms: int = 0, tokens: int = 0,
              method: str = "agent", fallback: bool = False,
              error: Optional[str] = None) -> AgentMeta:
    s = get_settings()
    return AgentMeta(
        agent=agent,
        model=s.gemini_model if not fallback else "heuristic",
        method=method,                       # "agent" | "fallback" | "cache"
        fallback_used=fallback,
        latency_ms=timer_ms,
        tokens_used=tokens,
        trace_project=s.langsmith_project if s.langsmith_enabled else None,
        error=error,
    )

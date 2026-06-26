"""Agentic layer (LangGraph).

Four single-responsibility agents, each a LangGraph graph that emits a typed
JSON envelope (see schemas.py) rather than free text:

  match_agent  – score a job description against the user's profile.
  moves_agent  – recompute the home-screen "3 moves for today", but ONLY when
                 the profile or tracker actually changed (change detection).
  coach_agent  – ReAct chat agent; decides on its own which tools to call
                 (skills / experience / tracked jobs / a job's description).
  gmail_agent  – once a day, reads Gmail via an MCP server and proposes/apply
                 tracker status updates for companies the user is pursuing.

There is intentionally NO supervisor agent: the four are triggered by different
events (HTTP request, dashboard load, daily schedule) and never need to
negotiate at runtime, so a router/orchestrator (orchestrator.py) is enough and
a supervisor would only add latency and cost. See AGENTS.md for the rationale.

Everything here imports its heavy deps (langgraph / langchain) lazily, so the
FastAPI app still boots and runs in offline/heuristic mode when the agent
packages or keys are absent.
"""
from __future__ import annotations


def agents_importable() -> bool:
    """True when the LangGraph/LangChain stack is installed."""
    try:
        import langgraph  # noqa: F401
        import langchain_google_genai  # noqa: F401
        return True
    except Exception:
        return False

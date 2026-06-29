# Agentic layer — architecture

The Resume Tracker is now agentic via **LangGraph**. Four single-responsibility
agents sit behind the existing FastAPI routes; everything degrades to the
original heuristic/Gemini path when keys or packages are absent, so the app
still runs fully offline.

```
backend/app/
  agents/
    __init__.py        agents_importable() — is the langgraph stack installed?
    schemas.py         JSON contracts: AgentEnvelope + typed payloads (the "structured
                       manner using JSONs" every agent speaks)
    runtime.py         Gemini chat model, LangSmith setup, timing/token helpers
    tools.py           store-backed LangChain tools for the coach
    mcp_client.py      Gmail MCP → LangChain tools (langchain-mcp-adapters)
    match_agent.py     graph: prepare → score      (MatchResult)
    moves_agent.py     graph: detect_change → generate/cache   (MovesResult)
    coach_agent.py     prebuilt ReAct agent + tools (CoachResult)
    gmail_agent.py     ReAct + Gmail MCP, applies tracker updates (GmailScanResult)
    orchestrator.py    the ONE dispatcher routers call (agent vs fallback)
    scheduler.py       in-process daily Gmail scan loop
  guardrails/
    input_validation.py   length / sanitize / injection-flagging
    rate_limit.py         requests-per-min + daily token budget
  skills/
    coach/ daily_moves/ job_match/ gmail_tracking/  → SKILL.md each
```

## Structured messages
No agent returns bare text. Each returns an `AgentEnvelope`:
```json
{ "schema_version": "1.0", "agent": "match_agent", "ok": true,
  "data": { ...typed payload... },
  "meta": { "model": "gemini-2.0-flash", "method": "agent",
            "fallback_used": false, "latency_ms": 812, "tokens_used": 1340,
            "trace_project": "resume-tracker" } }
```
Routers, the scheduler, and any agent-to-agent handoff exchange these models.

## Why there is no supervisor agent
The brief said to add a supervisor *only if needed*. It isn't:

- The four agents are triggered by **unrelated events** — an HTTP request to
  `/score`, a dashboard load, a chat POST, a daily timer — and never need to
  collaborate within a single turn.
- A supervisor's value is dynamic routing/delegation among agents mid-task.
  Here the routing is static and known at the call site, so a supervisor would
  add a model round-trip (latency + tokens + a failure point) for zero benefit.

Instead, `orchestrator.py` is a plain, deterministic dispatcher: it checks
`agents_ready()` and calls the right agent or the existing fallback. If agents
ever need to chain at runtime (e.g. moves → match → gmail in one flow), promote
the orchestrator to a LangGraph supervisor then — the envelopes already make
agents composable.

## Tracing
LangSmith auto-traces every graph/agent run once `LANGSMITH_API_KEY` is set
(`runtime.configure_langsmith()` translates Settings → env on startup). Project:
`LANGSMITH_PROJECT` (default `resume-tracker`).

## Control surface
`GET /api/agents/status`, `POST /api/agents/gmail/scan`,
`GET /api/agents/gmail/log`, `POST /api/agents/moves/refresh`,
plus `agents` block in `GET /api/health`.

See `SETUP_AGENTS.md` for what to configure.

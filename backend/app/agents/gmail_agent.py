"""gmail_agent — daily inbox scan that auto-updates the tracker.

Once a day it:
  1. collects the companies the user is pursuing (jobs with gmail_tracking on,
     or every tracked job if none are explicitly flagged),
  2. uses the Gmail MCP tools (via a LangGraph ReAct agent) to find recent
     emails from those companies and classify each into a tracker status,
  3. returns structured proposals and APPLIES the safe ones (forward-only
     progression, or a rejection) to the store.

Everything is async because the MCP transport is. Results are logged to
agent_state["gmail_log"] and traced in LangSmith.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .. import store
from ..config import get_settings
from ..models import JobStatus
from .mcp_client import load_gmail_tools
from .runtime import configure_langsmith, get_chat_model, make_meta, timer
from .schemas import AgentEnvelope, GmailScanResult, GmailUpdateProposal, envelope

AGENT = "gmail_agent"
_LOG_KEY = "gmail_log"
_APPLY_CONFIDENCE = 0.6

# Forward-only progression guard. A scanned email may advance a job but not
# silently regress it; a rejection is allowed from any state.
_RANK = {JobStatus.saved: 0, JobStatus.applied: 1,
         JobStatus.interviewing: 2, JobStatus.offer: 3}

_SYSTEM = (
    "You are an assistant that maintains a job-application tracker from Gmail. "
    "You are given a list of tracked jobs (job_id, company, current_status). "
    "For EACH job, use the Gmail tools to search the user's mailbox for recent "
    "messages from that company about their application (interview invites, "
    "assessments, offers, rejections, recruiter replies). Read the most "
    "relevant message if needed. Then classify the application's current state "
    "into exactly one of: Saved, Applied, Interviewing, Offer, Rejected.\n"
    "Rules: propose a change ONLY when the evidence clearly shows a new state "
    "that differs from current_status. Interview/assessment invite => "
    "Interviewing. Offer/congratulations => Offer. 'Unfortunately'/not moving "
    "forward => Rejected. If there is no relevant email, do not propose a "
    "change for that job. Always cite the email subject, a short snippet, the "
    "date, and threadId as evidence. Return the structured result."
)


def _tracked_targets():
    jobs = store.list_jobs()
    flagged = [j for j in jobs if j.gmail_tracking]
    targets = flagged or jobs
    # only jobs with a real company name are searchable
    return [j for j in targets if j.company.strip()]


def _instruction(targets, lookback_days: int) -> str:
    lines = [f"- job_id={j.id} | company=\"{j.company}\" | current_status={j.status.value}"
             for j in targets]
    return (f"Look back {lookback_days} day(s). Tracked jobs:\n" + "\n".join(lines) +
            "\n\nScan Gmail and return proposals only for jobs whose status should change.")


def _apply(proposals: list[GmailUpdateProposal]) -> tuple[int, list[str]]:
    applied, errors = 0, []
    for p in proposals:
        try:
            if p.confidence < _APPLY_CONFIDENCE:
                continue
            job = store.get_job(p.job_id)
            if not job:
                errors.append(f"job {p.job_id} not found")
                continue
            try:
                new_status = JobStatus(p.new_status)
            except ValueError:
                errors.append(f"bad status '{p.new_status}' for {p.job_id}")
                continue
            old = job.status
            forward = _RANK.get(new_status, -1) > _RANK.get(old, -1)
            if new_status == JobStatus.rejected or forward:
                job.status = new_status
                store.upsert_job(job)
                p.applied = True
                p.old_status = old.value
                applied += 1
        except Exception as e:  # never let one bad proposal abort the batch
            errors.append(f"{p.job_id}: {type(e).__name__}: {e}")
    return applied, errors


async def run(lookback_days: int | None = None) -> AgentEnvelope:
    from langgraph.prebuilt import create_react_agent

    configure_langsmith()
    s = get_settings()
    lookback = lookback_days if lookback_days is not None else s.gmail_scan_lookback_days
    targets = _tracked_targets()

    with timer() as t:
        if not targets:
            res = GmailScanResult(lookback_days=lookback,
                                  errors=["no tracked jobs with a company to scan"])
            return envelope(AGENT, res, make_meta(AGENT, timer_ms=t.ms), ok=True)
        try:
            tools = await load_gmail_tools()
            llm = get_chat_model(temperature=0.0)
            agent = create_react_agent(llm, tools, prompt=_SYSTEM,
                                       response_format=GmailScanResult)
            state = await agent.ainvoke(
                {"messages": [("user", _instruction(targets, lookback))]})
            res: GmailScanResult = state.get("structured_response") or GmailScanResult()
            res.lookback_days = lookback
            res.scanned_companies = sorted({j.company for j in targets})
            applied, errors = _apply(res.proposals)
            res.applied_count = applied
            res.skipped_no_change = len(targets) - len(res.proposals)
            res.errors = list(res.errors or []) + errors
            _save_log(res, fallback=False)
            return envelope(AGENT, res, make_meta(AGENT, timer_ms=t.ms))
        except Exception as e:
            res = GmailScanResult(
                lookback_days=lookback,
                scanned_companies=sorted({j.company for j in targets}),
                errors=[f"{type(e).__name__}: {e}"[:300]])
            _save_log(res, fallback=True)
            meta = make_meta(AGENT, timer_ms=t.ms, method="fallback", fallback=True,
                             error=f"{type(e).__name__}: {e}"[:200])
            return envelope(AGENT, res, meta, ok=False)


def _save_log(res: GmailScanResult, fallback: bool) -> None:
    log = store.get_agent_state(_LOG_KEY) or []
    if not isinstance(log, list):
        log = []
    log.append({
        "at": datetime.now(timezone.utc).isoformat(),
        "applied": res.applied_count,
        "proposals": len(res.proposals),
        "errors": res.errors,
        "fallback": fallback,
    })
    store.save_agent_state(_LOG_KEY, log[-30:])  # keep last 30 runs

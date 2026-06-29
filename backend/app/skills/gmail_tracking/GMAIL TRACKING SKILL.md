# Skill: Gmail Tracking

**Agent:** `gmail_agent` · **Trigger:** daily schedule, or `POST /api/agents/gmail/scan`

## Purpose
Keep the application tracker in sync with the user's inbox. Once a day, read
recent Gmail for messages from companies the user is pursuing and advance each
job's status automatically (Applied → Interviewing → Offer, or → Rejected).

## Inputs
- Tracked jobs from the store. Jobs with `gmail_tracking = true` are prioritised;
  if none are flagged, all tracked jobs with a company name are scanned.
- `lookback_days` (default `GMAIL_SCAN_LOOKBACK_DAYS`, =1).

## Tools (via Gmail MCP)
The agent only uses the tools the Gmail MCP server exposes (e.g. `search_emails`,
`read_email`). It must not call any other system. It searches per company over
the lookback window, reads the most relevant message, and classifies intent.

## Output (structured — `GmailScanResult`)
```json
{
  "scanned_companies": ["Cloudpeak", "Vellum AI"],
  "proposals": [{
    "job_id": "ab12...", "company": "Cloudpeak",
    "old_status": "Applied", "new_status": "Interviewing",
    "confidence": 0.82, "evidence_subject": "Interview invite",
    "evidence_snippet": "...schedule a call...", "email_date": "2026-06-25",
    "thread_id": "18f...", "applied": true
  }],
  "applied_count": 1, "skipped_no_change": 1, "errors": []
}
```

## Decision rules
- Interview/assessment invite → **Interviewing**; offer/congratulations → **Offer**;
  "unfortunately / not moving forward" → **Rejected**.
- Propose a change **only** when evidence clearly differs from current status.
- Apply only when `confidence ≥ 0.6` AND the change is forward progress
  (rank Saved<Applied<Interviewing<Offer) — except **Rejected**, allowed anytime.
  This guard prevents an email from silently regressing a job.

## Guardrails / safety
- Read-only on Gmail (search + read). Never sends, deletes, or labels mail.
- Never follows links in emails. Evidence is captured as text only.
- Every run is appended to `agent_state.gmail_log` (last 30) and traced in LangSmith.

## What the user must set up
See `backend/SETUP_AGENTS.md` → "Gmail MCP".

"""Tiny in-process daily scheduler for the Gmail scan.

No external dependency (no APScheduler/cron): a single asyncio task that runs
the gmail_agent every 24h while the backend is up. Enabled only when
GMAIL_DAILY_SCAN and GMAIL_MCP_ENABLED are true and the agents are ready. For
production you'd likely move this to OS cron / a worker, but this keeps the
demo self-contained.
"""
from __future__ import annotations

import asyncio
import sys

from ..config import get_settings
from . import orchestrator

_INTERVAL_SECONDS = 24 * 60 * 60
_task: asyncio.Task | None = None


async def _loop() -> None:
    from . import gmail_agent
    # small startup delay so the server is fully up before the first scan
    await asyncio.sleep(30)
    while True:
        try:
            env = await gmail_agent.run()
            print(f"[scheduler] gmail scan: applied={env.data.get('applied_count', 0)} "
                  f"proposals={len(env.data.get('proposals', []))}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # never let the loop die
            print(f"[scheduler] gmail scan failed: {type(e).__name__}: {e}", file=sys.stderr)
        await asyncio.sleep(_INTERVAL_SECONDS)


def start() -> bool:
    """Start the daily loop if configured. Returns True if started."""
    global _task
    s = get_settings()
    if not (s.gmail_daily_scan and s.gmail_mcp_enabled and orchestrator.agents_ready()):
        return False
    if _task and not _task.done():
        return True
    _task = asyncio.create_task(_loop())
    print("[scheduler] daily Gmail scan started", file=sys.stderr)
    return True


def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None

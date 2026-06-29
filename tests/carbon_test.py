"""7.3 Carbon footprint — LIVE (real token usage from Gemini).

Each agent task is run against the live model and the REAL token count is read
from the envelope meta (meta.tokens_used, populated from Gemini usage_metadata).
Tokens -> energy (kWh) -> CO2 (gCO2eq) with public reference numbers, then a
monthly projection at a target MAU and an SLM-substitution estimate.

The Gmail scan needs the Gmail MCP server (npx) + prior OAuth; if it isn't
available in the run environment it is reported as 'unavailable' and excluded
from totals (re-run on a machine with the MCP configured to include it).
Results -> tests/results/carbon.json
"""
from __future__ import annotations

import asyncio
import os
import statistics as stats

import _harness as H
from app.agents import match_agent, moves_agent, coach_agent
from app.agents.runtime import estimate_tokens
from app.models import CoachMessage

REPEATS = int(os.getenv("TEST_CARBON_REPEATS", "2"))

# Reference constants (labelled, adjustable, order-of-magnitude).
KWH_PER_1K_TOKENS = 0.0003          # 0.3 Wh / 1k tokens (frontier reference)
SLM_KWH_PER_1K_TOKENS = 0.00003     # ~10x lower for a 1-3B specialised SLM
GRIDS = {"France": 60, "EU_avg": 250, "US_avg": 380}
MAU = 10_000
TASKS_PER_USER_PER_MONTH = {"match_score": 20, "daily_moves": 22,
                            "coach_turn": 30, "gmail_scan": 22}


def kwh(tokens, intensity=KWH_PER_1K_TOKENS):
    return tokens / 1000.0 * intensity


def gco2(k, grid="France"):
    return k * GRIDS[grid]


def _avg_tokens(run_fn, label, reset_each=False):
    toks, calls, methods = [], [], []
    for _ in range(REPEATS):
        if reset_each:
            H.reset_store()
        env = H.live_run(run_fn, label=label)
        toks.append(env.meta.tokens_used or 0)
        methods.append(env.meta.method)
    return {"tokens": round(stats.mean(toks)), "samples": toks, "methods": methods}


def task_match():
    p = H.base_profile()
    title = "Junior Data Analyst"
    desc = ("Write SQL, build Tableau dashboards, analyse data in Python (pandas), and "
            "communicate findings to non-technical stakeholders. Internships count.")
    H.reset_store(); H.seed_profile(p)
    r = _avg_tokens(lambda: match_agent.run(p, title, desc), "match")
    return {"task": "match_score", "calls": 1, **r}


def task_moves():
    p = H.base_profile()
    # reset_each clears the moves cache so we measure a real generation each time
    r = _avg_tokens(lambda: (H.seed_profile(p), moves_agent.run(p, []))[1],
                    "moves", reset_each=True)
    return {"task": "daily_moves", "calls": 1, **r}


def task_coach():
    p = H.base_profile()
    hist = [CoachMessage(role="user",
                         content="How should I answer 'tell me about a project you are proud of'?")]
    H.reset_store(); H.seed_profile(p)
    r = _avg_tokens(lambda: coach_agent.run(p, hist, None), "coach")
    return {"task": "coach_turn", "calls": "1-3 (ReAct)", **r}


def task_gmail():
    """Best-effort live Gmail scan; needs the Gmail MCP. Reported separately."""
    from app.agents import gmail_agent
    H.reset_store(jobs=[H.make_job(company="Cloudpeak")])   # default status = Applied
    try:
        env = asyncio.run(asyncio.wait_for(gmail_agent.run(lookback_days=1), timeout=120))
        return {"task": "gmail_scan", "available": True, "tokens": env.meta.tokens_used or 0,
                "method": env.meta.method, "errors": env.data.get("errors", [])[:3]}
    except Exception as e:
        return {"task": "gmail_scan", "available": False, "tokens": None,
                "note": f"MCP unavailable: {type(e).__name__}: {str(e)[:80]}"}


def main():
    H.require_live()
    print(f"[carbon] LIVE token measurement against {H.MODEL} (x{REPEATS} each)")
    tasks = [task_match(), task_moves(), task_coach()]
    gmail = task_gmail()
    H.flush_traces()

    table = []
    for t in tasks:
        k = kwh(t["tokens"])
        table.append({"task": t["task"], "model": H.MODEL, "calls": t["calls"],
                      "tokens_per_task": t["tokens"], "token_samples": t["samples"],
                      "methods": t["methods"], "kwh_per_task": round(k, 9),
                      "gco2_per_task": {g: round(gco2(k, g), 4) for g in GRIDS}})
    if gmail.get("available"):
        k = kwh(gmail["tokens"])
        table.append({"task": "gmail_scan", "model": H.MODEL, "calls": "1+N",
                      "tokens_per_task": gmail["tokens"], "kwh_per_task": round(k, 9),
                      "gco2_per_task": {g: round(gco2(k, g), 4) for g in GRIDS}})

    # monthly projection from measured tokens
    tok_by_task = {t["task"]: t["tokens"] for t in tasks}
    if gmail.get("available"):
        tok_by_task["gmail_scan"] = gmail["tokens"]
    monthly, total_tokens = {}, 0
    for task, per_month in TASKS_PER_USER_PER_MONTH.items():
        if task not in tok_by_task:
            continue
        n = per_month * MAU
        toks = tok_by_task[task] * n
        total_tokens += toks
        k = kwh(toks)
        monthly[task] = {"tasks_per_month": n, "tokens_per_month": toks,
                         "kwh_per_month": round(k, 3),
                         "gco2_per_month": {g: round(gco2(k, g)) for g in GRIDS}}
    total_k = kwh(total_tokens)
    monthly_total = {"tokens_per_month": total_tokens, "kwh_per_month": round(total_k, 2),
                     "kg_co2_per_month": {g: round(gco2(total_k, g) / 1000.0, 1) for g in GRIDS}}

    # SLM substitution on the measured match_score call
    m_tokens = tok_by_task["match_score"]
    n_match = TASKS_PER_USER_PER_MONTH["match_score"] * MAU
    slm = {"substituted_call": "match_score (fit scoring)", "measured_tokens_per_task": m_tokens,
           "frontier": {"model": H.MODEL,
                        "gco2_per_month_France": round(gco2(kwh(m_tokens * n_match)))},
           "slm": {"model": "fine-tuned 1-3B SLM (Phi-3-mini / Llama-3.2-3B)",
                   "gco2_per_month_France": round(gco2(kwh(m_tokens * n_match, SLM_KWH_PER_1K_TOKENS)))},
           "energy_reduction_pct": round(100 * (1 - SLM_KWH_PER_1K_TOKENS / KWH_PER_1K_TOKENS), 1),
           "quality_tradeoff": ("Fit scoring is schema-bound (0-100 + matched/missing skills); "
                                "a small fine-tuned model should keep ~90-95% of ranking quality. "
                                "Keep the frontier model only for open-ended coach chat. The "
                                "existing heuristic scorer is the 0-energy floor already in prod.")}

    out = {"category": "carbon",
           "assumptions": {"kwh_per_1k_tokens_frontier": KWH_PER_1K_TOKENS,
                           "kwh_per_1k_tokens_slm": SLM_KWH_PER_1K_TOKENS,
                           "grids_gco2_per_kwh": GRIDS, "MAU": MAU,
                           "tasks_per_user_per_month": TASKS_PER_USER_PER_MONTH,
                           "tokens": "REAL meta.tokens_used from Gemini usage_metadata",
                           "repeats_per_task": REPEATS},
           "per_task": table, "gmail_scan": gmail,
           "monthly_projection": monthly, "monthly_total": monthly_total,
           "slm_substitution": slm}
    H.write_result("carbon.json", out)

    print("[carbon] measured tokens & gCO2eq (France grid):")
    for r in table:
        print(f"   {r['task']:12s} {r['tokens_per_task']:5d} tok  "
              f"{r['kwh_per_task']*1000:.4f} Wh  {r['gco2_per_task']['France']:.4f} gCO2eq")
    if not gmail.get("available"):
        print(f"   gmail_scan   {gmail.get('note')}")
    print(f"   MONTHLY TOTAL @ {MAU} MAU: {monthly_total['kwh_per_month']} kWh, "
          f"{monthly_total['kg_co2_per_month']} kgCO2eq")
    return out


if __name__ == "__main__":
    main()

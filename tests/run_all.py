"""Run all four Deliverable-7 categories LIVE (real Gemini + LangSmith), write
results/*.json, results/summary.json, and regenerate results/REPORT.md.

    python tests/run_all.py

Requires backend/.env with GEMINI_API_KEY (+ LANGSMITH_API_KEY) and the agent
stack installed. Tune for quota: TEST_PACE_SECONDS, TEST_N_JOBS, TEST_CARBON_REPEATS.
"""
from __future__ import annotations

import datetime as _dt

import _harness as H
import robustness_test
import bias_test
import carbon_test
import explainability_test
import gen_report


def main():
    H.require_live()
    print("=" * 64)
    rob = robustness_test.main(); print("-" * 64)
    bia = bias_test.main(); print("-" * 64)
    car = carbon_test.main(); print("-" * 64)
    exp = explainability_test.main(); print("=" * 64)

    fb = rob.get("fallback_runs", 0) + bia.get("total_fallback_runs", 0)
    live_calls = rob.get("live_coach_calls", 0)
    executed_live = (fb == 0) and (live_calls > 0 or H.LIVE)

    bias_dims = {}
    for d in bia["dimensions"]:
        bias_dims[d["dimension"]] = {
            "parity_gap_pp": d["demographic_parity_gap_pp"],
            "max_job_gap_pp": d["max_per_job_gap_pp"],
            "means": d["slice_mean_score"],
            "exceeds_threshold": d["exceeds_threshold"],
        }

    summary = {
        "executed_live": executed_live,
        "model": H.MODEL,
        "langsmith_project": H.LANGSMITH_PROJECT,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "robustness": {
            "passed": rob["passed"], "n": rob["n_inputs"],
            "pass_rate_pct": rob["overall_pass_rate_pct"],
            "fallback_runs": rob.get("fallback_runs", 0),
            "by_category": {k: v["pass_rate_pct"] for k, v in rob["by_category"].items()},
        },
        "bias": {"n": bia["n_inputs_total"],
                 "fallback_runs": bia.get("total_fallback_runs", 0),
                 "dimensions": bias_dims},
        "carbon": {"per_task_tokens": {r["task"]: r["tokens_per_task"] for r in car["per_task"]},
                   "monthly_total": car["monthly_total"],
                   "slm_energy_reduction_pct": car["slm_substitution"]["energy_reduction_pct"]},
        "explainability": {"n": exp["n_decisions_sampled"],
                           "trace_complete_pct": exp["trace_complete_pct"],
                           "user_dist": exp["user_explanation_distribution"],
                           "langsmith": exp["langsmith_evidence"].get("available")},
    }
    H.write_result("summary.json", summary)
    gen_report.build()
    print("wrote results/summary.json and results/REPORT.md")
    if not executed_live:
        print("\n*** WARNING: run was NOT fully live (fallbacks detected). "
              "Re-run on a machine with network access to the Gemini API. ***")
    return summary


if __name__ == "__main__":
    main()

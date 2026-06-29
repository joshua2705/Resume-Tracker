# Tests : robustness, bias, carbon, explainability

These tests run **online** against the real Gemini model configured in
`backend/.env`, through the actual LangGraph agents, with every run traced to
**LangSmith**. Nothing is mocked or offline. The headline artefact is
[`results/REPORT.md`](results/REPORT.md) (regenerated from each run); raw numbers
are the JSON files in `results/`.

## Run it (on a machine with network access to the Gemini API)

```bash
cd backend && pip install -r requirements.txt && pip install pyyaml && cd ..
python tests/run_all.py
```

`run_all.py` runs all four categories, writes `results/*.json`, `summary.json`,
and regenerates `results/REPORT.md`. It stamps `executed_live` and prints a
WARNING if any agent call fell back (e.g. no network / quota), so a non-live run
can't be mistaken for a live one.

### Quota / pacing knobs (env vars)

| Var | Default | Meaning |
|---|---|---|
| `TEST_PACE_SECONDS` | 1.5 | sleep between live model calls |
| `TEST_N_JOBS` | 5 | jobs per bias proxy slice (more = more calls) |
| `TEST_CARBON_REPEATS` | 2 | repeats per carbon task (averaged) |

A full live run is ~120–160 Gemini calls; raise `TEST_PACE_SECONDS` if you hit
free-tier 429s (the harness also auto-backs-off on quota errors).

## What each file does

| File | Purpose |
|---|---|
| `_harness.py` | path shim, live-mode assert, throwaway store, `live_run()` (quota backoff), fixtures, LangSmith flush |
| `data/adversarial_inputs.yaml` | the adversarial input set for 7.1 |
| `robustness_test.py` | 7.1 — guardrail + **real coach agent** (prompt-leak & refusal checks), injected model outage, gmail apply guard |
| `bias_test.py` | 7.2 — gender / age / language slices scored by the **real match_agent** |
| `carbon_test.py` | 7.3 — **real** `meta.tokens_used` → kWh → gCO₂eq, monthly + SLM |
| `explainability_test.py` | 7.4 — real-agent envelopes, trace completeness, GDPR Art 22, LangSmith run capture |
| `gen_report.py` | renders `results/REPORT.md` from the JSON results |
| `run_all.py` | runs everything + writes summary + report |

## Notes

- LangSmith traces land in the project named by `LANGSMITH_PROJECT` (`.env`).
  `explainability.json` also pulls the recent run IDs/URLs as evidence.
- The Gmail-scan carbon row needs the Gmail MCP server (npx) + prior OAuth; if it
  isn't configured it is reported `unavailable` and excluded from totals.

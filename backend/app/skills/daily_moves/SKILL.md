# Skill: Daily Moves

**Agent:** `moves_agent` · **Trigger:** dashboard load (`GET /api/dashboard`), or
`POST /api/agents/moves/refresh`

## Purpose
Produce the **3 "moves for today"** shown on the home screen — concrete,
high-leverage actions tailored to the user's skills, experience, and tracker.

## Change detection (the "tool to see if it needs change")
Before calling the model, the agent computes a fingerprint over:
- skill names, experience (role@company), and the tracker (job id + status + score).

If the fingerprint matches the last run, the agent returns the **cached** moves
and makes **no model call**. The moves only change when the user's skills,
experience, or job tracker actually changed — exactly as required.

## Output (structured — `MovesResult`)
```json
{
  "moves": [
    {"text": "Add 2 missing skills to beat the SWE I role (62% → 74%).",
     "rationale": "...", "category": "skills", "priority": 1}
  ],
  "changed": true,
  "fingerprint": "9af3c1d2e4b5a6c7"
}
```
Categories: `skills | applications | prep | explore | profile`.

## Fallback
On any model error the agent emits the same 3-move structure from the offline
heuristic (mirrors the original dashboard logic), so the home screen always
renders.

## Cache location
`agent_state.moves = { fingerprint, moves[] }` in the JSON store.

# Skill: Job Match

**Agent:** `match_agent` · **Trigger:** `POST /api/score`,
`POST /api/catalog/{id}/evaluate`, and on apply.

## Purpose
Score how well the user's profile (skills + experience) matches a job
description, with the gaps spelled out.

## Flow (LangGraph: `prepare → score`)
Serializes the profile, then asks Gemini for **structured output** (`MatchResult`)
— a validated object, never free text.

## Output (structured — `MatchResult`)
```json
{
  "score": 72,
  "reasoning": "Strong Python/SQL match; lacks cloud deployment evidence.",
  "matched_skills": ["Python", "SQL", "pandas"],
  "missing_skills": ["Docker", "AWS"],
  "recommendation": "moderate",   // strong | moderate | stretch | weak
  "confidence": 0.78
}
```
It is adapted back to the app's existing `ScoreBreakdown` so the frontend and
the per-(job,profile) evaluation cache are unchanged.

## Calibration
80+ = strong/hireable; 55–74 = moderate; 35–54 = stretch; <35 = weak. Score is
based only on supplied evidence — the agent must not invent skills.

## Fallback
Any failure → the offline `HeuristicLLM.score` (keyword overlap), flagged via
`meta.fallback_used = true`.

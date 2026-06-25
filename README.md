# Resume Tracker

A career copilot: upload resumes → build an editable mind map of your skills &
experience → browse jobs and get an AI fit score → prep interview questions by
round → track applications on a draggable board → chat with an AI coach.

Two-tier app, each piece swappable without touching the rest: **FastAPI**
backend (parsing, scoring, storage, coach) + **React/Vite** frontend (hand-drawn
UI). Runs **fully offline** out of the box (mock parser + heuristic scoring) and
upgrades to **LlamaParse + Gemini** by adding two keys.

## Screens

| Tab | What it does |
| --- | --- |
| **Dashboard** | Greets you by name, summarizes stats, and the AI coach lists your "moves for today". |
| **Resumes** | Upload many resumes (cards); one is **active**. Editable skills/experience **mind map** below — click any node to edit; experiences show the title and open full details on click. |
| **Jobs** | Hardcoded tech entry-level roles. Click one → AI evaluates your fit score vs the active resume. **Apply** (adds to tracker) or **Tailor my resume** (placeholder). |
| **Tracker** | Drag cards between stages. **Auto-Track with Gmail** toggle (top-left, placeholder). Each card has **Prep with AI Coach** → pick HR / Hiring Manager / Team Fit → questions drafted from the JD. |
| **AI Coach** | Chat with a Gemini-backed coach that knows your resume + pipeline. Mock interviews, resume review, fit advice. |

## Architecture

```
backend/app/
  main.py            FastAPI app + router wiring
  config.py          env flags (keys → feature toggles)
  models.py          Pydantic shapes (Resume, Job, Score, Coach…)
  store.py           JSON persistence + migration from old shape
  catalog.py         hardcoded job catalog
  services/
    parser.py        ResumeParser: Mock | LlamaParse (PDF→md→Gemini→JSON)
    llm.py           LLMService: Heuristic | Gemini (score, questions, coach)
  routers/
    resume.py        upload / list / activate / delete resumes
    profile.py       edit the ACTIVE resume (mind map CRUD)
    jobs.py          catalog, AI evaluate, tracker, prep-by-round
    dashboard.py     fast stats, moves, top matches
    coach.py         chat + "what I know about you"
frontend/src/
  App.jsx            tab shell + shared state
  api.js             one API client
  components/        Dashboard, ResumesTab, MindMapEditable, JobsTab,
                     TrackerTab, CoachTab, Modal
```

Design choices (per "best architecture, no bloat"):
- **Pluggable providers.** `get_parser()` / `get_llm()` pick the real or offline
  implementation from env vars; nothing else branches on it.
- **Active-resume = profile.** The mind map reads and writes whichever resume is
  active, so multi-resume came free.
- **Fast vs. accurate split.** Dashboard/top-matches use the instant heuristic;
  the explicit "Evaluate" and "Coach" actions use Gemini.
- **No drag library.** The tracker uses native HTML5 drag-and-drop.

## Run it

You already have it installed. With your keys in `backend/.env`:

```bash
# terminal 1 — backend
cd backend
pip install -r requirements.txt        # adds google-genai + llama-parse
uvicorn app.main:app --reload          # http://localhost:8000/docs

# terminal 2 — frontend
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

## Keys (already scaffolded in `backend/.env`)

```
LLAMA_CLOUD_API_KEY=...   # real resume parsing (LlamaParse)
GEMINI_API_KEY=...        # AI scoring, interview questions, coach (Gemini)
GEMINI_MODEL=gemini-2.0-flash
```

Paste your keys and restart uvicorn. With both set: PDFs are parsed by
LlamaParse and structured by Gemini; fit scores, questions, and coach replies
are all Gemini. Leave either blank to fall back to the offline mock/heuristic for
that feature — the app still runs end-to-end.

## If AI features "aren't working"

1. **Reinstall after pulling new code:** `pip install -r requirements.txt`. The
   old pin (`google-genai==0.3.0`) predates the client API the code uses; the
   requirements now need **`google-genai>=1.0.0`**. An out-of-date SDK was the
   original cause — every Gemini call threw and silently fell back to keyword
   scoring (that's why old scores say `"method": "heuristic"`).
2. **Check the live status:** open `http://localhost:8000/api/health`. It now
   does a real Gemini ping and returns `gemini.ok: true` or an `error` string.
3. **Watch the uvicorn console:** provider failures are printed (`[llm] …`,
   `[parser] …`) instead of being hidden.
4. **Key format:** a Google AI Studio key normally looks like `AIza…`. If your
   key is rejected, regenerate one at https://aistudio.google.com/apikey and
   paste it into `backend/.env`, then restart uvicorn.
5. **`429 RESOURCE_EXHAUSTED`** = your key works but you've hit Google's free
   quota for the model. The app keeps running on the offline scorer and
   auto-upgrades to Gemini once quota returns. To get AI back sooner:
   - wait for the quota window to reset (free tier is limited per-minute *and*
     per-day), or
   - set `GEMINI_MODEL=gemini-2.0-flash-lite` in `.env` (lighter, higher free
     throughput), or
   - enable billing on the key's Google Cloud project (Flash is very cheap).
   Catalog evaluations are cached per (job, profile), so re-opening a job or
   applying to one you just scored makes **no** extra API call.

## Still placeholders (by request)

- **Tailor my resume** button (Jobs dialog) — non-functional.
- **Auto-Track with Gmail** toggle (Tracker) — stores state only; no inbox is
  read. Real watch-and-advance logic goes in `routers/jobs.py` (`PATCH /jobs`).

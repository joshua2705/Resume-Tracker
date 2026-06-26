# Setting up the agentic layer — what YOU need to do

Three things to configure: (1) install deps, (2) LangSmith, (3) Gmail MCP.
Everything is optional — skip any part and that feature falls back gracefully.

---

## 0. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```
This adds `langgraph`, `langchain-google-genai`, `langchain-mcp-adapters`,
`langsmith`. You already have the Gemini key the agents use as their LLM.

In `backend/.env` (copy from `.env.example`):
```env
AGENTS_ENABLED=true
GEMINI_API_KEY=<your existing key>     # the agents' LLM
```
Check it worked: `GET http://localhost:8000/api/health` → `agents.langgraph_installed: true`,
or `GET /api/agents/status`.

---

## 1. LangSmith (logging & tracing) — ~2 minutes
1. Sign in at **https://smith.langchain.com**.
2. **Settings → API Keys → Create API Key**. Copy it.
3. In `backend/.env`:
   ```env
   LANGSMITH_API_KEY=lsv2_...
   LANGSMITH_PROJECT=resume-tracker
   ```
4. Restart the backend. Every agent run now appears in LangSmith under the
   `resume-tracker` project (inputs, tool calls, tokens, latency, errors).

Nothing else is needed — tracing is automatic once the key is set.

---

## 2. Gmail MCP (daily inbox → tracker auto-update)

The Gmail agent talks to the **`@gongrzhe/server-gmail-autoauth-mcp`** server
over stdio. You need Node.js (so `npx` works) and a one-time Google OAuth.

### a. Google Cloud OAuth credentials
1. Go to **https://console.cloud.google.com** → create/select a project.
2. **APIs & Services → Library → enable the *Gmail API***.
3. **APIs & Services → OAuth consent screen** → External → add **your own email
   as a Test user** (so you can authorize without app verification).
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   → Application type **Desktop app** → Create → **Download JSON**.
5. Rename the file to **`gcp-oauth.keys.json`**.

### b. Authenticate the MCP server (one time)
```bash
mkdir -p ~/.gmail-mcp
mv /path/to/gcp-oauth.keys.json ~/.gmail-mcp/
npx -y @gongrzhe/server-gmail-autoauth-mcp auth
```
A browser opens → sign in → grant Gmail access. Credentials are saved to
`~/.gmail-mcp/credentials.json`. (Windows: same commands in Git Bash/WSL, or set
`%USERPROFILE%\.gmail-mcp\`.)

### c. Enable it in the app
`backend/.env`:
```env
GMAIL_MCP_ENABLED=true
GMAIL_MCP_COMMAND=npx
GMAIL_MCP_ARGS=-y,@gongrzhe/server-gmail-autoauth-mcp
GMAIL_DAILY_SCAN=true          # run automatically once a day while the backend is up
GMAIL_SCAN_LOOKBACK_DAYS=1
```
> Using a different Gmail MCP? Just change `GMAIL_MCP_COMMAND` / `GMAIL_MCP_ARGS`.

### d. Use it
- In the app, turn on **Auto-Track with Gmail** on the jobs you want scanned
  (or leave all off to scan every tracked job).
- Trigger a scan now: `POST http://localhost:8000/api/agents/gmail/scan`
- See past runs: `GET /api/agents/gmail/log`

**What it does / doesn't do:** read-only (search + read mail only); it never
sends, deletes, labels, or clicks links. It advances a job's status only with
≥0.6 confidence and only forward (or to Rejected), and logs the evidence email.

---

## 3. Guardrails (chat) — optional tuning
Defaults are sane; override in `.env` if needed:
```env
COACH_MAX_INPUT_CHARS=4000
COACH_DAILY_TOKEN_BUDGET=200000     # per user/day, input+output (estimated)
COACH_MAX_REQUESTS_PER_MIN=12
```
Over the limit, `POST /api/coach` returns **HTTP 429** with a `Retry-After`
header. Prompt-injection phrasing isn't blocked but is flagged in the response's
`safety` field and the agent is told to ignore embedded instructions.

---

## Quick verification checklist
- `GET /api/health` → `agents.langgraph_installed: true`, `langsmith: true`, `gmail_mcp: true`.
- `GET /api/agents/status` → `agents_ready: true`.
- Open the **AI Coach**, ask "what should I improve for the Cloudpeak role?" →
  in LangSmith you'll see the coach agent call `get_job_description`.
- `POST /api/agents/gmail/scan` → returns a `GmailScanResult` envelope.

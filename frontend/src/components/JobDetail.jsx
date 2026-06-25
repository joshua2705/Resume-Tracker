import { useState } from "react";
import { api } from "../api";

const STAGES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"];

function scoreClass(n) {
  return n >= 75 ? "good" : n >= 50 ? "ok" : "low";
}

// Detail drawer: candidate score, the "continue applying" flow, interview prep,
// Gmail-agent toggle (placeholder), and the live-interview placeholder.
export default function JobDetail({ job, onUpdate, onClose, onDelete }) {
  const [busy, setBusy] = useState("");
  const s = job.score;

  const patch = async (p) => onUpdate(await api.patchJob(job.id, p));
  const run = async (key, fn) => {
    setBusy(key);
    try { onUpdate(await fn()); } finally { setBusy(""); }
  };

  // "Continue applying" -> mark Applied + generate study questions.
  async function continueApplying() {
    setBusy("apply");
    try {
      await api.patchJob(job.id, { status: "Applied" });
      onUpdate(await api.genQuestions(job.id));
    } finally { setBusy(""); }
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <div>
            <h2>{job.title}</h2>
            <p className="muted">{job.company}</p>
          </div>
          <button className="ghost" onClick={onClose}>Close</button>
        </div>

        {/* Candidate score */}
        <section className="card">
          <div className="score-row">
            <div className={`score-badge ${scoreClass(s?.score ?? 0)}`}>{s?.score ?? "—"}</div>
            <div>
              <h3>Candidate fit score</h3>
              <p className="muted">
                {s?.method === "llm" ? "Semantic match (LLM)" : "Keyword match (offline)"}
              </p>
            </div>
            <button className="ghost" disabled={busy === "rescore"}
              onClick={() => run("rescore", () => api.rescoreJob(job.id))}>
              {busy === "rescore" ? "…" : "Re-score"}
            </button>
          </div>
          {s?.reasoning && <p>{s.reasoning}</p>}
          {s?.matched_skills?.length > 0 && (
            <p><strong>Matched:</strong> {s.matched_skills.join(", ")}</p>
          )}
          {s?.missing_skills?.length > 0 && (
            <p className="muted"><strong>Gaps:</strong> {s.missing_skills.join(", ")}</p>
          )}
        </section>

        {/* Stage + continue-applying */}
        <section className="card">
          <h3>Application stage</h3>
          <div className="row">
            <select value={job.status} onChange={(e) => patch({ status: e.target.value })}>
              {STAGES.map((st) => <option key={st}>{st}</option>)}
            </select>
            <button className="primary" disabled={busy === "apply"} onClick={continueApplying}>
              {busy === "apply" ? "Preparing…" : "Continue applying → prep questions"}
            </button>
          </div>
        </section>

        {/* Interview prep */}
        <section className="card">
          <div className="score-row">
            <h3>Interview prep</h3>
            <button className="ghost" disabled={busy === "q"}
              onClick={() => run("q", () => api.genQuestions(job.id))}>
              {busy === "q" ? "…" : "Generate questions"}
            </button>
          </div>
          {job.interview_questions.length === 0 ? (
            <p className="muted">No questions yet — generate a set to study from.</p>
          ) : (
            <ol className="questions">
              {job.interview_questions.map((q, i) => <li key={i}>{q}</li>)}
            </ol>
          )}
        </section>

        {/* Live AI interview — placeholder */}
        <section className="card placeholder">
          <h3>Live AI interview assistant</h3>
          <p className="muted">Coming soon — real-time help during interviews.</p>
          <button className="ghost" disabled>Start session (placeholder)</button>
        </section>

        {/* Gmail agent toggle — placeholder */}
        <section className="card placeholder">
          <div className="score-row">
            <div>
              <h3>Auto-track via Gmail</h3>
              <p className="muted">Placeholder — toggle saved, no email is read yet.</p>
            </div>
            <label className="switch">
              <input type="checkbox" checked={job.gmail_tracking}
                onChange={(e) => patch({ gmail_tracking: e.target.checked })} />
              <span className="slider" />
            </label>
          </div>
        </section>

        <button className="danger" onClick={() => onDelete(job.id)}>Delete job</button>
      </div>
    </div>
  );
}

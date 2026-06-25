import { useState } from "react";
import { api } from "../api";
import Modal, { scoreClass } from "./Modal";

const STAGES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"];
const ROUNDS = ["HR", "Hiring Manager", "Team Fit"];

// Kanban tracker. Drag a card between stages to update it; dropping on
// "Rejected" deletes the card. Gmail auto-track toggle (placeholder) top-left.
// Per-card "Prep with AI Coach" drafts round-specific questions via the LLM.
export default function TrackerTab({ jobs, onChange }) {
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);
  const [autoTrack, setAutoTrack] = useState(jobs.some((j) => j.gmail_tracking));
  const [prepFor, setPrepFor] = useState(null);

  async function drop(stage) {
    setOverCol(null);
    const id = dragId; setDragId(null);
    if (!id) return;
    const job = jobs.find((j) => j.id === id);
    if (!job) return;
    if (stage === "Rejected") {
      // Reject = remove from the board.
      await api.deleteJob(id);
      onChange();
    } else if (job.status !== stage) {
      await api.patchJob(id, { status: stage });
      onChange();
    }
  }

  async function toggleAuto(on) {
    setAutoTrack(on);
    await Promise.all(jobs.map((j) => api.patchJob(j.id, { gmail_tracking: on })));
    onChange();
  }

  return (
    <div>
      <div className="tracker-head">
        <div>
          <div className="eyebrow">Screen · Tracker</div>
          <h1>Application tracker</h1>
        </div>
        <div className="sk autotrack" title="Placeholder — no email is read yet">
          <span>📧 Auto-Track with Gmail</span>
          <label className="switch">
            <input type="checkbox" checked={autoTrack} onChange={(e) => toggleAuto(e.target.checked)} />
            <span className="slider" />
          </label>
        </div>
      </div>

      <div className="board">
        {STAGES.map((stage) => {
          const col = jobs.filter((j) => j.status === stage);
          const isReject = stage === "Rejected";
          return (
            <div key={stage}
              className={`col ${overCol === stage ? "drag-over" : ""} ${isReject ? "col-reject" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setOverCol(stage); }}
              onDragLeave={() => setOverCol((c) => (c === stage ? null : c))}
              onDrop={() => drop(stage)}>
              <div className="col-title">{isReject ? "Reject ✕" : stage}<span className="muted">{col.length}</span></div>
              {col.map((j) => (
                <div key={j.id} draggable
                  className={`sk tcard ${dragId === j.id ? "dragging" : ""}`}
                  onDragStart={() => setDragId(j.id)} onDragEnd={() => setDragId(null)}>
                  <div className="t-title">{j.title}</div>
                  <div className="muted" style={{ fontSize: 14 }}>{j.company}</div>
                  <div className="t-foot">
                    {j.score && <span className={`pill ${scoreClass(j.score.score)}`}>{j.score.score}%</span>}
                    <button className="btn btn-ghost btn-sm" onClick={() => setPrepFor(j)}>✦ Prep</button>
                  </div>
                  {Object.keys(j.prep || {}).length > 0 && (
                    <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                      prepped: {Object.keys(j.prep).join(", ")}
                    </div>)}
                </div>
              ))}
              {col.length === 0 && <div className="col-empty">{isReject ? "drop to delete" : "drop here"}</div>}
            </div>
          );
        })}
      </div>
      <p className="muted" style={{ marginTop: 10 }}>
        Drag a card between columns to change its stage. Drop on <strong>Reject ✕</strong> to remove it.
      </p>

      {prepFor && <PrepDialog job={prepFor} onClose={() => setPrepFor(null)} onChange={onChange} />}
    </div>
  );
}

function PrepDialog({ job, onClose, onChange }) {
  const [round, setRound] = useState(ROUNDS[0]);
  const [busy, setBusy] = useState(false);
  const [prep, setPrep] = useState(job.prep || {});

  async function generate() {
    setBusy(true);
    try {
      const updated = await api.prep(job.id, round);
      setPrep(updated.prep);
      onChange();
    } finally { setBusy(false); }
  }

  return (
    <Modal onClose={onClose}>
      <div className="eyebrow">{job.company}</div>
      <h2>Prep with AI Coach — {job.title}</h2>
      <p className="muted">Pick the round; the AI drafts likely questions from the job description.</p>
      <div className="row" style={{ margin: "10px 0" }}>
        {ROUNDS.map((r) => (
          <button key={r} className={`btn btn-sm ${round === r ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setRound(r)}>{r}</button>
        ))}
        <button className="btn btn-primary btn-sm" onClick={generate} disabled={busy}>
          {busy ? <><span className="spin" /> Drafting…</> : "Generate questions"}
        </button>
      </div>
      {(prep[round] || []).length > 0 && (
        <div className="sk" style={{ padding: 14 }}>
          <h3>{round} round</h3>
          <ol className="q-list">{prep[round].map((q, i) => <li key={i}>{q}</li>)}</ol>
        </div>
      )}
    </Modal>
  );
}

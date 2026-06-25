import { useEffect, useState } from "react";
import { api } from "../api";
import Modal, { scoreClass } from "./Modal";

// Catalog of roles + an "add job" card for custom postings. Clicking a catalog
// card opens a dialog that computes the match score immediately (no extra click).
export default function JobsTab({ catalog, hasResume, onApplied, onGoto }) {
  const [open, setOpen] = useState(null);   // catalog job
  const [creating, setCreating] = useState(false);

  return (
    <div>
      <div className="eyebrow">Screen · Jobs</div>
      <h1 className="section-title">Open roles</h1>
      <p className="muted" style={{ marginTop: -8 }}>
        Click a role to see your AI fit score instantly, or add your own.
      </p>

      <div className="job-grid" style={{ marginTop: 14 }}>
        {catalog.map((j) => (
          <div className="sk job-card" key={j.id} onClick={() => setOpen(j)}>
            <h3>{j.title}</h3>
            <span>{j.company} · <span className="muted">{j.location}</span></span>
            <div className="tags">{j.tags.map((t) => <span className="tag" key={t}>{t}</span>)}</div>
          </div>
        ))}
        <button className="add-card" onClick={() => setCreating(true)}>
          <div style={{ textAlign: "center" }}>
            <div className="plus">+</div><div>Add a job</div>
          </div>
        </button>
      </div>

      {open && (
        <CatalogDialog job={open} hasResume={hasResume} onClose={() => setOpen(null)}
          onApplied={onApplied} onGoto={onGoto} />
      )}
      {creating && (
        <CreateDialog hasResume={hasResume} onClose={() => setCreating(false)}
          onApplied={onApplied} onGoto={onGoto} />
      )}
    </div>
  );
}

// Shared score panel
function ScorePanel({ score }) {
  if (!score) return null;
  if (score.error) return <p className="muted">Couldn’t evaluate: {score.error}</p>;
  return (
    <div className="sk" style={{ padding: 14, margin: "12px 0" }}>
      <div className="score-hero">
        <div className={`score-orb pill ${scoreClass(score.score)}`}>{score.score}</div>
        <div>
          <h3 style={{ margin: 0 }}>Fit score</h3>
          <span className="muted">{score.method === "llm" ? "AI semantic match (Gemini)" : "Keyword match (offline)"}</span>
        </div>
      </div>
      {score.reasoning && <p>{score.reasoning}</p>}
      {score.matched_skills?.length > 0 && (
        <div><strong>Matched:</strong>
          <div className="chips-static">{score.matched_skills.map((s) => <span className="tag" key={s}>{s}</span>)}</div></div>)}
      {score.missing_skills?.length > 0 && (
        <div style={{ marginTop: 6 }}><strong>Gaps:</strong>
          <div className="chips-static">{score.missing_skills.map((s) => <span className="tag" key={s}>{s}</span>)}</div></div>)}
    </div>
  );
}

// Catalog job: auto-evaluate as soon as the dialog opens.
function CatalogDialog({ job, hasResume, onClose, onApplied, onGoto }) {
  const [score, setScore] = useState(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (!hasResume) return;
    setBusy("eval");
    api.evaluate(job.id)
      .then(setScore).catch((e) => setScore({ error: String(e.message || e) }))
      .finally(() => setBusy(""));
  }, [job.id, hasResume]);

  async function apply() {
    setBusy("apply");
    try {
      await api.apply({ title: job.title, company: job.company, location: job.location,
        description: job.description, catalog_id: job.id, status: "Applied" });
      await onApplied(); onClose(); onGoto("tracker");
    } finally { setBusy(""); }
  }

  return (
    <Modal onClose={onClose}>
      <div className="eyebrow">{job.company} · {job.location}</div>
      <h2>{job.title}</h2>
      {!hasResume && <p className="muted">Upload a resume first to see your match score.</p>}
      {busy === "eval" && <p className="muted"><span className="spin" /> Evaluating your fit…</p>}
      <ScorePanel score={score} />
      <details style={{ margin: "10px 0" }}>
        <summary className="muted">Full job description</summary>
        <p>{job.description}</p>
      </details>
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn btn-primary" onClick={apply} disabled={busy === "apply"}>
          {busy === "apply" ? "Applying…" : "Apply"}
        </button>
        <button className="btn btn-ghost" disabled title="Coming soon">Tailor my resume (soon)</button>
      </div>
    </Modal>
  );
}

// Custom job: fill the form, evaluate, then apply.
function CreateDialog({ hasResume, onClose, onApplied, onGoto }) {
  const [f, setF] = useState({ title: "", company: "", description: "", skills: "" });
  const [score, setScore] = useState(null);
  const [busy, setBusy] = useState("");
  const skillsArr = () => f.skills.split(",").map((s) => s.trim()).filter(Boolean);
  const ready = f.title.trim() && f.description.trim();

  async function evaluate() {
    setBusy("eval");
    try { setScore(await api.score({ title: f.title, description: f.description, skills: skillsArr() })); }
    catch (e) { setScore({ error: String(e.message || e) }); }
    finally { setBusy(""); }
  }
  async function apply() {
    setBusy("apply");
    try {
      await api.apply({ title: f.title, company: f.company, description: f.description,
        skills: skillsArr(), status: "Applied" });
      await onApplied(); onClose(); onGoto("tracker");
    } finally { setBusy(""); }
  }

  return (
    <Modal onClose={onClose}>
      <h2>Add a job</h2>
      <div className="col-form" style={{ marginTop: 10 }}>
        <div className="row">
          <input className="field" placeholder="Job title" value={f.title}
            onChange={(e) => setF({ ...f, title: e.target.value })} />
          <input className="field" placeholder="Company" value={f.company}
            onChange={(e) => setF({ ...f, company: e.target.value })} />
        </div>
        <textarea className="field" rows={4} placeholder="Job description" value={f.description}
          onChange={(e) => setF({ ...f, description: e.target.value })} />
        <input className="field" placeholder="Key skills (comma separated)" value={f.skills}
          onChange={(e) => setF({ ...f, skills: e.target.value })} />
      </div>
      <ScorePanel score={score} />
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" onClick={evaluate} disabled={!ready || !hasResume || busy === "eval"}>
          {busy === "eval" ? <><span className="spin" /> Scoring…</> : "✦ Evaluate match"}
        </button>
        <button className="btn btn-primary" onClick={apply} disabled={!ready || busy === "apply"}>
          {busy === "apply" ? "Applying…" : "Apply"}
        </button>
      </div>
      {!hasResume && <p className="muted">Upload a resume to enable scoring.</p>}
    </Modal>
  );
}

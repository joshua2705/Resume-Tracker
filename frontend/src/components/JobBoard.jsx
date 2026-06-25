import { useState } from "react";
import { api } from "../api";
import JobDetail from "./JobDetail";

const STAGES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"];

function scoreClass(n) {
  return n >= 75 ? "good" : n >= 50 ? "ok" : "low";
}

// Add-job form + kanban tracker. Click a card to open the detail drawer.
export default function JobBoard({ jobs, onChange }) {
  const [form, setForm] = useState({ title: "", company: "", description: "" });
  const [busy, setBusy] = useState(false);
  const [openId, setOpenId] = useState(null);

  async function addJob(e) {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    setBusy(true);
    try {
      const job = await api.createJob(form);
      await onChange();
      setForm({ title: "", company: "", description: "" });
      setOpenId(job.id); // jump straight into the scored job
    } finally {
      setBusy(false);
    }
  }

  const open = jobs.find((j) => j.id === openId);

  return (
    <div className="jobs">
      <section className="card addjob">
        <h3>Add a job</h3>
        <form className="col" onSubmit={addJob}>
          <div className="row">
            <input placeholder="Job title" value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input placeholder="Company" value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })} />
          </div>
          <textarea placeholder="Paste the job description…" rows={4} value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Scoring…" : "Add & score"}
          </button>
        </form>
      </section>

      <div className="board">
        {STAGES.map((stage) => {
          const col = jobs.filter((j) => j.status === stage);
          return (
            <div className="column" key={stage}>
              <div className="col-head">{stage} <span className="count">{col.length}</span></div>
              {col.map((j) => (
                <button className="job-card" key={j.id} onClick={() => setOpenId(j.id)}>
                  <div className="job-card-top">
                    <strong>{j.title}</strong>
                    {j.score && (
                      <span className={`pill ${scoreClass(j.score.score)}`}>{j.score.score}</span>
                    )}
                  </div>
                  <div className="muted">{j.company || "—"}</div>
                  <div className="job-card-tags">
                    {j.gmail_tracking && <span className="tag">📧 auto</span>}
                    {j.interview_questions.length > 0 && <span className="tag">❓ prep</span>}
                  </div>
                </button>
              ))}
              {col.length === 0 && <div className="col-empty">—</div>}
            </div>
          );
        })}
      </div>

      {open && (
        <JobDetail
          job={open}
          onClose={() => setOpenId(null)}
          onUpdate={() => onChange()}
          onDelete={async (id) => { await api.deleteJob(id); setOpenId(null); onChange(); }}
        />
      )}
    </div>
  );
}

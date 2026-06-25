import { useRef, useState } from "react";
import { api } from "../api";

// Resume upload + manual add/remove of skills and experiences.
export default function ProfilePanel({ profile, onChange, parser }) {
  const fileRef = useRef();
  const [busy, setBusy] = useState(false);
  const [skill, setSkill] = useState({ name: "", category: "Technical", level: "" });
  const [exp, setExp] = useState({ role: "", company: "", highlights: "" });

  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      onChange(await api.uploadResume(file));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function addSkill(e) {
    e.preventDefault();
    if (!skill.name.trim()) return;
    const payload = { ...skill, level: skill.level ? Number(skill.level) : null };
    onChange(await api.addSkill(payload));
    setSkill({ name: "", category: skill.category, level: "" });
  }

  async function addExp(e) {
    e.preventDefault();
    if (!exp.role.trim()) return;
    onChange(
      await api.addExperience({
        role: exp.role,
        company: exp.company,
        highlights: exp.highlights
          ? exp.highlights.split("\n").map((s) => s.trim()).filter(Boolean)
          : [],
      })
    );
    setExp({ role: "", company: "", highlights: "" });
  }

  return (
    <div className="panel">
      <section className="card">
        <h3>Resume</h3>
        <p className="muted">
          Parser: <strong>{parser || "…"}</strong>
          {parser === "MockResumeParser" && " (sample data — add LlamaParse key for real parsing)"}
        </p>
        <input ref={fileRef} type="file" accept="application/pdf" onChange={upload} disabled={busy} />
        {busy && <span className="muted"> parsing…</span>}
      </section>

      <section className="card">
        <h3>Add a skill</h3>
        <form className="row" onSubmit={addSkill}>
          <input placeholder="Skill name" value={skill.name}
            onChange={(e) => setSkill({ ...skill, name: e.target.value })} />
          <select value={skill.category}
            onChange={(e) => setSkill({ ...skill, category: e.target.value })}>
            {["Technical", "Business", "Soft", "Languages", "General"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <input type="number" min="1" max="5" placeholder="Lvl" style={{ width: 60 }}
            value={skill.level} onChange={(e) => setSkill({ ...skill, level: e.target.value })} />
          <button type="submit">Add</button>
        </form>
        <div className="chips">
          {profile.skills.map((s) => (
            <span key={s.id} className={`chip ${s.source === "manual" ? "chip-manual" : ""}`}>
              {s.name}
              <button className="x" onClick={() => api.deleteSkill(s.id).then(onChange)}>×</button>
            </span>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Add experience</h3>
        <form className="col" onSubmit={addExp}>
          <div className="row">
            <input placeholder="Role" value={exp.role}
              onChange={(e) => setExp({ ...exp, role: e.target.value })} />
            <input placeholder="Company" value={exp.company}
              onChange={(e) => setExp({ ...exp, company: e.target.value })} />
          </div>
          <textarea placeholder="Highlights (one per line)" rows={2} value={exp.highlights}
            onChange={(e) => setExp({ ...exp, highlights: e.target.value })} />
          <button type="submit">Add experience</button>
        </form>
        <ul className="explist">
          {profile.experiences.map((e) => (
            <li key={e.id}>
              <div>
                <strong>{e.role}</strong>{e.company && <span className="muted"> · {e.company}</span>}
              </div>
              <button className="x" onClick={() => api.deleteExperience(e.id).then(onChange)}>×</button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

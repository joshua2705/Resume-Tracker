import { useRef, useState } from "react";
import { api } from "../api";
import MindMapEditable from "./MindMapEditable";

// Resume library — every upload contributes its skills/experiences to ONE
// aggregate mind map (tagged with that resume). Deleting a resume removes
// exactly the items it added; manual items stay.
export default function ResumesTab({ resumes, profile, parser, onResumesChange, onProfileChange }) {
  const fileRef = useRef();
  const [busy, setBusy] = useState(false);

  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await api.uploadResume(file);
      await onProfileChange();   // refreshes profile + resumes + dashboard
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }
  async function remove(id) {
    if (!confirm("Remove this resume? Its skills/experiences will leave the mind map.")) return;
    await api.deleteResume(id);
    await onProfileChange();
  }

  const live = parser === "LlamaParseResumeParser";

  return (
    <div>
      <div className="eyebrow">Screen · Resumes</div>
      <h1 className="section-title">Your resumes</h1>
      <p className="muted" style={{ marginTop: -8 }}>
        Each resume adds its skills & experience to the mind map below. Remove one and
        its items disappear. Parser: <strong>{live ? "LlamaParse (live)" : "Mock (set keys)"}</strong>.
      </p>

      <div className="resume-grid" style={{ marginTop: 14 }}>
        {resumes.map((r) => (
          <div key={r.id} className="sk resume-card">
            <h3>{r.name}</h3>
            <span className="muted">{r.skill_count} skills · {r.experience_count} experiences</span>
            <span className="muted" style={{ fontSize: 13 }}>{r.filename || "—"}</span>
            {r.parser && <span className="tag" style={{ alignSelf: "flex-start" }}>{r.parser}</span>}
            <div className="card-actions">
              <button className="btn btn-ghost btn-sm" onClick={() => remove(r.id)}>Remove</button>
            </div>
          </div>
        ))}
        <button className="add-card" onClick={() => fileRef.current?.click()} disabled={busy}>
          <div style={{ textAlign: "center" }}>
            <div className="plus">{busy ? "…" : "+"}</div>
            <div>{busy ? "Parsing…" : "Add resume"}</div>
          </div>
        </button>
        <input ref={fileRef} type="file" accept="application/pdf" hidden onChange={upload} />
      </div>

      <h2 className="section-title" style={{ marginTop: 26 }}>Skills & experience mind map</h2>
      {profile
        ? <MindMapEditable profile={profile} onChange={onProfileChange} />
        : <div className="sk" style={{ padding: 20 }}><p className="muted">Loading…</p></div>}
    </div>
  );
}

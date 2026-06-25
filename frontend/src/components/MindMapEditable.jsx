import { useMemo, useState } from "react";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import { api } from "../api";
import Modal from "./Modal";

// Radial mind map built from the active resume. Click any node to edit it.
// Experiences show only the role; clicking opens full details.
function buildGraph(profile) {
  const nodes = [{ id: "root", position: { x: 0, y: 0 }, data: { label: "You" }, className: "mm-node mm-root" }];
  const edges = [];
  const groups = {};
  for (const s of profile.skills) (groups[s.category] ||= []).push(s);
  const branches = Object.entries(groups).map(([name, items]) => ({ name, kind: "cat", items }));
  if (profile.experiences.length) branches.push({ name: "Experience", kind: "exp", items: profile.experiences });

  const n = Math.max(branches.length, 1);
  branches.forEach((b, i) => {
    const ang = (i / n) * 2 * Math.PI - Math.PI / 2;
    const cx = Math.cos(ang) * 330, cy = Math.sin(ang) * 330;
    const cid = `cat-${i}`;
    nodes.push({ id: cid, position: { x: cx, y: cy }, data: { label: b.name },
      className: `mm-node mm-cat ${b.kind === "exp" ? "mm-cat-exp" : ""}` });
    edges.push({ id: `e-root-${cid}`, source: "root", target: cid });
    const m = b.items.length;
    b.items.forEach((it, j) => {
      const a = ang + (m === 1 ? 0 : (j / (m - 1) - 0.5) * (Math.PI / 2.2));
      const lid = `${b.kind}-${it.id}`;
      nodes.push({
        id: lid,
        position: { x: cx + Math.cos(a) * 240, y: cy + Math.sin(a) * 240 },
        data: { label: b.kind === "exp" ? it.role : it.name, kind: b.kind, item: it },
        className: `mm-node ${b.kind === "exp" ? "mm-exp" : ""} ${it.source === "manual" ? "mm-leaf-manual" : ""}`,
      });
      edges.push({ id: `e-${cid}-${lid}`, source: cid, target: lid });
    });
  });
  return { nodes, edges };
}

const CATEGORIES = ["Technical", "Business", "Soft", "Languages", "General"];

export default function MindMapEditable({ profile, onChange }) {
  const { nodes, edges } = useMemo(() => buildGraph(profile), [profile]);
  const [editing, setEditing] = useState(null); // {kind, item} or {kind:'new-skill'|'new-exp'}
  const empty = profile.skills.length === 0 && profile.experiences.length === 0;

  function onNodeClick(_e, node) {
    const k = node.data?.kind;
    if (k === "cat" || k === "exp") setEditing({ kind: k === "exp" ? "exp" : "skill", item: node.data.item });
  }

  return (
    <div className="mindmap-wrap">
      <div className="mindmap">
        {empty ? (
          <div className="mm-empty">Upload a resume (or add a skill) to grow your mind map.</div>
        ) : (
          <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable
            onNodeClick={onNodeClick} proOptions={{ hideAttribution: true }}>
            <Background gap={22} color="#d8d4c6" />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
      </div>
      <div className="mm-hint">Click a node to edit ·
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing({ kind: "skill", item: null })}>+ skill</button>
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing({ kind: "exp", item: null })}>+ experience</button>
      </div>

      {editing && (
        <NodeEditor editing={editing} onClose={() => setEditing(null)}
          onSaved={(p) => { onChange(p); setEditing(null); }} categories={CATEGORIES} />
      )}
    </div>
  );
}

function NodeEditor({ editing, onClose, onSaved, categories }) {
  const isSkill = editing.kind === "skill";
  const it = editing.item;
  const [form, setForm] = useState(
    isSkill
      ? { name: it?.name || "", category: it?.category || "Technical", level: it?.level || "" }
      : {
          role: it?.role || "", company: it?.company || "", start: it?.start || "",
          end: it?.end || "", highlights: (it?.highlights || []).join("\n"),
        }
  );
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      let p;
      if (isSkill) {
        const payload = { name: form.name, category: form.category, level: form.level ? Number(form.level) : null };
        p = it ? await api.editSkill(it.id, payload) : await api.addSkill(payload);
      } else {
        const payload = {
          role: form.role, company: form.company, start: form.start, end: form.end,
          highlights: form.highlights.split("\n").map((s) => s.trim()).filter(Boolean),
        };
        p = it ? await api.editExperience(it.id, payload) : await api.addExperience(payload);
      }
      onSaved(p);
    } finally { setBusy(false); }
  }
  async function remove() {
    setBusy(true);
    try { onSaved(isSkill ? await api.deleteSkill(it.id) : await api.deleteExperience(it.id)); }
    finally { setBusy(false); }
  }

  return (
    <Modal onClose={onClose} width={460}>
      <h2>{it ? "Edit" : "Add"} {isSkill ? "skill" : "experience"}</h2>
      {isSkill ? (
        <div className="col-form" style={{ marginTop: 10 }}>
          <input className="field" placeholder="Skill name" value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div className="row">
            <select className="field" style={{ flex: 1 }} value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {categories.map((c) => <option key={c}>{c}</option>)}
            </select>
            <input className="field" style={{ width: 90 }} type="number" min="1" max="5"
              placeholder="Level" value={form.level}
              onChange={(e) => setForm({ ...form, level: e.target.value })} />
          </div>
        </div>
      ) : (
        <div className="col-form" style={{ marginTop: 10 }}>
          <input className="field" placeholder="Role / title" value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })} />
          <input className="field" placeholder="Company" value={form.company}
            onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <div className="row">
            <input className="field" style={{ flex: 1 }} placeholder="Start (YYYY-MM)" value={form.start}
              onChange={(e) => setForm({ ...form, start: e.target.value })} />
            <input className="field" style={{ flex: 1 }} placeholder="End" value={form.end}
              onChange={(e) => setForm({ ...form, end: e.target.value })} />
          </div>
          <textarea className="field" rows={3} placeholder="Highlights (one per line)" value={form.highlights}
            onChange={(e) => setForm({ ...form, highlights: e.target.value })} />
        </div>
      )}
      <div className="row-between" style={{ marginTop: 16 }}>
        {it ? <button className="btn btn-ghost btn-sm" onClick={remove} disabled={busy}>Delete</button> : <span />}
        <button className="btn btn-primary" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</button>
      </div>
    </Modal>
  );
}

import { useMemo } from "react";
import { ReactFlow, Background, Controls } from "@xyflow/react";

// Build a radial mind map from the profile:
//   center "You"  ->  category nodes  ->  individual skill/experience nodes
function buildGraph(profile) {
  const nodes = [];
  const edges = [];

  nodes.push({
    id: "root",
    position: { x: 0, y: 0 },
    data: { label: "You" },
    className: "mm-node mm-root",
    sourcePosition: "right",
    targetPosition: "left",
  });

  // group skills by category, plus a dedicated Experience branch
  const groups = {};
  for (const s of profile.skills) (groups[s.category] ||= []).push(s);
  const branches = [
    ...Object.entries(groups).map(([name, items]) => ({
      name,
      kind: "skill",
      items,
    })),
  ];
  if (profile.experiences.length) {
    branches.push({ name: "Experience", kind: "exp", items: profile.experiences });
  }

  const n = Math.max(branches.length, 1);
  const R1 = 320;
  branches.forEach((b, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const cx = Math.cos(angle) * R1;
    const cy = Math.sin(angle) * R1;
    const cid = `cat-${i}`;
    nodes.push({
      id: cid,
      position: { x: cx, y: cy },
      data: { label: b.name },
      className: `mm-node mm-cat ${b.kind === "exp" ? "mm-cat-exp" : ""}`,
    });
    edges.push({ id: `e-root-${cid}`, source: "root", target: cid, className: "mm-edge" });

    const m = b.items.length;
    b.items.forEach((it, j) => {
      const spread = Math.PI / 2.2;
      const a = angle + (m === 1 ? 0 : (j / (m - 1) - 0.5) * spread);
      const lx = cx + Math.cos(a) * 230;
      const ly = cy + Math.sin(a) * 230;
      const lid = `leaf-${i}-${j}`;
      const label =
        b.kind === "exp" ? `${it.role}${it.company ? " · " + it.company : ""}` : it.name;
      nodes.push({
        id: lid,
        position: { x: lx, y: ly },
        data: { label },
        className: `mm-node mm-leaf ${it.source === "manual" ? "mm-leaf-manual" : ""}`,
      });
      edges.push({ id: `e-${cid}-${lid}`, source: cid, target: lid, className: "mm-edge" });
    });
  });

  return { nodes, edges };
}

export default function MindMap({ profile }) {
  const { nodes, edges } = useMemo(() => buildGraph(profile), [profile]);
  const empty = profile.skills.length === 0 && profile.experiences.length === 0;

  return (
    <div className="mindmap">
      {empty ? (
        <div className="mm-empty">
          Upload a resume or add a skill to grow your mind map.
        </div>
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          nodesDraggable
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={24} color="#e2e8f0" />
          <Controls showInteractive={false} />
        </ReactFlow>
      )}
    </div>
  );
}

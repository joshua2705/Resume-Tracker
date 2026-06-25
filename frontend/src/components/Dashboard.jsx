import { scoreClass } from "./Modal";

// Landing screen: greets the user, summarizes the tabs, and shows the AI-coach
// "moves for today" callout (all data comes from /api/dashboard).
export default function Dashboard({ data, onGoto }) {
  if (!data) return <div className="muted">Loading your dashboard…</div>;
  const stat = (label, value) => (
    <div className="sk stat">
      <span className="eyebrow">{label}</span>
      <span className="big">{value}</span>
    </div>
  );

  return (
    <div>
      <div className="greet">
        <div className="eyebrow">Screen · Dashboard</div>
        <h1>Hi {data.name} — let’s land your next role.</h1>
        <p className="muted">Here’s where things stand today.</p>
      </div>

      <div className="stat-row">
        {stat("Resume", data.resume_parsed ? "Parsed ✓" : "None yet")}
        {stat("Skills mapped", data.skills_count)}
        {stat("Jobs tracked", data.jobs_count)}
        {stat("Avg fit score", `${data.avg_fit}%`)}
      </div>

      <div className="dash-grid">
        <div className="sk coach-card">
          <span className="coach-tag">✦ AI Coach</span>
          <h2>Your {data.moves.length} moves for today</h2>
          <ol className="moves">
            {data.moves.map((m, i) => (
              <li key={i}><span className="n">{i + 1}</span><span>{m}</span></li>
            ))}
          </ol>
          <div className="row">
            <button className="btn btn-primary" onClick={() => onGoto("coach")}>Open Coach →</button>
            <button className="btn btn-ghost" onClick={() => onGoto("jobs")}>Browse jobs</button>
          </div>
        </div>

        <div className="col-form">
          <div className="sk stat" style={{ padding: 16 }}>
            <h3>Top matches</h3>
            {data.top_matches.length === 0 && <p className="muted">Upload a resume to see matches.</p>}
            {data.top_matches.map((m) => (
              <div className="match" key={m.id} onClick={() => onGoto("jobs")}>
                <span>{m.title} · <span className="muted">{m.company}</span></span>
                <span className={`pill ${scoreClass(m.score)}`}>{m.score}%</span>
              </div>
            ))}
          </div>

          <div className="sk stat" style={{ padding: 16 }}>
            <h3>Recent activity</h3>
            {data.recent_activity.map((a, i) => (
              <div className="activity-line" key={i}>{a}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

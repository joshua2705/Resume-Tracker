import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const CHIPS = ["Review my resume", "Improve my fit", "Mock interview"];
const QUICK = [
  { label: "Score me vs a new job", goto: "jobs" },
  { label: "Strengthen my profile", goto: "resumes" },
  { label: "Review my pipeline", goto: "tracker" },
];

// AI Coach chat. Sends the running message history to /api/coach (Gemini-backed
// when keyed). Right rail shows context + quick actions.
export default function CoachTab({ userName, onGoto }) {
  const [ctx, setCtx] = useState(null);
  const [messages, setMessages] = useState([
    { role: "assistant", content: `Hi ${userName}! I can run a mock interview, tighten your resume, or improve your job fit. Where do you want to start?` },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef();

  useEffect(() => { api.coachContext().then(setCtx).catch(() => {}); }, []);
  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [messages, busy]);

  async function send(text) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const { reply } = await api.coach(next);
      setMessages([...next, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages([...next, { role: "assistant", content: "Sorry — I couldn’t reach the coach service." }]);
    } finally { setBusy(false); }
  }

  return (
    <div>
      <div className="eyebrow">Screen · AI Coach ✦</div>
      <h1 className="section-title">Your AI Coach</h1>

      <div className="coach-layout">
        <div className="sk chat">
          <div className="chat-log" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === "assistant" && <div className="avatar">✦</div>}
                <div className="bubble">{m.content}</div>
              </div>
            ))}
            {busy && <div className="msg assistant"><div className="avatar">✦</div>
              <div className="bubble"><span className="spin" /></div></div>}
          </div>

          <div className="chips">
            {CHIPS.map((c) => <button key={c} className="chip" onClick={() => send(c)} disabled={busy}>{c}</button>)}
          </div>
          <div className="composer">
            <input placeholder="Type your answer…" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()} />
            <button className="btn btn-primary" onClick={() => send()} disabled={busy}>Send</button>
          </div>
        </div>

        <div className="col-form">
          <div className="sk know">
            <h3>What I know about you</h3>
            <ul>{(ctx?.facts || ["…"]).map((f, i) => <li key={i}>{f}</li>)}</ul>
            {ctx && <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
              {ctx.live ? "Live AI (Gemini) connected." : "Offline mode — add GEMINI_API_KEY for live coaching."}</p>}
          </div>
          <div className="sk know">
            <h3>Quick actions</h3>
            {QUICK.map((q) => (
              <div className="qa-row" key={q.label} onClick={() => onGoto(q.goto)} style={{ cursor: "pointer" }}>
                <span>{q.label}</span><span>→</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

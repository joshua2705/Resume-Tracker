import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Dashboard from "./components/Dashboard";
import ResumesTab from "./components/ResumesTab";
import JobsTab from "./components/JobsTab";
import TrackerTab from "./components/TrackerTab";
import CoachTab from "./components/CoachTab";

const TABS = [
  ["dashboard", "Dashboard"],
  ["resumes", "Resumes"],
  ["jobs", "Jobs"],
  ["tracker", "Tracker"],
  ["coach", "AI Coach"],
];

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [profile, setProfile] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [parser, setParser] = useState("");

  const loadDash = useCallback(() => api.dashboard().then(setDash).catch(() => {}), []);
  const loadResumes = useCallback(() => api.listResumes().then(setResumes).catch(() => {}), []);
  const loadProfile = useCallback(() => api.getProfile().then(setProfile).catch(() => {}), []);
  const loadJobs = useCallback(() => api.listJobs().then(setJobs).catch(() => {}), []);

  useEffect(() => {
    loadDash(); loadResumes(); loadProfile(); loadJobs();
    api.catalog().then(setCatalog).catch(() => {});
    api.parserStatus().then((s) => setParser(s.parser)).catch(() => {});
  }, [loadDash, loadResumes, loadProfile, loadJobs]);

  const goto = (t) => { setTab(t); if (t === "dashboard") loadDash(); };

  // Resume upload/delete changes the aggregate mind map → refresh both.
  const afterProfileChange = useCallback(async () => {
    await loadProfile(); await loadResumes(); loadDash();
  }, [loadProfile, loadResumes, loadDash]);
  const afterJobsChange = useCallback(async () => {
    await loadJobs(); loadDash();
  }, [loadJobs, loadDash]);

  const hasResume = !!(profile && (profile.skills.length || profile.experiences.length));

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">✦ Resume Tracker</span>
        <nav className="tabs">
          {TABS.map(([key, label]) => (
            <button key={key} className={`tab ${tab === key ? "active" : ""}`} onClick={() => goto(key)}>
              {label}
              {key === "tracker" && jobs.length > 0 && <span className="badge-count">{jobs.length}</span>}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {tab === "dashboard" && <Dashboard data={dash} onGoto={goto} />}
        {tab === "resumes" && (
          <ResumesTab resumes={resumes} profile={profile} parser={parser}
            onResumesChange={loadResumes} onProfileChange={afterProfileChange} />
        )}
        {tab === "jobs" && (
          <JobsTab catalog={catalog} hasResume={hasResume} onApplied={afterJobsChange} onGoto={goto} />
        )}
        {tab === "tracker" && <TrackerTab jobs={jobs} onChange={afterJobsChange} />}
        {tab === "coach" && <CoachTab userName={dash?.name || "there"} onGoto={goto} />}
      </main>
    </div>
  );
}

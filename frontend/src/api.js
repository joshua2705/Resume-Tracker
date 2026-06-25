// Thin API client. Every backend call goes through here.
const J = { "Content-Type": "application/json" };

async function req(path, opts = {}) {
  const res = await fetch(`/api${path}`, opts);
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => req("/health"),
  dashboard: () => req("/dashboard"),

  // Resumes
  listResumes: () => req("/resumes"),
  parserStatus: () => req("/resumes/parser-status"),
  uploadResume: (file, name = "") => {
    const fd = new FormData();
    fd.append("file", file);
    if (name) fd.append("name", name);
    return req("/resumes", { method: "POST", body: fd });
  },
  activateResume: (id) => req(`/resumes/${id}/activate`, { method: "POST" }),
  deleteResume: (id) => req(`/resumes/${id}`, { method: "DELETE" }),

  // Active resume = profile (mind map)
  getProfile: () => req("/profile"),
  addSkill: (s) => req("/profile/skills", { method: "POST", headers: J, body: JSON.stringify(s) }),
  editSkill: (id, s) => req(`/profile/skills/${id}`, { method: "PUT", headers: J, body: JSON.stringify(s) }),
  deleteSkill: (id) => req(`/profile/skills/${id}`, { method: "DELETE" }),
  addExperience: (e) => req("/profile/experiences", { method: "POST", headers: J, body: JSON.stringify(e) }),
  editExperience: (id, e) => req(`/profile/experiences/${id}`, { method: "PUT", headers: J, body: JSON.stringify(e) }),
  deleteExperience: (id) => req(`/profile/experiences/${id}`, { method: "DELETE" }),

  // Jobs
  catalog: () => req("/catalog"),
  evaluate: (catId) => req(`/catalog/${catId}/evaluate`, { method: "POST" }),
  score: (body) => req("/score", { method: "POST", headers: J, body: JSON.stringify(body) }),
  listJobs: () => req("/jobs"),
  apply: (job) => req("/jobs", { method: "POST", headers: J, body: JSON.stringify(job) }),
  patchJob: (id, p) => req(`/jobs/${id}`, { method: "PATCH", headers: J, body: JSON.stringify(p) }),
  prep: (id, round) => req(`/jobs/${id}/prep?round=${encodeURIComponent(round)}`, { method: "POST" }),
  deleteJob: (id) => req(`/jobs/${id}`, { method: "DELETE" }),

  // Coach
  coachContext: () => req("/coach/context"),
  coach: (messages, jobId) =>
    req("/coach", { method: "POST", headers: J, body: JSON.stringify({ messages, job_id: jobId || null }) }),
};

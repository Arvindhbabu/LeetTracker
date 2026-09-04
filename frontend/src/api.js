const configuredUrl = import.meta.env.VITE_API_URL;
const BASE_URL = configuredUrl
  ? `${configuredUrl.replace(/\/$/, "")}/api`
  : "/api";

async function fetchJSON(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function getStudents() {
  return fetchJSON("/students");
}

export async function getStudent(id) {
  return fetchJSON(`/students/${id}`);
}

export async function getOverview() {
  return fetchJSON("/overview");
}

export async function getLeaderboard(sortBy = "total") {
  return fetchJSON(`/leaderboard?sort_by=${encodeURIComponent(sortBy)}`);
}

export async function getDailyProgress(days = 30) {
  return fetchJSON(`/daily-progress?days=${days}`);
}

export async function triggerSync() {
  return fetchJSON("/sync", { method: "POST" });
}

export async function getSyncStatus() {
  return fetchJSON("/sync-status");
}

export async function getHistoryDates() {
  return fetchJSON("/history/dates");
}

export async function getHistoryStats(date) {
  return fetchJSON(`/history/stats?date_str=${encodeURIComponent(date)}`);
}

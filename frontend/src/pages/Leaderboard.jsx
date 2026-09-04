import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  Search,
  Target,

  TrendingUp,
  Trophy,
  UserRoundCheck,
} from "lucide-react";
import { getHistoryDates, getHistoryStats, getLeaderboard } from "../api";

const AVATAR_COLORS = [
  "linear-gradient(135deg, #4f46e5, #7c3aed)",
  "linear-gradient(135deg, #2563eb, #0ea5e9)",
  "linear-gradient(135deg, #7c3aed, #db2777)",
  "linear-gradient(135deg, #059669, #0ea5e9)",
  "linear-gradient(135deg, #d97706, #e11d48)",
];

function getAvatarColor(index) {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function Leaderboard() {
  const [data, setData] = useState([]);
  const [sortBy, setSortBy] = useState("total");
  const [metricView, setMetricView] = useState("overall"); // "overall" | "daily"
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    async function fetchDates() {
      try {
        const dates = await getHistoryDates();
        if (!active) return;

        setAvailableDates(dates);
        setSelectedDate((current) => {
          if (!dates.length) return "";
          if (!current || !dates.includes(current)) return dates[0];
          return current;
        });
      } catch (e) {
        if (active) console.error("Failed to fetch history dates:", e);
      }
    }

    fetchDates();
    const interval = setInterval(fetchDates, 60000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const isLatest =
        !selectedDate ||
        availableDates.length === 0 ||
        selectedDate === availableDates[0];

      if (isLatest) {
        setData(await getLeaderboard(sortBy));
      } else {
        const stats = await getHistoryStats(selectedDate);
        const mapped = stats.map((student) => ({
          ...student,
          daily_growth: student.growth,
          daily_easy: student.daily_easy ?? 0,
          daily_medium: student.daily_medium ?? 0,
          daily_hard: student.daily_hard ?? 0,
          data_available: student.recorded,
          last_updated: student.recorded ? selectedDate : null,
          status: student.status || (student.leetcode_configured ? "configured" : "pending_username"),
        }));

        mapped.sort((a, b) => {
          const aPending = a.status === "pending_username";
          const bPending = b.status === "pending_username";
          const aReady = a.data_available;
          const bReady = b.data_available;

          if (aPending !== bPending) return aPending ? 1 : -1;
          if (aReady !== bReady) return aReady ? -1 : 1;

          const aMetric = sortBy === "hard"
            ? a.hard
            : sortBy === "daily_growth"
              ? a.daily_growth
              : a.total;
          const bMetric = sortBy === "hard"
            ? b.hard
            : sortBy === "daily_growth"
              ? b.daily_growth
              : b.total;

          return bMetric - aMetric || a.name.localeCompare(b.name);
        });

        let rank = 1;
        setData(
          mapped.map((student) => ({
            ...student,
            rank:
              student.data_available && student.status !== "pending_username"
                ? rank++
                : null,
          })),
        );
      }
    } catch (e) {
      console.error("Failed to load leaderboard:", e);
      setError("Unable to load the leaderboard right now.");
    } finally {
      setLoading(false);
    }
  }, [availableDates, selectedDate, sortBy]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSortChange = (newSortBy) => {
    setSortBy(newSortBy);
    if (newSortBy === "daily_growth") {
      setMetricView("daily");
    } else {
      setMetricView("overall");
    }
  };

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return data;

    return data.filter((student) => {
      const name = student.name?.toLowerCase() || "";
      const username = student.leetcode_id?.toLowerCase() || "";
      return name.includes(query) || username.includes(query);
    });
  }, [data, search]);

  const currentIndex = availableDates.indexOf(selectedDate);
  const isLatest = currentIndex === 0 || !selectedDate;
  const isDailyView = sortBy === "daily_growth" || metricView === "daily";

  function handlePrevDate() {
    if (currentIndex < availableDates.length - 1) {
      setSelectedDate(availableDates[currentIndex + 1]);
    }
  }

  function handleNextDate() {
    if (currentIndex > 0) {
      setSelectedDate(availableDates[currentIndex - 1]);
    }
  }

  return (
    <>
      <div className="page-header page-header-with-actions">
        <div className="page-header-content">
          <div className="eyebrow"><Trophy size={14} /> CLASS RANKINGS</div>
          <h2>Leaderboard</h2>
          <p>Compare every student while keeping unconfigured accounts visible.</p>
        </div>
        <div className="live-indicator">
          <span className="live-dot" />
          Auto-refresh enabled
        </div>
      </div>

      <div className="leaderboard-toolbar">
        <div className="sort-tabs">
          {[
            { key: "total", label: "Total Solved", icon: <Target size={14} /> },
            { key: "daily_growth", label: "Daily Growth", icon: <TrendingUp size={14} /> },
            { key: "hard", label: "Hard Solved", icon: <Trophy size={14} /> },
          ].map((tab) => (
            <button
              key={tab.key}
              className={`sort-tab ${sortBy === tab.key ? "active" : ""}`}
              onClick={() => handleSortChange(tab.key)}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <div className="view-mode-toggle">
          <button
            className={`view-mode-btn ${metricView === "overall" ? "active" : ""}`}
            onClick={() => setMetricView("overall")}
            title="View overall solved counts"
          >
            Lifetime Totals
          </button>
          <button
            className={`view-mode-btn ${metricView === "daily" ? "active" : ""}`}
            onClick={() => setMetricView("daily")}
            title="View today's progress breakdown"
          >
            Today's Progress
          </button>
        </div>

        <div className="date-navigator">
          <button onClick={handlePrevDate} disabled={currentIndex < 0 || currentIndex === availableDates.length - 1}>
            <ChevronLeft size={18} />
          </button>
          <div>
            <span className="date-navigator-label">Snapshot</span>
            <strong>{formatDate(selectedDate)}</strong>
          </div>
          <button onClick={handleNextDate} disabled={currentIndex <= 0}>
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div className="search-bar">
        <span className="search-icon"><Search size={18} /></span>
        <input
          type="text"
          placeholder="Search by student name or LeetCode username..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <div className="table-meta-row">
        <div>
          <strong>{filtered.length}</strong> students shown
          {search && <span> · filtered by “{search}”</span>}
          {isDailyView && <span className="daily-view-badge"> · Showing Daily Easy/Med/Hard Progress</span>}
        </div>
        <div className="table-meta-status">
          {isLatest ? <><UserRoundCheck size={15} /> Current snapshot</> : <><Clock3 size={15} /> Historical snapshot</>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading">
          <div className="loading-spinner" />
          Loading class rankings...
        </div>
      ) : (
        <div className="card leaderboard-card">
          <div className="table-scroll">
            <table className="leaderboard-table">
              <thead>
                <tr>
                  <th style={{ width: "72px" }}>Rank</th>
                  <th>Student</th>
                  <th>{isDailyView ? "Daily Easy" : "Easy"}</th>
                  <th>{isDailyView ? "Daily Med" : "Medium"}</th>
                  <th>{isDailyView ? "Daily Hard" : "Hard"}</th>
                  <th>Total</th>
                  <th>Today</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((student, index) => {
                  const pending = student.status === "pending_username";
                  const configuredNoData = !pending && !student.data_available;

                  return (
                    <tr
                      key={student.id}
                      className={pending ? "leaderboard-pending-row" : ""}
                      onClick={() => navigate(`/student/${student.id}`)}
                    >
                      <td>
                        {student.rank ? (
                          <span className={`rank-badge ${student.rank <= 3 ? `rank-${student.rank}` : "rank-default"}`}>
                            {student.rank}
                          </span>
                        ) : (
                          <span className="rank-placeholder">—</span>
                        )}
                      </td>
                      <td>
                        <div className="student-name-cell">
                          <div className="student-avatar" style={{ background: getAvatarColor(index) }}>
                            {student.name?.charAt(0)?.toUpperCase() || "?"}
                          </div>
                          <div className="student-name-text">
                            <span className="student-name">{student.name}</span>
                            <span className="student-username">
                              {student.leetcode_id ? `@${student.leetcode_id}` : "Username not added yet"}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        {isDailyView ? (
                          student.growth_known ? (
                            <span className={`diff-pill diff-easy daily ${student.daily_easy > 0 ? "has-growth" : "zero-growth"}`}>
                              {student.daily_easy > 0 ? `+${student.daily_easy}` : "0"}
                            </span>
                          ) : (
                            <span className="muted-value">—</span>
                          )
                        ) : (
                          <span className="diff-pill diff-easy">{student.easy}</span>
                        )}
                      </td>
                      <td>
                        {isDailyView ? (
                          student.growth_known ? (
                            <span className={`diff-pill diff-medium daily ${student.daily_medium > 0 ? "has-growth" : "zero-growth"}`}>
                              {student.daily_medium > 0 ? `+${student.daily_medium}` : "0"}
                            </span>
                          ) : (
                            <span className="muted-value">—</span>
                          )
                        ) : (
                          <span className="diff-pill diff-medium">{student.medium}</span>
                        )}
                      </td>
                      <td>
                        {isDailyView ? (
                          student.growth_known ? (
                            <span className={`diff-pill diff-hard daily ${student.daily_hard > 0 ? "has-growth" : "zero-growth"}`}>
                              {student.daily_hard > 0 ? `+${student.daily_hard}` : "0"}
                            </span>
                          ) : (
                            <span className="muted-value">—</span>
                          )
                        ) : (
                          <span className="diff-pill diff-hard">{student.hard}</span>
                        )}
                      </td>
                      <td className="total-cell">{student.total}</td>
                      <td>
                        {student.growth_known ? (
                          <span className={`growth-value ${student.daily_growth > 0 ? "positive" : "neutral"}`}>
                            {student.daily_growth > 0 ? `+${student.daily_growth}` : "0"}
                            {student.daily_growth > 0 && <TrendingUp size={13} />}
                          </span>
                        ) : (
                          <span className="muted-value">—</span>
                        )}
                      </td>
                      <td>
                        {pending ? (
                          <span className="status-pill status-pending"><Clock3 size={12} /> Username pending</span>
                        ) : configuredNoData ? (
                          <span className="status-pill status-neutral"><Clock3 size={12} /> Awaiting sync</span>
                        ) : (
                          <span className="status-pill status-ready"><span className="status-check" /> Synced</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filtered.length === 0 && (
            <div className="empty-state">
              <Search size={24} />
              <strong>No students found</strong>
              <span>Try a different name or LeetCode username.</span>
            </div>
          )}
        </div>
      )}
    </>
  );
}
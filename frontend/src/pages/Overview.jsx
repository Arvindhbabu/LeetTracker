import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Activity,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Flame,
  Target,
  Trophy,
  Users,
} from "lucide-react";
import {
  getDailyProgress,
  getHistoryDates,
  getHistoryStats,
  getLeaderboard,
  getOverview,
} from "../api";

const COLORS = {
  easy: "#059669",
  medium: "#d97706",
  hard: "#e11d48",
  primary: "#4f46e5",
};

const AVATAR_COLORS = [
  "linear-gradient(135deg, #4f46e5, #7c3aed)",
  "linear-gradient(135deg, #2563eb, #0ea5e9)",
  "linear-gradient(135deg, #7c3aed, #db2777)",
  "linear-gradient(135deg, #059669, #0ea5e9)",
  "linear-gradient(135deg, #d97706, #e11d48)",
];

function formatDate(value, options = {}) {
  if (!value) return "—";
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...options,
  });
}

function AnimatedNumber({ value = 0, decimals = false }) {
  const numericValue = Number(value) || 0;
  return <span>{decimals ? numericValue.toFixed(1) : numericValue.toLocaleString()}</span>;
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="chart-tooltip">
      <span>{label}</span>
      {payload.map((item) => (
        <strong key={item.dataKey}>
          {item.name || item.dataKey}: {item.value}
        </strong>
      ))}
    </div>
  );
}

function DateNavigator({ dates, selectedDate, onChange }) {
  const index = dates.indexOf(selectedDate);

  return (
    <div className="date-navigator">
      <button
        onClick={() => index < dates.length - 1 && onChange(dates[index + 1])}
        disabled={index < 0 || index === dates.length - 1}
        aria-label="Older snapshot"
      >
        <ChevronLeft size={18} />
      </button>
      <div>
        <span className="date-navigator-label">Snapshot date</span>
        <strong>{formatDate(selectedDate)}</strong>
      </div>
      <button
        onClick={() => index > 0 && onChange(dates[index - 1])}
        disabled={index <= 0}
        aria-label="Newer snapshot"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}

function ProgressSheet() {
  const [data, setData] = useState([]);
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [showDailyBreakdown, setShowDailyBreakdown] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    async function loadDates() {
      try {
        const dates = await getHistoryDates();
        if (!active) return;

        setAvailableDates(dates);
        setSelectedDate((current) => {
          if (!dates.length) return "";
          if (!current || !dates.includes(current)) return dates[0];
          return current;
        });
      } catch (error) {
        console.error("Failed to load history dates:", error);
      }
    }

    loadDates();
    const interval = setInterval(loadDates, 60000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!selectedDate) {
      return undefined;
    }

    let active = true;

    async function loadStats() {
      try {
        const stats = await getHistoryStats(selectedDate);
        if (active) {
          setData([...stats].sort((a, b) => a.name.localeCompare(b.name)));
        }
      } catch (error) {
        console.error("Failed to load daily stats:", error);
      }
    }

    loadStats();
    return () => {
      active = false;
    };
  }, [selectedDate]);

  const configured = data.filter((student) => student.leetcode_configured).length;
  const recorded = data.filter((student) => student.recorded).length;

  return (
    <section className="card progress-sheet-card">
      <div className="card-header progress-sheet-header">
        <div>
          <div className="section-kicker"><CalendarDays size={14} /> DAILY SNAPSHOT</div>
          <span className="card-title">Class progress tracker</span>
          <span className="card-subtitle">
            Historical cumulative totals and daily growth breakdown by difficulty.
          </span>
        </div>
        <div className="progress-sheet-actions">
          <div className="view-mode-toggle mini">
            <button
              className={`view-mode-btn ${!showDailyBreakdown ? "active" : ""}`}
              onClick={() => setShowDailyBreakdown(false)}
            >
              Lifetime
            </button>
            <button
              className={`view-mode-btn ${showDailyBreakdown ? "active" : ""}`}
              onClick={() => setShowDailyBreakdown(true)}
            >
              Daily Growth
            </button>
          </div>
          <DateNavigator
            dates={availableDates}
            selectedDate={selectedDate}
            onChange={setSelectedDate}
          />
        </div>
      </div>

      {availableDates.length === 0 ? (
        <div className="empty-state compact">
          <Clock3 size={22} />
          <strong>No daily snapshots yet</strong>
          <span>The automatic sync will populate this section after its first successful run.</span>
        </div>
      ) : (
        <div className="table-scroll">
          <table className="leaderboard-table progress-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>{showDailyBreakdown ? "Daily Easy" : "Easy"}</th>
                <th>{showDailyBreakdown ? "Daily Med" : "Medium"}</th>
                <th>{showDailyBreakdown ? "Daily Hard" : "Hard"}</th>
                <th>Total</th>
                <th>Daily Growth</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((student, index) => {
                const pending = student.status === "pending_username";
                return (
                  <tr key={student.id} onClick={() => navigate(`/student/${student.id}`)}>
                    <td>
                      <div className="student-name-cell">
                        <div className="student-avatar" style={{ background: AVATAR_COLORS[index % AVATAR_COLORS.length] }}>
                          {student.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="student-name-text">
                          <span className="student-name">{student.name}</span>
                          <span className="student-username">{student.leetcode_id ? `@${student.leetcode_id}` : "Username not added yet"}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      {showDailyBreakdown ? (
                        student.growth_known ? (
                          <span className={`diff-pill diff-easy daily ${student.daily_easy > 0 ? "has-growth" : "zero-growth"}`}>
                            {student.daily_easy > 0 ? `+${student.daily_easy}` : "0"}
                          </span>
                        ) : <span className="muted-value">—</span>
                      ) : (
                        <span className="diff-pill diff-easy">{student.easy}</span>
                      )}
                    </td>
                    <td>
                      {showDailyBreakdown ? (
                        student.growth_known ? (
                          <span className={`diff-pill diff-medium daily ${student.daily_medium > 0 ? "has-growth" : "zero-growth"}`}>
                            {student.daily_medium > 0 ? `+${student.daily_medium}` : "0"}
                          </span>
                        ) : <span className="muted-value">—</span>
                      ) : (
                        <span className="diff-pill diff-medium">{student.medium}</span>
                      )}
                    </td>
                    <td>
                      {showDailyBreakdown ? (
                        student.growth_known ? (
                          <span className={`diff-pill diff-hard daily ${student.daily_hard > 0 ? "has-growth" : "zero-growth"}`}>
                            {student.daily_hard > 0 ? `+${student.daily_hard}` : "0"}
                          </span>
                        ) : <span className="muted-value">—</span>
                      ) : (
                        <span className="diff-pill diff-hard">{student.hard}</span>
                      )}
                    </td>
                    <td className="total-cell">{student.total}</td>
                    <td>
                      {student.growth_known ? (
                        <span className={`growth-value ${student.growth > 0 ? "positive" : "neutral"}`}>
                          {student.growth > 0 ? `+${student.growth}` : "0"}
                        </span>
                      ) : <span className="muted-value">—</span>}
                    </td>
                    <td>
                      {pending ? (
                        <span className="status-pill status-pending"><Clock3 size={12} /> Username pending</span>
                      ) : student.recorded ? (
                        <span className="status-pill status-ready"><span className="status-check" /> Recorded</span>
                      ) : (
                        <span className="status-pill status-neutral"><Clock3 size={12} /> No snapshot</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {availableDates.length > 0 && (
        <div className="sheet-footer">
          <span>{configured} configured</span>
          <span>{recorded} snapshots recorded</span>
          <span>IST calendar date</span>
        </div>
      )}
    </section>
  );
}

export default function Overview() {
  const [overview, setOverview] = useState(null);
  const [dailyProgress, setDailyProgress] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function loadData() {
    try {
      setError("");
      const [ov, dp, lb] = await Promise.all([
        getOverview(),
        getDailyProgress(30),
        getLeaderboard("total"),
      ]);
      setOverview(ov);
      setDailyProgress(dp);
      setLeaderboard(lb);
    } catch (e) {
      console.error("Failed to load overview:", e);
      setError("Unable to refresh the dashboard. Please check the API service.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, []);

  const trendData = useMemo(
    () => dailyProgress.map((item) => ({
      ...item,
      label: formatDate(item.date, { year: undefined }),
    })),
    [dailyProgress],
  );

  const difficultyData = overview
    ? [
        { name: "Easy", value: overview.total_easy, fill: COLORS.easy },
        { name: "Medium", value: overview.total_medium, fill: COLORS.medium },
        { name: "Hard", value: overview.total_hard, fill: COLORS.hard },
      ]
    : [];

  const topStudents = leaderboard.filter((student) => student.rank).slice(0, 5);

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner" />
        Loading class dashboard...
      </div>
    );
  }

  return (
    <>
      <div className="page-header page-header-with-actions">
        <div className="page-header-content">
          <div className="eyebrow"><Activity size={14} /> CLASS ANALYTICS</div>
          <h2>LeetTracker Dashboard</h2>
          <p>Automatic LeetCode progress tracking for your entire class.</p>
        </div>
        <div className="dashboard-date">
          <CalendarDays size={16} />
          {formatDate(overview?.today)}
          <span>IST</span>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {overview?.pending_students > 0 && (
        <div className="roster-alert">
          <div className="roster-alert-icon"><Clock3 size={18} /></div>
          <div>
            <strong>{overview.pending_students} student{overview.pending_students === 1 ? "" : "s"} waiting for a LeetCode username</strong>
            <span>They remain in the class roster and will automatically start syncing as soon as their username is added to <code>manual_data.py</code>.</span>
          </div>
          <button onClick={() => navigate("/leaderboard")}>View roster</button>
        </div>
      )}

      <div className="stats-grid dashboard-stats-grid">
        <div className="stat-card">
          <div className="stat-icon"><Users size={24} color="#4f46e5" /></div>
          <div className="stat-value"><AnimatedNumber value={overview?.student_count} /></div>
          <div className="stat-label">Class Students</div>
          <div className="stat-footnote">{overview?.configured_students} configured · {overview?.pending_students} pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Target size={24} color="#059669" /></div>
          <div className="stat-value"><AnimatedNumber value={overview?.total_solved} /></div>
          <div className="stat-label">Problems Solved</div>
          <div className="stat-footnote">Across configured accounts</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Trophy size={24} color="#d97706" /></div>
          <div className="stat-value"><AnimatedNumber value={overview?.average_solved} decimals /></div>
          <div className="stat-label">Average Per Student</div>
          <div className="stat-footnote">Configured students only</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"><Flame size={24} color="#e11d48" /></div>
          <div className="stat-value">
            {overview?.daily_growth > 0 ? "+" : ""}<AnimatedNumber value={overview?.daily_growth} />
          </div>
          <div className="stat-label">Today's Growth</div>
          <div className="stat-footnote">{overview?.students_with_growth} students improved</div>
        </div>
      </div>

      <div className="dashboard-health-row">
        <div className="health-card">
          <div className="health-card-icon"><CheckCircle2 size={18} /></div>
          <div>
            <span>Tracking coverage</span>
            <strong>{overview?.coverage_percent}%</strong>
          </div>
          <div className="mini-progress"><span style={{ width: `${overview?.coverage_percent || 0}%` }} /></div>
        </div>
        <div className="health-card">
          <div className="health-card-icon"><Users size={18} /></div>
          <div>
            <span>Snapshots today</span>
            <strong>{overview?.active_today}/{overview?.configured_students}</strong>
          </div>
        </div>
        <div className="health-card">
          <div className="health-card-icon"><Clock3 size={18} /></div>
          <div>
            <span>Last automatic sync</span>
            <strong>{overview?.last_sync ? new Date(overview.last_sync).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Waiting"}</strong>
          </div>
        </div>
      </div>

      {overview?.top_performer && (
        <div className="top-performer-card animate-in">
          <div className="top-performer-avatar"><Trophy size={28} color="#ffffff" /></div>
          <div className="top-performer-info">
            <p>Current class leader</p>
            <h3>{overview.top_performer.name}</h3>
            <div className="top-performer-stats">
              <span style={{ color: COLORS.easy }}>Easy {overview.top_performer.easy}</span>
              <span style={{ color: COLORS.medium }}>Medium {overview.top_performer.medium}</span>
              <span style={{ color: COLORS.hard }}>Hard {overview.top_performer.hard}</span>
              <span>Total {overview.top_performer.total}</span>
            </div>
          </div>
          <button className="ghost-action" onClick={() => navigate(`/student/${overview.top_performer.id}`)}>
            View profile →
          </button>
        </div>
      )}

      <div className="charts-grid dashboard-charts-grid">
        <div className="chart-card">
          <div className="card-header">
            <div>
              <span className="card-title">Daily solving trend</span>
              <span className="card-subtitle">Actual deltas from consecutive daily snapshots</span>
            </div>
          </div>
          {trendData.length ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trendData} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="dailyFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.22} />
                    <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="total" name="Solved" stroke={COLORS.primary} strokeWidth={2.5} fill="url(#dailyFill)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">
              <Activity size={24} />
              <strong>Building your trend history</strong>
              <span>Daily growth appears once consecutive daily snapshots are available.</span>
            </div>
          )}
        </div>

        <div className="chart-card">
          <div className="card-header">
            <div>
              <span className="card-title">Class difficulty mix</span>
              <span className="card-subtitle">All configured students combined</span>
            </div>
          </div>
          <div className="difficulty-chart-wrap">
            <ResponsiveContainer width="58%" height={280}>
              <PieChart>
                <Pie data={difficultyData} dataKey="value" nameKey="name" innerRadius={64} outerRadius={96} paddingAngle={3} stroke="none">
                  {difficultyData.map((item) => <Cell key={item.name} fill={item.fill} />)}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="difficulty-legend">
              {difficultyData.map((item) => (
                <div key={item.name}>
                  <span className="legend-dot" style={{ background: item.fill }} />
                  <span>{item.name}</span>
                  <strong>{item.value.toLocaleString()}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <section className="card class-leaders-card">
        <div className="card-header">
          <div>
            <div className="section-kicker"><Trophy size={14} /> LEADERBOARD PREVIEW</div>
            <span className="card-title">Top students</span>
            <span className="card-subtitle">Click a student for detailed history and profile data.</span>
          </div>
          <button className="ghost-action" onClick={() => navigate("/leaderboard")}>Open full leaderboard →</button>
        </div>
        <div className="leader-preview-grid">
          {topStudents.map((student, index) => (
            <button key={student.id} className="leader-preview-item" onClick={() => navigate(`/student/${student.id}`)}>
              <span className={`preview-rank ${index < 3 ? `rank-${index + 1}` : ""}`}>{index + 1}</span>
              <span className="preview-avatar" style={{ background: AVATAR_COLORS[index % AVATAR_COLORS.length] }}>{student.name.charAt(0)}</span>
              <span className="preview-name">{student.name}</span>
              <strong>{student.total}</strong>
            </button>
          ))}
        </div>
      </section>

      <ProgressSheet />
    </>
  );
}
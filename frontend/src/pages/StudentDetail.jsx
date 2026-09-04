import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  Award,
  Calendar,
  Clock3,
  ExternalLink,
  Target,
  TrendingUp,
  UserRound,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getStudent } from "../api";

const EMPTY_HISTORY = [];

const COLORS = {
  easy: "#059669",
  medium: "#d97706",
  hard: "#e11d48",
  primary: "#4f46e5",
};

function formatDate(value) {
  if (!value) return "—";
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
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

export default function StudentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadStudent = useCallback(async (showLoader = false) => {
    try {
      if (showLoader) setLoading(true);
      const data = await getStudent(id);
      setStudent(data);
      setError("");
    } catch (e) {
      console.error("Failed to load student:", e);
      setError("Unable to load this student profile.");
    } finally {
      if (showLoader) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadStudent(true);
    const interval = setInterval(() => loadStudent(false), 60000);
    return () => clearInterval(interval);
  }, [loadStudent]);

  const pending = student
    ? student.status === "pending_username" || !student.leetcode_configured
    : false;
  const history = student?.history || EMPTY_HISTORY;
  const latestStats = history.length
    ? history[history.length - 1]
    : { easy: 0, medium: 0, hard: 0, total: 0 };

  const historyChart = useMemo(() => {
    return history.map((item, index) => {
      const previous = history[index - 1];
      const growth = previous ? Math.max(0, item.total - previous.total) : 0;
      return {
        date: item.date,
        label: new Date(`${item.date}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        total: item.total,
        growth,
      };
    });
  }, [history]);

  const pieData = [
    { name: "Easy", value: latestStats.easy, color: COLORS.easy },
    { name: "Medium", value: latestStats.medium, color: COLORS.medium },
    { name: "Hard", value: latestStats.hard, color: COLORS.hard },
  ];

  const allQuestions = student?.total_questions || [];
  const globalTotal = allQuestions.find((item) => item.difficulty === "All")?.count || 0;
  const overallPercent = globalTotal
    ? Math.min(100, (latestStats.total / globalTotal) * 100)
    : 0;
  const lastUpdated = history.length ? history[history.length - 1].date : null;

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner" />
        Loading student profile...
      </div>
    );
  }

  if (!student || student.error) {
    return (
      <div>
        <button className="back-link-button" onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="empty-state">
          <UserRound size={28} />
          <strong>Student not found</strong>
          <span>The requested student record does not exist.</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <button className="back-link-button" onClick={() => navigate(-1)}>
        <ArrowLeft size={17} /> Back to dashboard
      </button>

      {error && <div className="alert alert-error">{error}</div>}

      <section className={`student-hero animate-in ${pending ? "student-hero-pending" : ""}`}>
        <div className="student-hero-avatar-container">
          {student.avatar_url ? (
            <img
              src={student.avatar_url}
              alt={student.name}
              className="student-hero-img"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <div className="student-hero-avatar">
              {student.name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        <div className="student-hero-info">
          <div className="student-status-line">
            {pending ? (
              <span className="status-pill status-pending"><Clock3 size={12} /> Username pending</span>
            ) : (
              <span className="status-pill status-ready"><span className="status-check" /> Live tracking</span>
            )}
            {lastUpdated && <span className="hero-meta">Last snapshot {formatDate(lastUpdated)}</span>}
          </div>
          <h2>{student.name}</h2>
          <p>{student.leetcode_id ? `@${student.leetcode_id}` : "LeetCode username has not been added yet"}</p>
          {!pending && (
            <a
              href={`https://leetcode.com/u/${encodeURIComponent(student.leetcode_id)}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="hero-link"
            >
              Open LeetCode profile <ExternalLink size={14} />
            </a>
          )}
        </div>
      </section>

      {pending ? (
        <section className="pending-profile-card">
          <div className="pending-profile-icon"><Clock3 size={24} /></div>
          <div>
            <h3>Waiting for LeetCode username</h3>
            <p>
              This student is already part of the class roster. Add their username to
              <code>backend/manual_data.py</code>, then the next automatic sync will begin tracking them.
            </p>
          </div>
          <div className="pending-profile-state">No account linked</div>
        </section>
      ) : (
        <>
          {globalTotal > 0 && (
            <section className="card progress-overview-card">
              <div className="progress-overview-heading">
                <div>
                  <div className="section-kicker"><Target size={14} /> GLOBAL PROGRESS</div>
                  <h3>Overall LeetCode progress</h3>
                  <p>Solved problems compared with the current LeetCode problem pool.</p>
                </div>
                <strong>{latestStats.total.toLocaleString()} <span>/ {globalTotal.toLocaleString()}</span></strong>
              </div>
              <div className="large-progress"><span style={{ width: `${overallPercent}%` }} /></div>
              <div className="difficulty-progress-grid">
                {[
                  ["Easy", "easy", COLORS.easy],
                  ["Medium", "medium", COLORS.medium],
                  ["Hard", "hard", COLORS.hard],
                ].map(([label, key, color]) => {
                  const solved = latestStats[key] || 0;
                  const total = allQuestions.find((item) => item.difficulty === label)?.count || 0;
                  const percent = total ? Math.min(100, (solved / total) * 100) : 0;
                  return (
                    <div key={key}>
                      <div><span>{label}</span><strong style={{ color }}>{solved}/{total}</strong></div>
                      <div className="small-progress"><span style={{ width: `${percent}%`, background: color }} /></div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon"><Target size={24} color={COLORS.primary} /></div>
              <div className="stat-value">{latestStats.total}</div>
              <div className="stat-label">Total Solved</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon"><Award size={24} color={COLORS.easy} /></div>
              <div className="stat-value">{latestStats.easy}</div>
              <div className="stat-label">Easy</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon"><Activity size={24} color={COLORS.medium} /></div>
              <div className="stat-value">{latestStats.medium}</div>
              <div className="stat-label">Medium</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon"><TrendingUp size={24} color={COLORS.hard} /></div>
              <div className="stat-value">{latestStats.hard}</div>
              <div className="stat-label">Hard</div>
            </div>
          </div>

          <div className="charts-grid">
            <div className="chart-card">
              <div className="card-header">
                <div>
                  <span className="card-title">Solved history</span>
                  <span className="card-subtitle">Cumulative snapshots over time</span>
                </div>
              </div>
              {historyChart.length > 1 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={historyChart} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="studentFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.22} />
                        <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Area type="monotone" dataKey="total" name="Solved" stroke={COLORS.primary} strokeWidth={2.5} fill="url(#studentFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="chart-empty">
                  <Activity size={24} />
                  <strong>History is being built</strong>
                  <span>Daily snapshots will appear here automatically.</span>
                </div>
              )}
            </div>

            <div className="chart-card">
              <div className="card-header">
                <div>
                  <span className="card-title">Difficulty breakdown</span>
                  <span className="card-subtitle">Current solved distribution</span>
                </div>
              </div>
              <div className="difficulty-chart-wrap">
                <ResponsiveContainer width="58%" height={280}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={3} stroke="none">
                      {pieData.map((item) => <Cell key={item.name} fill={item.color} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="difficulty-legend">
                  {pieData.map((item) => (
                    <div key={item.name}>
                      <span className="legend-dot" style={{ background: item.color }} />
                      <span>{item.name}</span>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {student.badges?.length > 0 && (
            <section className="card badges-card">
              <div className="card-header">
                <div>
                  <div className="section-kicker"><Award size={14} /> ACHIEVEMENTS</div>
                  <span className="card-title">LeetCode badges</span>
                </div>
                <span className="badge-count">{student.badges.length} badges</span>
              </div>
              <div className="badges-grid">
                {student.badges.map((badge, index) => (
                  <div className="badge-item" key={`${badge.name}-${index}`} title={badge.name}>
                    <img
                      src={badge.icon?.startsWith("http") ? badge.icon : `https://leetcode.com${badge.icon || ""}`}
                      alt={badge.name}
                    />
                    <span>{badge.name}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <section className="card history-card">
        <div className="card-header">
          <div>
            <div className="section-kicker"><Calendar size={14} /> HISTORY</div>
            <span className="card-title">Daily progress history</span>
            <span className="card-subtitle">Cumulative snapshots and verified daily deltas.</span>
          </div>
          {history.length > 0 && <span className="badge-count">{history.length} snapshots</span>}
        </div>

        {history.length ? (
          <div className="table-scroll">
            <table className="leaderboard-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Easy</th>
                  <th>Medium</th>
                  <th>Hard</th>
                  <th>Daily Growth</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().map((item, index, reversed) => {
                  const previous = reversed[index + 1];
                  const growth = previous ? Math.max(0, item.total - previous.total) : 0;
                  const consecutive = previous && item.date === new Date(new Date(`${previous.date}T00:00:00`).getTime() + 86400000).toISOString().slice(0, 10);
                  return (
                    <tr key={item.date}>
                      <td>{formatDate(item.date)}</td>
                      <td><span className="diff-pill diff-easy">{item.easy}</span></td>
                      <td><span className="diff-pill diff-medium">{item.medium}</span></td>
                      <td><span className="diff-pill diff-hard">{item.hard}</span></td>
                      <td>
                        {consecutive ? (
                          <span className={`growth-value ${growth > 0 ? "positive" : "neutral"}`}>
                            {growth > 0 ? `+${growth}` : "0"}
                          </span>
                        ) : <span className="muted-value">—</span>}
                      </td>
                      <td className="total-cell">{item.total}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state compact">
            <Clock3 size={22} />
            <strong>No snapshots recorded yet</strong>
            <span>This profile will populate automatically once its LeetCode username is configured.</span>
          </div>
        )}
      </section>
    </>
  );
}

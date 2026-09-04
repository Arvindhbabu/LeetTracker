import { useEffect, useState } from "react";
import {
  BarChart3,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Trophy,
  Users,
  X,
} from "lucide-react";
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import Overview from "./pages/Overview";
import Leaderboard from "./pages/Leaderboard";
import StudentDetail from "./pages/StudentDetail";
import { getSyncStatus, triggerSync } from "./api";
import "./App.css";

function formatSyncTime(value) {
  if (!value) return "Waiting for first sync";
  return new Date(value).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Sidebar({ isOpen, onClose }) {
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const location = useLocation();

  async function loadSyncStatus() {
    try {
      const status = await getSyncStatus();
      setSyncStatus(status);
      return status;
    } catch (error) {
      console.error("Failed to load sync status:", error);
    }
  }

  useEffect(() => {
    const timer = setTimeout(onClose, 0);
    return () => clearTimeout(timer);
  }, [location.pathname, onClose]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadSyncStatus();
    }, 0);
    const interval = setInterval(loadSyncStatus, 30000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  async function handleSync() {
    try {
      setSyncing(true);
      await triggerSync();
      await loadSyncStatus();

      // The API starts the work in the background. Poll briefly so the UI
      // reflects the actual completion state instead of guessing after 5s.
      const startedAt = Date.now();
      const poll = setInterval(async () => {
        const status = await loadSyncStatus();
        const timedOut = Date.now() - startedAt > 90000;
        const finished = status && status.status !== "running";

        if (timedOut || finished) {
          clearInterval(poll);
          setSyncing(false);
        }
      }, 3000);

      setTimeout(() => {
        clearInterval(poll);
        setSyncing(false);
        loadSyncStatus();
      }, 90000);
    } catch (error) {
      console.error("Sync failed:", error);
      setSyncing(false);
    }
  }

  const syncOk = syncStatus?.status === "success";
  const syncPartial = syncStatus?.status === "partial";

  return (
    <>
      <div className={`sidebar-backdrop ${isOpen ? "visible" : ""}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon"><BarChart3 size={23} color="#ffffff" /></div>
            <div className="sidebar-logo-text">
              <h1>LeetTracker</h1>
              <p>Class Analytics</p>
            </div>
          </div>
        </div>

        <div className="sidebar-roster-summary">
          <div className="sidebar-roster-icon"><Users size={16} /></div>
          <div>
            <strong>{syncStatus?.students ?? "—"} students</strong>
            <span>{syncStatus?.pending ? `${syncStatus.pending} username pending` : "Roster fully configured"}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            <LayoutDashboard size={18} />
            Overview
          </NavLink>
          <NavLink to="/leaderboard" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            <Trophy size={18} />
            Leaderboard
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="sync-status-card">
            <div className="sync-status-heading">
              <span className={`sync-status-dot ${syncOk ? "ok" : syncPartial ? "partial" : ""}`} />
              <strong>{syncOk ? "Automatic tracking healthy" : syncPartial ? "Sync partially complete" : "Sync status"}</strong>
            </div>
            <span>Last snapshot: {formatSyncTime(syncStatus?.last_sync)}</span>
            {syncStatus?.failed > 0 && <span className="sync-warning">{syncStatus.failed} account(s) need attention</span>}
          </div>

          <button className={`sync-btn ${syncing ? "syncing" : ""}`} onClick={handleSync} disabled={syncing}>
            <RefreshCw size={16} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing class..." : "Sync Now"}
          </button>
        </div>
      </aside>
    </>
  );
}

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <button className="mobile-menu-btn" onClick={() => setSidebarOpen((open) => !open)} aria-label="Toggle menu">
        {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/student/:id" element={<StudentDetail />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

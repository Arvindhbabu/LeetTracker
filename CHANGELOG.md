LeetTracker Change Log

2026-08-15 — v3.0 Professional Class Tracking Foundation

Backend

Reconciled the manual roster to all 63 students.

Added safe pending-username handling using unique internal placeholders.

Prevented pending students from being sent to LeetCode.

Added configured/pending/coverage information to overview and sync APIs.

Leaderboard now includes all 63 students; pending accounts appear without a rank.

Average solved is calculated across configured students only.

Added snapshot/activity health information to the overview API.

Made FastAPI startup roster seeding non-destructive and name-aware.

Replaced destructive/obsolete helper scripts with safe compatibility wrappers.

Kept daily history intact.

Frontend

Reworked Overview into a class analytics dashboard.

Added tracking coverage, snapshot health, pending roster alerts, daily solving trend,
difficulty mix, and top-student preview.

Reworked Leaderboard with search, historical date navigation, status pills, and
pending-user visibility.

Reworked Student Detail with pending-account state, progress bars, history chart,
badges, and live-refresh behavior.

Improved sidebar sync monitoring and manual sync UX.

Added responsive professional dashboard styles.

Validation

Python compilation: passed.

FastAPI endpoint smoke tests: passed.

Frontend ESLint: passed with zero errors/warnings.

Live LeetCode network verification: unavailable in the coding environment because
leetcode.com DNS/network access is blocked there.

v3.1 — Automatic Tracking Hardening (15 Aug 2026)

Fixed the Leaderboard React hook ordering bug so the page does not reference loadData before initialization.

Added backend protection against concurrent manual/cron synchronization runs.

Preserved the one-minute external cron architecture and same-day snapshot upsert model.
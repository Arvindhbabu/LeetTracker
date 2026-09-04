LeetTracker Project State

Canonical baseline

Baseline source: the project ZIP uploaded on 15 August 2026.

Canonical project root: Leetcode-Tracker-optimized/Leetcode-Tracker/.

Current tracked version: v3.1 — Automatic Tracking Hardening.

Class roster source: backend/manual_data.py.

Current roster: 63 students.

Current configured LeetCode usernames: 59.

Current pending usernames: 4.

Architecture

LeetCode GraphQL
      |
      | every minute
      v
Render Cron -> backend/sync_job.py
      |
      v
PostgreSQL (production) / SQLite (local)
      ^
      |
FastAPI API
      ^
      |
React/Vite Dashboard

The dashboard is read-only with respect to LeetCode collection. It can request
an on-demand sync, but automatic data collection belongs to the external cron.

Canonical files

Backend

manual_data.py — only class roster source.

models.py — Student, DailyStat, SyncRun schema.

leetcode_service.py — LeetCode GraphQL collection and daily snapshot logic.

sync_job.py — production synchronization entry point.

routes.py — dashboard API.

main.py — FastAPI application and safe roster seeding.

database.py — SQLite/PostgreSQL configuration and IST date handling.

Frontend

src/App.jsx — shell, navigation, sync status.

src/pages/Overview.jsx — class analytics dashboard.

src/pages/Leaderboard.jsx — searchable historical/current rankings.

src/pages/StudentDetail.jsx — individual progress/profile view.

src/api.js — API client.

src/index.css — dashboard design system and responsive UI.

Pending username design

A blank username in manual_data.py is converted to a private database key:

__PENDING__Student_Name

This is not a LeetCode username and is never sent to LeetCode.
The API hides the placeholder and returns leetcode_id: null plus a pending
status to the frontend.

When a real username becomes available, change only manual_data.py:

('Student Name', 'real_leetcode_username'),

The next sync updates the existing student instead of creating a duplicate.

Data integrity rules

Never fabricate a daily submission count.

DailyStat is a cumulative snapshot for one student and IST calendar date.

Daily growth is calculated only from consecutive calendar-day snapshots.

Pending students remain visible in the 63-student roster.

Pending students are not counted as sync failures.

Student history must not be deleted merely to repair roster metadata.

manual_data.py is the source of truth for class membership.

Current known verification limitation

The coding environment used to inspect this project cannot resolve the external
leetcode.com hostname, so a live LeetCode sync cannot be validated here.
The local API, roster synchronization, pending-user handling, Python compilation,
and frontend ESLint checks are validated.

Change tracking rule

Future project changes should be based on this state and then on the latest
working state produced in this conversation. The current working version is v3.1. Do not reintroduce the old
hard-coded student scripts or nullable/duplicate username approach unless the
architecture is intentionally redesigned.
# LeetTracker Production Deployment

LeetTracker uses a strict separation between **data collection** and the **dashboard UI**.

```text
LeetCode GraphQL
      |
      | every minute
      v
Render Cron Job (sync_job.py)
      |
      v
PostgreSQL
      ^
      |
FastAPI Web Service
      ^
      |
React Static Site
```

## Services

1. **`leettracker-frontend`** — React/Vite static site.
2. **`leettracker-api`** — FastAPI web service.
3. **`leettracker-sync`** — Render Cron Job; runs every minute.
4. **`leettracker-db`** — Render PostgreSQL.

The dashboard never performs the data collection itself. Opening the site only reads the database.

## Daily-history rule

`DailyStat` stores the **cumulative LeetCode totals observed on a particular calendar date**.

For example:

```text
Aug 14 snapshot: 100
Aug 15 snapshot: 108

Aug 15 daily growth = 108 - 100 = 8
```

The API only reports a daily delta when consecutive calendar-day snapshots exist. It does not invent activity for missing days.

Running the sync multiple times on the same day updates the existing `(student_id, date)` row, so the one-minute schedule does not create duplicate daily records.

## Automatic synchronization

Render Cron uses:

```text
* * * * *
```

Render evaluates cron schedules in UTC. The application itself uses **IST (UTC+05:30)** when deciding which daily snapshot date to write.

The cron job is independent of the frontend and independent of the FastAPI web process. Therefore nobody needs to open the dashboard for synchronization to happen.

Render guarantees at most one active run of a given cron job. If a run takes longer than the interval, the next scheduled run waits until the current run finishes. Keep the sync comfortably below one minute. See the official Render cron documentation for current behavior and billing: https://render.com/docs/cronjobs

## Production database

Production requires `DATABASE_URL` and uses PostgreSQL. The bundled SQLite database is only for local development/history inspection.

Do **not** use a Render filesystem or persistent disk as the production database for this application. The cron job is ephemeral and cannot access a persistent disk; PostgreSQL is the shared durable store.

## Manual student source

Students are defined in:

```text
backend/manual_data.py
```

The production synchronization does **not** read Excel or Google Sheets.

The startup/cron seed operation only adds missing students and updates names when the manual list changes.

## Sync monitoring

The API exposes:

```text
GET /health
GET /api/sync-status
```

`/health` verifies the database connection, so Render can detect an unhealthy API.

`/api/sync-status` reports the latest sync status, start/completion time, number of successful students, and failures.

## Local development

Backend terminal:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```

If PowerShell rejects the activation command, use:

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Backend checks:

```text
http://localhost:8000/health
http://localhost:8000/api/overview
http://localhost:8000/api/sync-status
```

## Manual sync

The dashboard's **Sync Now** button starts an on-demand synchronization. It is only a convenience feature; production automation remains the Render Cron Job.

The API prevents starting another manual sync while a recent synchronization is already running.

# LeetTracker Optimization Notes

This version is prepared for the next local validation and Render deployment.

## Fixed

- Automatic synchronization is isolated in `backend/sync_job.py`.
- Render cron remains configured for every minute (`* * * * *`).
- SQLAlchemy ORM objects are no longer passed into worker threads; only primitive IDs/usernames are passed.
- Sync concurrency is configurable through `SYNC_WORKERS` and defaults to 8.
- Request timeout/retry settings are configurable through environment variables.
- Every sync creates an operational `SyncRun` record.
- Added `GET /api/sync-status`.
- `/health` now verifies the database connection.
- Same-day syncs upsert the same `(student_id, date)` snapshot; they do not create duplicates.
- Daily growth is calculated only across consecutive calendar-day snapshots.
- Missing historical days are never fabricated as real activity.
- Manual sync is prevented from starting while a recent sync is already running.
- Frontend API requests use `cache: no-store` and a 15-second timeout.
- Dashboard refreshes display data every minute without triggering collection.
- Daily history date lists refresh automatically every minute, so a new calendar day appears without reopening the page.
- Production student source remains `backend/manual_data.py`; Excel is not read by the application.
- Render remains split into static frontend, always-on API, independent cron, and PostgreSQL.

## Validation

Backend Python files compile successfully.

The synchronization algorithm was tested with a simulated two-day dataset:

- Day 1 snapshot created for all students.
- Day 2 snapshot updated for all students.
- Daily growth matched Day 2 minus Day 1.
- Repeated same-day synchronization updated the existing snapshot instead of duplicating it.

The frontend changed files were parsed successfully with Babel. A full Vite build was not run in this Linux validation container because the uploaded `node_modules` was Windows-specific; Render and the local Windows machine will install dependencies from `package-lock.json` with `npm ci`.

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import requests
from sqlalchemy.orm import Session

from database import get_now, get_today
from models import DailyBaseline, DailyStat, Student, SyncRun

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
SYNC_WORKERS = max(1, int(os.getenv("SYNC_WORKERS", "8")))
REQUEST_TIMEOUT = max(5, int(os.getenv("REQUEST_TIMEOUT", "12")))
MAX_RETRIES = max(1, int(os.getenv("MAX_RETRIES", "3")))
PENDING_PREFIX = "__PENDING__"

QUERY = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile {
      userAvatar
    }
    badges {
      name
      icon
    }
    submitStats: submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
  }
  allQuestionsCount {
    difficulty
    count
  }
}
"""


def is_pending_username(username: str | None) -> bool:
    return not username or username.startswith(PENDING_PREFIX)


def fetch_user_stats(username: str) -> dict | None:
    """Fetch one user's current solved counts from LeetCode."""
    if is_pending_username(username):
        return None

    payload = {"query": QUERY, "variables": {"username": username}}
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/",
        "User-Agent": "LeetTracker/2.1",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                LEETCODE_GRAPHQL_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < MAX_RETRIES:
                    delay = 2 ** (attempt - 1)
                    logger.warning(
                        "LeetCode returned %s for %s; retrying in %ss",
                        response.status_code,
                        username,
                        delay,
                    )
                    time.sleep(delay)
                    continue

            response.raise_for_status()
            data = response.json()

            if data.get("errors"):
                logger.warning("GraphQL errors for %s: %s", username, data["errors"])

            matched = data.get("data", {}).get("matchedUser")
            if not matched:
                logger.warning("User '%s' not found on LeetCode", username)
                return None

            submissions = matched.get("submitStats", {}).get("acSubmissionNum", [])
            stats = {"easy": 0, "medium": 0, "hard": 0, "total": 0}
            for entry in submissions:
                difficulty = str(entry.get("difficulty", "")).lower()
                count = int(entry.get("count", 0) or 0)
                if difficulty == "all":
                    stats["total"] = count
                elif difficulty in stats:
                    stats[difficulty] = count

            profile = matched.get("profile") or {}
            return {
                "stats": stats,
                "avatar": profile.get("userAvatar"),
                "badges": matched.get("badges") or [],
                "all_questions": data.get("data", {}).get("allQuestionsCount") or [],
            }

        except Exception as exc:
            if attempt < MAX_RETRIES:
                delay = 2 ** (attempt - 1)
                logger.warning(
                    "Fetch failed for %s (attempt %s/%s): %s; retrying in %ss",
                    username,
                    attempt,
                    MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Failed to fetch '%s' after %s attempts: %s",
                    username,
                    MAX_RETRIES,
                    exc,
                )

    return None


def _fetch_student(student_id: int, username: str):
    # Pass only immutable primitives to worker threads. SQLAlchemy ORM objects
    # are session-bound and must never be shared between worker threads.
    return student_id, username, fetch_user_stats(username)


def _upsert_today(
    db: Session,
    student: Student,
    result: dict,
    today: date,
):
    """
    Update today's latest cumulative snapshot and create today's
    baseline exactly once.

    Daily progress:

        current cumulative count - start-of-day cumulative count
    """

    stats = result["stats"]

    # ---------------------------------------------------------
    # Update student profile
    # ---------------------------------------------------------

    student.avatar_url = result.get("avatar")
    student.badges = result.get("badges")
    student.total_questions = result.get("all_questions")

    # ---------------------------------------------------------
    # Get/create today's latest snapshot
    # ---------------------------------------------------------

    stat = (
        db.query(DailyStat)
        .filter(
            DailyStat.student_id == student.id,
            DailyStat.date == today,
        )
        .first()
    )

    if stat is None:
        stat = DailyStat(
            student_id=student.id,
            date=today,
        )
        db.add(stat)

    # DailyStat always represents the latest cumulative value.
    stat.easy = stats["easy"]
    stat.medium = stats["medium"]
    stat.hard = stats["hard"]
    stat.total = stats["total"]

    # ---------------------------------------------------------
    # Get today's baseline
    # ---------------------------------------------------------

    baseline = (
        db.query(DailyBaseline)
        .filter(
            DailyBaseline.student_id == student.id,
            DailyBaseline.date == today,
        )
        .first()
    )

    if baseline is not None:
        return

    # ---------------------------------------------------------
    # Find the latest snapshot BEFORE today
    # ---------------------------------------------------------

    previous_stat = (
        db.query(DailyStat)
        .filter(
            DailyStat.student_id == student.id,
            DailyStat.date < today,
        )
        .order_by(DailyStat.date.desc())
        .first()
    )

    if previous_stat is not None:
        baseline = DailyBaseline(
            student_id=student.id,
            date=today,
            easy=previous_stat.easy,
            medium=previous_stat.medium,
            hard=previous_stat.hard,
            total=previous_stat.total,
        )

        logger.info(
            "Baseline created for %s — previous=%s total=%s",
            student.leetcode_id,
            previous_stat.date,
            previous_stat.total,
        )

    else:
        # No previous history exists.
        #
        # This student's first observed value becomes the baseline.
        baseline = DailyBaseline(
            student_id=student.id,
            date=today,
            easy=stats["easy"],
            medium=stats["medium"],
            hard=stats["hard"],
            total=stats["total"],
        )

        logger.info(
            "Baseline initialized for %s — first observed total=%s",
            student.leetcode_id,
            stats["total"],
        )

    db.add(baseline)

def sync_all_students(db: Session) -> dict:
    """Fetch every manual student and upsert today's cumulative snapshot.

    The operation is idempotent: running it repeatedly on the same day updates
    the same (student, date) row instead of creating duplicate history.
    """
    today = get_today()
    started_at = get_now()

    # Prevent a manual sync from racing an already-running cron sync.
    # Render cron jobs do not overlap with themselves, but the dashboard
    # can request a manual sync at any time.
    running = (
        db.query(SyncRun)
        .filter(SyncRun.status == "running")
        .order_by(SyncRun.id.desc())
        .first()
    )

    if running:
        running_started = running.started_at
        if running_started.tzinfo is None:
            running_started = running_started.replace(tzinfo=started_at.tzinfo)

        age_seconds = (started_at - running_started).total_seconds()

        if 0 <= age_seconds < 600:
            logger.info(
                "SYNC SKIPPED — run %s is already active (%ss old)",
                running.id,
                int(age_seconds),
            )
            return {
                "date": today.isoformat(),
                "students": db.query(Student).count(),
                "configured": db.query(Student)
                    .filter(~Student.leetcode_id.startswith(PENDING_PREFIX))
                    .count(),
                "success": 0,
                "failed": 0,
                "pending": db.query(Student)
                    .filter(Student.leetcode_id.startswith(PENDING_PREFIX))
                    .count(),
                "status": "already_running",
                "run_id": running.id,
            }

    students = db.query(Student).order_by(Student.id).all()
    configured_students = [s for s in students if not is_pending_username(s.leetcode_id)]
    pending_students = [s for s in students if is_pending_username(s.leetcode_id)]

    run = SyncRun(
        started_at=started_at,
        date=today,
        students=len(students),
        status="running",
    )
    db.add(run)
    db.commit()

    if not students:
        run.completed_at = get_now()
        run.status = "success"
        db.commit()
        logger.warning("SYNC SKIPPED — no students in database")
        return {"date": today.isoformat(), "students": 0, "configured": 0, "success": 0, "failed": 0, "pending": 0, "status": "success"}

    if not configured_students:
        run.completed_at = get_now()
        run.status = "success"
        run.success = 0
        run.failed = 0
        db.commit()
        logger.info("SYNC COMPLETE — all %s students are pending LeetCode usernames", len(pending_students))
        return {
            "date": today.isoformat(),
            "students": len(students),
            "configured": 0,
            "success": 0,
            "failed": 0,
            "pending": len(pending_students),
            "status": "success",
        }

    workers = min(SYNC_WORKERS, len(configured_students))
    logger.info(
        "SYNC STARTED — date=%s students=%s workers=%s",
        today,
        len(students),
        workers,
    )

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_fetch_student, student.id, student.leetcode_id)
            for student in configured_students
        ]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                logger.exception("Unexpected worker failure")

    success = 0
    failed = 0

    for student_id, username, result in results:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student is None or result is None:
            failed += 1
            logger.warning("SKIP %s — no fresh data returned", username)
            continue

        try:
            _upsert_today(db, student, result, today)
            success += 1
        except Exception:
            failed += 1
            logger.exception("Failed to update database for %s", username)

    status = "success" if failed == 0 else "partial" if success else "failed"
    completed_at = get_now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        run = db.query(SyncRun).filter(SyncRun.id == run.id).first()
        if run:
            run.status = "failed"
            run.error = "Database commit failed"
            run.success = success
            run.failed = failed
            run.completed_at = completed_at
            db.commit()
        raise

    run = db.query(SyncRun).filter(SyncRun.id == run.id).first()
    run.success = success
    run.failed = failed
    run.status = status
    run.completed_at = completed_at
    if failed:
        run.error = f"{failed} configured student sync(s) failed"
    db.commit()

    result = {
        "date": today.isoformat(),
        "students": len(students),
        "configured": len(configured_students),
        "success": success,
        "failed": failed,
        "pending": len(pending_students),
        "status": status,
    }
    logger.info("SYNC COMPLETE — %s", result)
    return result


def backfill_missing_days(db: Session, target_date: date | None = None) -> int:
    """Legacy utility; never call this during normal synchronization.

    Missing days are intentionally left missing because copying an older
    cumulative snapshot would fabricate daily activity.
    """
    logger.warning(
        "backfill_missing_days is disabled for production accuracy; no rows inserted"
    )
    return 0
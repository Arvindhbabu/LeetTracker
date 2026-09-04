import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import SessionLocal, get_db, get_now, get_today
from leetcode_service import (
    is_pending_username,
    sync_all_students,
)
from models import DailyBaseline, DailyStat, Student, SyncRun

from datetime import date, timedelta

PENDING_PREFIX = "__PENDING__"

router = APIRouter()
logger = logging.getLogger(__name__)


def is_configured(student: Student) -> bool:
    return bool(
        student.leetcode_id
        and student.leetcode_id.strip()
        and not student.leetcode_id.startswith(PENDING_PREFIX)
    )


def pending_count(students: list[Student]) -> int:
    return sum(1 for student in students if not is_configured(student))


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db)):
    """Return the real-time synchronization health state."""

    run = (
        db.query(SyncRun)
        .order_by(desc(SyncRun.id))
        .first()
    )

    students = db.query(Student).all()

    pending_count = sum(
        1
        for student in students
        if is_pending_username(student.leetcode_id)
    )

    configured_count = len(students) - pending_count

    environment = os.getenv(
        "ENVIRONMENT",
        "development",
    ).lower()

    auto_sync_enabled = os.getenv(
        "AUTO_SYNC_ENABLED",
        "true" if environment == "development" else "false",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    try:
        interval_minutes = float(
            os.getenv(
                "SYNC_INTERVAL_MINUTES",
                "15",
            )
        )
    except ValueError:
        interval_minutes = 15

    interval_minutes = max(1, interval_minutes)

    scheduler_mode = (
        "local-fastapi"
        if environment == "development" and auto_sync_enabled
        else "external-cron"
    )

    if not run:
        return {
            "status": "never",
            "tracking_health": "waiting",
            "scheduler_mode": scheduler_mode,
            "sync_interval_minutes": interval_minutes,
            "last_sync": None,
            "next_sync": None,
            "date": get_today().isoformat(),
            "students": len(students),
            "configured": configured_count,
            "success": 0,
            "failed": 0,
            "pending": pending_count,
        }

    last_sync = run.completed_at or run.started_at

    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(
            tzinfo=get_now().tzinfo
        )

    next_sync = None

    if run.status != "running":
        next_sync = (
            last_sync
            + timedelta(minutes=interval_minutes)
        )

    now = get_now()
    age_seconds = (
        now - last_sync
    ).total_seconds()

    # While a sync is actively running.
    if run.status == "running":
        tracking_health = "running"

    # A successful sync is healthy until two scheduled intervals
    # have passed without another successful/partial run.
    elif run.status == "success":
        if age_seconds <= interval_minutes * 60 * 2:
            tracking_health = "healthy"
        else:
            tracking_health = "stale"

    elif run.status == "partial":
        if age_seconds <= interval_minutes * 60 * 2:
            tracking_health = "degraded"
        else:
            tracking_health = "stale"

    else:
        tracking_health = "failed"

    return {
        **run.to_dict(),

        "status": run.status,

        "tracking_health": tracking_health,

        "scheduler_mode": scheduler_mode,

        "sync_interval_minutes": interval_minutes,

        "last_sync": (
            run.completed_at.isoformat()
            if run.completed_at
            else run.started_at.isoformat()
        ),

        "next_sync": (
            next_sync.isoformat()
            if next_sync
            else None
        ),

        "date": get_today().isoformat(),

        "students": len(students),

        "configured": configured_count,

        "pending": pending_count,
    }


@router.get("/students")
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.name).all()
    result = []

    for student in students:
        latest = (
            db.query(DailyStat)
            .filter(DailyStat.student_id == student.id)
            .order_by(desc(DailyStat.date))
            .first()
        )

        entry = student.to_dict()
        entry["latest_stats"] = latest.to_dict() if latest else None
        entry["status"] = (
            "configured" if is_configured(student) else "pending_username"
        )
        result.append(entry)

    return result


@router.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        return {"error": "Student not found"}

    history = (
        db.query(DailyStat)
        .filter(DailyStat.student_id == student.id)
        .order_by(DailyStat.date)
        .all()
    )

    return {
        **student.to_dict(),
        "status": "configured" if is_configured(student) else "pending_username",
        "history": [h.to_dict() for h in history],
    }


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    today = get_today()

    configured_students = [student for student in students if is_configured(student)]
    pending_students = len(students) - len(configured_students)

    total_easy = total_medium = total_hard = total_solved = 0
    daily_growth_total = 0
    active_today = 0
    students_with_growth = 0
    top_performer = None
    top_total = -1

    for student in configured_students:
        latest = (
            db.query(DailyStat)
            .filter(DailyStat.student_id == student.id)
            .order_by(desc(DailyStat.date))
            .first()
        )

        if latest:
            total_easy += latest.easy or 0
            total_medium += latest.medium or 0
            total_hard += latest.hard or 0
            total_solved += latest.total or 0

            if latest.total > top_total:
                top_total = latest.total
                top_performer = {
                    **student.to_dict(),
                    "total": latest.total,
                    "easy": latest.easy,
                    "medium": latest.medium,
                    "hard": latest.hard,
                }

        today_stat = (
            db.query(DailyStat)
            .filter(
                DailyStat.student_id == student.id,
                DailyStat.date == today,
            )
            .first()
        )

        if today_stat:
            active_today += 1

            baseline = (
                db.query(DailyBaseline)
                .filter(
                    DailyBaseline.student_id == student.id,
                    DailyBaseline.date == today,
                )
                .first()
            )

            if baseline:
                growth = max(
                    0,
                    today_stat.total - baseline.total,
                )

                daily_growth_total += growth

                if growth > 0:
                    students_with_growth += 1

    latest_run = db.query(SyncRun).order_by(desc(SyncRun.id)).first()

    return {
        "student_count": len(students),
        "configured_students": len(configured_students),
        "pending_students": pending_students,
        "coverage_percent": (
            round(len(configured_students) / len(students) * 100, 1)
            if students
            else 0
        ),
        "active_today": active_today,
        "students_with_growth": students_with_growth,
        "total_easy": total_easy,
        "total_medium": total_medium,
        "total_hard": total_hard,
        "total_solved": total_solved,
        "daily_growth": daily_growth_total,
        "top_performer": top_performer,
        "average_solved": (
            round(total_solved / len(configured_students), 1)
            if configured_students
            else 0
        ),
        "today": today.isoformat(),
        "last_sync": (
            latest_run.completed_at.isoformat()
            if latest_run and latest_run.completed_at
            else None
        ),
        "sync_status": latest_run.status if latest_run else "never",
        "sync_success": latest_run.success if latest_run else 0,
        "sync_failed": latest_run.failed if latest_run else 0,
        "sync_pending": pending_students,
    }


@router.get("/leaderboard")
def get_leaderboard(sort_by: str = "total", db: Session = Depends(get_db)):
    students = db.query(Student).all()
    today = get_today()
    entries = []

    for student in students:
        configured = is_configured(student)

        latest = (
            db.query(DailyStat)
            .filter(DailyStat.student_id == student.id)
            .order_by(desc(DailyStat.date))
            .first()
        )

        today_stat = (
            db.query(DailyStat)
            .filter(
                DailyStat.student_id == student.id,
                DailyStat.date == today,
            )
            .first()
        )

        easy = latest.easy if latest else 0
        medium = latest.medium if latest else 0
        hard = latest.hard if latest else 0
        total = latest.total if latest else 0

        daily_growth = 0
        daily_easy = 0
        daily_medium = 0
        daily_hard = 0
        growth_known = False

        if today_stat:

            baseline = (
                db.query(DailyBaseline)
                .filter(
                    DailyBaseline.student_id == student.id,
                    DailyBaseline.date == today,
                )
                .first()
            )

            if baseline:
                daily_easy = max(
                    0,
                    today_stat.easy - baseline.easy,
                )
                daily_medium = max(
                    0,
                    today_stat.medium - baseline.medium,
                )
                daily_hard = max(
                    0,
                    today_stat.hard - baseline.hard,
                )
                daily_growth = max(
                    0,
                    today_stat.total - baseline.total,
                )

                growth_known = True

        entries.append({
            **student.to_dict(),
            "easy": easy,
            "medium": medium,
            "hard": hard,
            "total": total,
            "daily_easy": daily_easy,
            "daily_medium": daily_medium,
            "daily_hard": daily_hard,
            "daily_growth": daily_growth,
            "growth_known": growth_known,
            "last_updated": latest.date.isoformat() if latest else None,
            "data_available": latest is not None,
            "status": "configured" if configured else "pending_username",
        })

    def sort_key(entry):
        # Configured students with actual data always appear before students
        # that are waiting for a username or their first sync.
        ready_bucket = 0 if entry["data_available"] else 1
        pending_bucket = 0 if entry["status"] == "configured" else 1

        if sort_by == "hard":
            metric = entry["hard"]
        elif sort_by == "daily_growth":
            metric = entry["daily_growth"]
        else:
            metric = entry["total"]

        return (pending_bucket, ready_bucket, -metric, entry["name"].casefold())

    entries.sort(key=sort_key)

    rank = 1
    for entry in entries:
        if entry["data_available"] and entry["status"] == "configured":
            entry["rank"] = rank
            rank += 1
        else:
            entry["rank"] = None

    return entries


@router.post("/sync")
def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start an on-demand sync unless another sync is already running."""
    latest_run = db.query(SyncRun).order_by(desc(SyncRun.id)).first()

    if latest_run and latest_run.status == "running":
        started_at = latest_run.started_at

        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=get_now().tzinfo)

        age = get_now() - started_at

        if age.total_seconds() < 600:
            return {
                "message": "A synchronization is already running",
                "status": "running",
                "run_id": latest_run.id,
            }

    background_tasks.add_task(run_sync_in_background)

    return {
        "message": "Sync started in background",
        "status": "started",
    }


def run_sync_in_background():
    db = SessionLocal()

    try:
        sync_all_students(db)
    except Exception:
        logger.exception("Manual sync failed")
    finally:
        db.close()


@router.get("/history/dates")
def get_history_dates(db: Session = Depends(get_db)):
    dates = (
        db.query(DailyStat.date)
        .distinct()
        .order_by(desc(DailyStat.date))
        .all()
    )

    return [item[0].isoformat() for item in dates]


@router.get("/history/stats")
def get_history_stats(date_str: str, db: Session = Depends(get_db)):
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    students = db.query(Student).order_by(Student.name).all()
    result = []

    for student in students:
        stat = (
            db.query(DailyStat)
            .filter(
                DailyStat.student_id == student.id,
                DailyStat.date == target_date,
            )
            .first()
        )

        previous = (
            db.query(DailyStat)
            .filter(
                DailyStat.student_id == student.id,
                DailyStat.date < target_date,
            )
            .order_by(desc(DailyStat.date))
            .first()
        )

        easy = stat.easy if stat else 0
        medium = stat.medium if stat else 0
        hard = stat.hard if stat else 0
        total = stat.total if stat else 0

        growth_known = bool(
            stat
            and previous
            and previous.date == target_date - timedelta(days=1)
        )

        growth = max(0, total - previous.total) if growth_known else 0
        daily_easy = max(0, easy - previous.easy) if growth_known else 0
        daily_medium = max(0, medium - previous.medium) if growth_known else 0
        daily_hard = max(0, hard - previous.hard) if growth_known else 0

        result.append({
            **student.to_dict(),
            "easy": easy,
            "medium": medium,
            "hard": hard,
            "total": total,
            "growth": growth,
            "daily_easy": daily_easy,
            "daily_medium": daily_medium,
            "daily_hard": daily_hard,
            "growth_known": growth_known,
            "recorded": bool(stat),
            "date": target_date.isoformat(),
            "status": "configured" if is_configured(student) else "pending_username",
        })

    return result

@router.get("/daily-progress")
def get_daily_progress(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    Return actual daily solved counts.

    For today:
        latest cumulative stats - today's baseline.

    For historical dates:
        current snapshot - previous day's snapshot.

    Missing dates are returned as zero.
    """

    days = max(1, min(days, 365))

    today = get_today()
    cutoff = today - timedelta(days=days - 1)

    # ---------------------------------------------------------
    # Load snapshots from one day before the requested period.
    # The extra day is required to calculate the first day's delta.
    # ---------------------------------------------------------

    rows = (
        db.query(DailyStat)
        .filter(
            DailyStat.date >= cutoff - timedelta(days=1),
            DailyStat.date <= today,
        )
        .order_by(
            DailyStat.student_id,
            DailyStat.date,
        )
        .all()
    )

    # ---------------------------------------------------------
    # Load baselines
    # ---------------------------------------------------------

    baselines = (
        db.query(DailyBaseline)
        .filter(
            DailyBaseline.date >= cutoff,
            DailyBaseline.date <= today,
        )
        .all()
    )

    baseline_map = {
        (b.student_id, b.date): b
        for b in baselines
    }

    # ---------------------------------------------------------
    # Calculate progress
    # ---------------------------------------------------------

    output = {}

    previous_by_student = {}

    for row in rows:

        previous = previous_by_student.get(row.student_id)

        # =====================================================
        # TODAY
        # =====================================================

        if row.date == today:

            baseline = baseline_map.get(
                (row.student_id, today)
            )

            if baseline is not None:

                bucket = output.setdefault(
                    today,
                    {
                        "easy": 0,
                        "medium": 0,
                        "hard": 0,
                        "total": 0,
                    },
                )

                bucket["easy"] += max(
                    0,
                    row.easy - baseline.easy,
                )

                bucket["medium"] += max(
                    0,
                    row.medium - baseline.medium,
                )

                bucket["hard"] += max(
                    0,
                    row.hard - baseline.hard,
                )

                bucket["total"] += max(
                    0,
                    row.total - baseline.total,
                )

        # =====================================================
        # HISTORICAL DATE
        # =====================================================

        elif (
            previous is not None
            and previous.date == row.date - timedelta(days=1)
        ):

            bucket = output.setdefault(
                row.date,
                {
                    "easy": 0,
                    "medium": 0,
                    "hard": 0,
                    "total": 0,
                },
            )

            bucket["easy"] += max(
                0,
                row.easy - previous.easy,
            )

            bucket["medium"] += max(
                0,
                row.medium - previous.medium,
            )

            bucket["hard"] += max(
                0,
                row.hard - previous.hard,
            )

            bucket["total"] += max(
                0,
                row.total - previous.total,
            )

        previous_by_student[row.student_id] = row

    # ---------------------------------------------------------
    # Return every requested date.
    # ---------------------------------------------------------

    result = []

    current_date = cutoff

    while current_date <= today:

        values = output.get(
            current_date,
            {
                "easy": 0,
                "medium": 0,
                "hard": 0,
                "total": 0,
            },
        )

        result.append(
            {
                "date": current_date.isoformat(),
                **values,
            }
        )

        current_date += timedelta(days=1)

    return result
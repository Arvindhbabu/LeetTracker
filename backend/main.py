import asyncio
import logging
import os
from contextlib import asynccontextmanager

from auto_sync import is_auto_sync_enabled, run_scheduler

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import Base, engine, SessionLocal
from models import Student
from routes import router

PENDING_PREFIX = "__PENDING__"


def pending_identifier(name: str) -> str:
    slug = "_".join(name.strip().split())
    return f"{PENDING_PREFIX}{slug}"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def seed_manual_students():
    """Synchronize the class roster from manual_data.py.

    A blank LeetCode username is a valid pending state. Students are matched
    by name so that adding a username later updates the existing student
    instead of creating a duplicate.
    """
    from manual_data import STUDENTS

    db = SessionLocal()

    try:
        existing_by_name = {
            student.name.strip().casefold(): student
            for student in db.query(Student).all()
        }
        existing_by_username = {
            student.leetcode_id: student
            for student in db.query(Student).filter(Student.leetcode_id.isnot(None)).all()
            if student.leetcode_id and student.leetcode_id.strip()
        }

        added = 0
        updated = 0

        for name, leetcode_id in STUDENTS:
            clean_name = name.strip()
            username = (
                leetcode_id.strip()
                if isinstance(leetcode_id, str) and leetcode_id.strip()
                else pending_identifier(clean_name)
            )

            student = existing_by_name.get(clean_name.casefold())
            if student is None and username:
                student = existing_by_username.get(username)

            if student is None:
                student = Student(
                    name=clean_name,
                    leetcode_id=username,
                )
                db.add(student)
                added += 1
            else:
                changed = False

                if student.name != clean_name:
                    student.name = clean_name
                    changed = True

                if student.leetcode_id != username:
                    student.leetcode_id = username
                    changed = True

                if changed:
                    updated += 1

            existing_by_name[clean_name.casefold()] = student
            existing_by_username[username] = student

        if added or updated:
            db.commit()

        pending = sum(
            1
            for _, username in STUDENTS
            if not isinstance(username, str) or not username.strip()
        )

        logger.info(
            "Manual roster synchronized: total=%s added=%s updated=%s pending=%s",
            len(STUDENTS),
            added,
            updated,
            pending,
        )

        return added

    except Exception:
        db.rollback()
        logger.exception("Failed to synchronize manual students")
        raise

    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # KEEP YOUR EXISTING ROSTER SYNCHRONIZATION HERE.
    seed_manual_students()

    stop_event = asyncio.Event()
    scheduler_task = None

    if is_auto_sync_enabled():
        scheduler_task = asyncio.create_task(
            run_scheduler(stop_event)
        )

        logger.info(
            "FastAPI started — local automatic synchronization is enabled"
        )
    else:
        logger.info(
            "FastAPI started — synchronization is handled by external cron"
        )

    try:
        yield

    finally:
        if scheduler_task is not None:
            stop_event.set()
            await scheduler_task

        logger.info("FastAPI shutdown complete")


app = FastAPI(
    title="LeetCode Tracker API",
    description="Automatic class-wide LeetCode progress tracking",
    version="3.0.0",
    lifespan=lifespan,
)


allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] + allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "sync": (
                "local-fastapi"
                if os.getenv("ENVIRONMENT", "development").lower() == "development"
                and os.getenv("AUTO_SYNC_ENABLED", "true").lower()
                in {"1", "true", "yes", "on"}
                else "external-cron"
            ),
            "database": "connected",
        }

    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )

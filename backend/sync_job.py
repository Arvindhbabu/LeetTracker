"""Standalone production synchronization job.

Run by Render Cron every minute. It does not depend on the FastAPI process
being awake and it does not require anyone to open the dashboard.
"""

import logging
import sys

from database import Base, SessionLocal, engine
from leetcode_service import sync_all_students

PENDING_PREFIX = "__PENDING__"


def pending_identifier(name: str) -> str:
    slug = "_".join(name.strip().split())
    return f"{PENDING_PREFIX}{slug}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("leettracker.sync_job")


def seed_manual_students():
    """Synchronize the manual roster without requiring every student to have a username."""
    from manual_data import STUDENTS
    from models import Student

    db = SessionLocal()
    try:
        existing_by_id = {s.leetcode_id: s for s in db.query(Student).filter(Student.leetcode_id.isnot(None)).all()}
        existing_by_name = {s.name.strip().casefold(): s for s in db.query(Student).all()}
        added = 0
        updated = 0

        for name, leetcode_id in STUDENTS:
            name_key = name.strip().casefold()
            username = (
                leetcode_id.strip()
                if isinstance(leetcode_id, str) and leetcode_id.strip()
                else pending_identifier(name)
            )

            # Prefer an existing configured account; otherwise match the student by name.
            student = existing_by_id.get(username) if username else None
            if student is None:
                student = existing_by_name.get(name_key)

            if student is None:
                student = Student(name=name, leetcode_id=username)
                db.add(student)
                added += 1
            else:
                changed = False
                if student.name != name:
                    student.name = name
                    changed = True
                if student.leetcode_id != username:
                    student.leetcode_id = username
                    changed = True
                if changed:
                    updated += 1

            existing_by_name[name_key] = student
            existing_by_id[username] = student

        if added or updated:
            db.commit()
        logger.info(
            "Manual students synchronized: added=%s updated=%s total=%s pending=%s",
            added,
            updated,
            len(STUDENTS),
            sum(1 for _, username in STUDENTS if not username or not username.strip()),
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    Base.metadata.create_all(bind=engine)
    seed_manual_students()

    db = SessionLocal()
    try:
        result = sync_all_students(db)
        logger.info("Cron sync result: %s", result)
        if result["success"] == 0 and result.get("configured", 0) > 0:
            raise RuntimeError("All student sync requests failed")
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Cron sync failed")
        sys.exit(1)

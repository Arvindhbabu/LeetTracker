"""Copy the local SQLite database into a PostgreSQL DATABASE_URL.

Usage from backend directory:

PowerShell:
  $env:TARGET_DATABASE_URL = "postgresql://..."
  python migrate_sqlite_to_postgres.py

The script is intentionally separate from application startup so production
never accidentally imports the local SQLite file.
"""

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, LOCAL_DB_PATH
from models import DailyStat, Student


def normalize(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def main():
    target_url = os.getenv("TARGET_DATABASE_URL")
    if not target_url:
        print("ERROR: TARGET_DATABASE_URL is not set.")
        sys.exit(1)

    source_engine = create_engine(f"sqlite:///{LOCAL_DB_PATH}", connect_args={"check_same_thread": False})
    target_engine = create_engine(normalize(target_url), pool_pre_ping=True)

    Base.metadata.create_all(bind=target_engine)

    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    source = SourceSession()
    target = TargetSession()

    try:
        students = source.query(Student).order_by(Student.id).all()
        student_map = {}

        for source_student in students:
            target_student = (
                target.query(Student)
                .filter(Student.leetcode_id == source_student.leetcode_id)
                .first()
            )
            if target_student is None:
                target_student = Student(
                    name=source_student.name,
                    leetcode_id=source_student.leetcode_id,
                    avatar_url=source_student.avatar_url,
                    badges=source_student.badges,
                    total_questions=source_student.total_questions,
                )
                target.add(target_student)
                target.flush()
            else:
                target_student.name = source_student.name
                target_student.avatar_url = source_student.avatar_url
                target_student.badges = source_student.badges
                target_student.total_questions = source_student.total_questions

            student_map[source_student.id] = target_student.id

        target.commit()

        stats = source.query(DailyStat).order_by(DailyStat.date, DailyStat.student_id).all()
        copied = 0

        for source_stat in stats:
            target_student_id = student_map.get(source_stat.student_id)
            if target_student_id is None:
                continue

            target_stat = (
                target.query(DailyStat)
                .filter(
                    DailyStat.student_id == target_student_id,
                    DailyStat.date == source_stat.date,
                )
                .first()
            )
            if target_stat is None:
                target_stat = DailyStat(
                    student_id=target_student_id,
                    date=source_stat.date,
                )
                target.add(target_stat)

            target_stat.easy = source_stat.easy
            target_stat.medium = source_stat.medium
            target_stat.hard = source_stat.hard
            target_stat.total = source_stat.total
            copied += 1

            if copied % 500 == 0:
                target.commit()

        target.commit()
        print(f"Migration complete: {len(students)} students, {copied} daily snapshots.")

    finally:
        source.close()
        target.close()
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()

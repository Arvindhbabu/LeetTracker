from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base

PENDING_PREFIX = "__PENDING__"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    leetcode_id = Column(String, unique=True, nullable=False, index=True)
    avatar_url = Column(String, nullable=True)
    badges = Column(JSON, nullable=True)
    total_questions = Column(JSON, nullable=True)

    daily_stats = relationship(
        "DailyStat",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    daily_baselines = relationship(
        "DailyBaseline",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "leetcode_id": (
                None
                if not self.leetcode_id
                or self.leetcode_id.startswith(PENDING_PREFIX)
                else self.leetcode_id
            ),
            "leetcode_configured": bool(
                self.leetcode_id
                and self.leetcode_id.strip()
                and not self.leetcode_id.startswith(PENDING_PREFIX)
            ),
            "avatar_url": self.avatar_url,
            "badges": self.badges,
            "total_questions": self.total_questions,
        }


class DailyStat(Base):
    """
    Latest cumulative LeetCode snapshot for a student on a given day.

    This row is updated repeatedly by the automatic sync.
    """

    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True,
    )

    date = Column(Date, nullable=False, index=True)

    easy = Column(Integer, default=0, nullable=False)
    medium = Column(Integer, default=0, nullable=False)
    hard = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)

    student = relationship(
        "Student",
        back_populates="daily_stats",
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "date",
            name="uq_student_date",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "date": self.date.isoformat(),
            "easy": self.easy,
            "medium": self.medium,
            "hard": self.hard,
            "total": self.total,
        }


class DailyBaseline(Base):
    """
    First known cumulative LeetCode count for a student on a given day.

    Daily progress is calculated as:

        latest DailyStat - DailyBaseline
    """

    __tablename__ = "daily_baselines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        index=True,
    )

    date = Column(Date, nullable=False, index=True)

    easy = Column(Integer, default=0, nullable=False)
    medium = Column(Integer, default=0, nullable=False)
    hard = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)

    student = relationship(
        "Student",
        back_populates="daily_baselines",
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "date",
            name="uq_student_daily_baseline",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "date": self.date.isoformat(),
            "easy": self.easy,
            "medium": self.medium,
            "hard": self.hard,
            "total": self.total,
        }


class SyncRun(Base):
    """Operational record for every automatic or manual synchronization."""

    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    date = Column(
        Date,
        nullable=False,
        index=True,
    )

    students = Column(
        Integer,
        nullable=False,
        default=0,
    )

    success = Column(
        Integer,
        nullable=False,
        default=0,
    )

    failed = Column(
        Integer,
        nullable=False,
        default=0,
    )

    status = Column(
        String,
        nullable=False,
        default="running",
    )

    error = Column(
        String,
        nullable=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at
                else None
            ),
            "date": self.date.isoformat(),
            "students": self.students,
            "success": self.success,
            "failed": self.failed,
            "status": self.status,
            "error": self.error,
        }
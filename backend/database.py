import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# All dashboard dates are based on Indian Standard Time.
IST = timezone(timedelta(hours=5, minutes=30))


def get_now():
    return datetime.now(IST)


def get_today():
    return get_now().date()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DB_PATH = os.path.join(BASE_DIR, "leetcode_tracker.db")


def get_database_url():
    """Return the configured database URL.

    Local development uses SQLite. Production must provide DATABASE_URL
    (Render PostgreSQL). We deliberately do not fall back to /tmp in
    production because /tmp is ephemeral and would destroy history on restart.
    """
    env_db = os.getenv("DATABASE_URL")
    if env_db:
        # Some hosted providers still expose the legacy postgres:// scheme.
        if env_db.startswith("postgres://"):
            env_db = env_db.replace("postgres://", "postgresql+psycopg2://", 1)
        elif env_db.startswith("postgresql://"):
            env_db = env_db.replace("postgresql://", "postgresql+psycopg2://", 1)
        return env_db

    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError(
            "DATABASE_URL is required in production. Configure a Render PostgreSQL database."
        )

    return f"sqlite:///{LOCAL_DB_PATH}"


DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

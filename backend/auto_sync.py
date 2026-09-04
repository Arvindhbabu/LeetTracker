import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("leettracker.auto_sync")


def is_auto_sync_enabled() -> bool:
    """Check whether automatic synchronization is enabled."""
    value = os.getenv("AUTO_SYNC_ENABLED", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_sync_interval_seconds() -> int:
    """Get the automatic sync interval in seconds."""

    raw_value = os.getenv("SYNC_INTERVAL_MINUTES", "1").strip()

    try:
        minutes = float(raw_value)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid SYNC_INTERVAL_MINUTES=%r. Using 1 minute.",
            raw_value,
        )
        minutes = 1

    # Minimum interval is 1 minute.
    minutes = max(1, minutes)

    return int(minutes * 60)


def get_backend_directory() -> Path:
    """Return the backend directory."""
    return Path(__file__).resolve().parent


def run_sync_job() -> None:
    """
    Run the existing sync_job.py using the same Python interpreter
    that is running FastAPI.
    """

    backend_dir = get_backend_directory()
    sync_job = backend_dir / "sync_job.py"

    logger.info("Starting synchronization job")

    result = subprocess.run(
        [
            sys.executable,
            str(sync_job),
        ],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        for line in result.stdout.splitlines():
            logger.info("sync_job: %s", line)

    if result.stderr:
        for line in result.stderr.splitlines():
            logger.warning("sync_job: %s", line)

    if result.returncode != 0:
        raise RuntimeError(
            f"sync_job.py exited with code {result.returncode}"
        )


async def automatic_sync_loop(stop_event: asyncio.Event) -> None:
    """
    Continuously execute sync_job.py until FastAPI shuts down.
    """

    interval_seconds = get_sync_interval_seconds()

    logger.info(
        "Automatic sync scheduler enabled — interval=%ss initial_delay=5s",
        interval_seconds,
    )

    # Give FastAPI time to finish startup.
    try:
        await asyncio.wait_for(
            stop_event.wait(),
            timeout=5,
        )
        return

    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():

        try:
            logger.info("Automatic sync cycle started")

            # sync_job.py is blocking, so run it outside
            # the FastAPI event loop.
            await asyncio.to_thread(
                run_sync_job
            )

            logger.info("Automatic sync cycle finished")

        except asyncio.CancelledError:
            logger.info(
                "Automatic sync scheduler cancelled"
            )
            raise

        except Exception:
            logger.exception(
                "Automatic sync cycle failed"
            )

        # Wait either for:
        # 1. the next sync interval, or
        # 2. FastAPI shutdown.
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=interval_seconds,
            )

        except asyncio.TimeoutError:
            # Normal timeout.
            # Start the next synchronization cycle.
            continue


def run_scheduler(stop_event: asyncio.Event):
    """
    Return the scheduler coroutine.

    IMPORTANT:
    main.py already calls:

        asyncio.create_task(
            run_scheduler(stop_event)
        )

    Therefore this function MUST NOT call
    asyncio.create_task() itself.
    """

    if not is_auto_sync_enabled():
        logger.info(
            "Automatic sync scheduler disabled"
        )
        return asyncio.sleep(0)

    return automatic_sync_loop(stop_event)
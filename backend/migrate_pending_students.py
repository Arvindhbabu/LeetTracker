"""One-time migration for legacy pending LeetCode usernames.

The current schema keeps ``students.leetcode_id`` non-nullable because every
student needs a unique database key. Students without a real LeetCode account
use a private ``__PENDING__...`` placeholder that the sync service never sends
to LeetCode.

This script is safe to run against an older local SQLite database that may
still contain blank or legacy ``Janarthanjana`` values.
"""

from pathlib import Path
import re
import sqlite3

DB_PATH = Path(__file__).with_name("leetcode_tracker.db")
PENDING_PREFIX = "__PENDING__"


def pending_identifier(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip()).strip("_")
    return f"{PENDING_PREFIX}{slug}"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, name, leetcode_id FROM students ORDER BY id"
        ).fetchall()

        updates = []
        used = {
            row[2]
            for row in rows
            if row[2] and not row[2].startswith(PENDING_PREFIX)
        }

        for student_id, name, username in rows:
            if username and username.startswith(PENDING_PREFIX):
                continue

            if username and username.strip():
                continue

            candidate = pending_identifier(name)
            counter = 2
            while candidate in used:
                candidate = f"{pending_identifier(name)}_{counter}"
                counter += 1

            used.add(candidate)
            updates.append((candidate, student_id))

        conn.executemany(
            "UPDATE students SET leetcode_id = ? WHERE id = ?",
            updates,
        )
        conn.commit()

        print(f"Pending username migration complete: updated={len(updates)}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

"""Deprecated compatibility wrapper.

The old version of this script deleted the complete student/history database.
That behavior is intentionally removed. The class roster is now synchronized
non-destructively by sync_job.py.
"""

from sync_job import seed_manual_students


if __name__ == "__main__":
    seed_manual_students()
    print("Roster synchronized safely. Historical DailyStat records were preserved.")

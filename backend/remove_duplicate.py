"""Deprecated compatibility script.

Duplicate cleanup is no longer performed by deleting arbitrary students.
The roster is reconciled by name and username in sync_job.py so historical
records remain attached to the correct student.
"""

from sync_job import seed_manual_students


if __name__ == "__main__":
    seed_manual_students()
    print("Roster reconciliation complete. No historical student records were deleted.")

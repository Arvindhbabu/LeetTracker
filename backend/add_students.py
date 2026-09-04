"""Deprecated compatibility wrapper.

Do not maintain a second hard-coded student list here. The canonical class
roster lives in manual_data.py and is synchronized by sync_job.py.
"""

from sync_job import seed_manual_students


if __name__ == "__main__":
    seed_manual_students()
    print("Use backend/manual_data.py for roster changes; the roster was synchronized safely.")

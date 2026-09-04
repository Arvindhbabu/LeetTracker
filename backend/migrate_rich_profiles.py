import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leetcode_tracker.db')

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("avatar_url", "TEXT"),
        ("badges", "JSON"),
        ("total_questions", "JSON")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE students ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding column {col_name}: {e}")
                
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()

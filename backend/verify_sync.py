from leetcode_service import fetch_user_stats
from database import SessionLocal
from models import Student
import json

def test_sync():
    db = SessionLocal()
    student = db.query(Student).filter(Student.leetcode_id == "arvindhbabu23").first()
    if not student:
        print("Student not found")
        return

    print(f"Fetching data for {student.leetcode_id}...")
    result = fetch_user_stats(student.leetcode_id)
    
    if result:
        print("Fetch successful!")
        print(f"Avatar: {result['avatar'][:50]}...")
        print(f"Badges count: {len(result['badges'])}")
        print(f"Total Questions fetched: {result['all_questions'] is not None}")
        
        student.avatar_url = result["avatar"]
        student.badges = result["badges"]
        student.total_questions = result["all_questions"]
        
        db.commit()
        print("Database updated!")
    else:
        print("Fetch failed")
    
    db.close()

if __name__ == "__main__":
    test_sync()

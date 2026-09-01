import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.database import SessionLocal, init_db
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService

def seed():
    init_db()
    db = SessionLocal()
    try:
        print("Seeding sample candidate...")
        cand = ResumeService.create_candidate_from_resume(
            db=db,
            name="Alex Rivera",
            target_role="AI/ML Engineer",
            years_exp=4.0,
            resume_text="Experienced AI Engineer skilled in Python, PyTorch, RAG, FastAPI, Vector Databases, and System Design.",
            email="alex.rivera@example.com"
        )
        print(f"Created candidate ID: {cand.id}")

        print("Seeding sample interview session...")
        session = InterviewService.create_interview(
            db=db,
            candidate_id=cand.id,
            target_role="AI/ML Engineer",
            total_questions=5
        )
        print(f"Created interview session ID: {session.id}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()

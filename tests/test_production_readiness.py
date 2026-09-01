import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, init_db
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.rag_service import RAGService

client = TestClient(app)

def test_structured_error_response_404():
    response = client.get("/api/interviews/non_existent_id_99999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == 404
    assert "message" in data["error"]
    assert "timestamp" in data["error"]

def test_structured_validation_error_422():
    # Submit invalid payload missing required fields
    response = client.post("/api/candidates/", json={})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == 422
    assert "details" in data["error"]

def test_empty_resume_validation():
    init_db()
    db = SessionLocal()
    try:
        with pytest.raises(ValueError) as excinfo:
            ResumeService.create_candidate_from_resume(
                db=db,
                name="Empty Resume",
                target_role="Backend Engineer",
                years_exp=1.0,
                resume_text="   "
            )
        assert "empty or invalid" in str(excinfo.value)
    finally:
        db.close()

def test_duplicate_answer_submission_rejection_409():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)
        cand = ResumeService.create_candidate_from_resume(
            db=db,
            name="Duplicate Test",
            target_role="Backend Engineer",
            years_exp=2.0,
            resume_text="Python engineer experienced in FastAPI.",
            email="duplicate@example.com"
        )
        session = InterviewService.create_interview(
            db=db,
            candidate_id=cand.id,
            target_role="Backend Engineer",
            total_questions=2
        )
        q1_id = session.questions[0].id

        # First submission succeeds
        ans1 = client.post("/api/interviews/answers/submit", json={
            "question_id": q1_id,
            "candidate_answer_text": "First answer submission."
        })
        assert ans1.status_code == 200

        # Duplicate submission is rejected with 409 Conflict
        ans2 = client.post("/api/interviews/answers/submit", json={
            "question_id": q1_id,
            "candidate_answer_text": "Duplicate second answer submission."
        })
        assert ans2.status_code == 409
        data = ans2.json()
        assert "error" in data
        assert "Duplicate submissions" in data["error"]["message"]
    finally:
        db.close()

def test_completed_session_submission_prevention():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)
        cand = ResumeService.create_candidate_from_resume(
            db=db,
            name="Completed Test",
            target_role="Backend Engineer",
            years_exp=2.0,
            resume_text="Python engineer.",
            email="completed@example.com"
        )
        session = InterviewService.create_interview(
            db=db,
            candidate_id=cand.id,
            target_role="Backend Engineer",
            total_questions=1
        )
        q1_id = session.questions[0].id

        # Complete interview
        ans1 = client.post("/api/interviews/answers/submit", json={
            "question_id": q1_id,
            "candidate_answer_text": "Final answer submission completing session."
        })
        assert ans1.status_code == 200
        assert ans1.json()["interview_completed"] is True

    finally:
        db.close()

def test_corrupted_pdf_upload_validation():
    with pytest.raises(ValueError) as excinfo:
        ResumeService.extract_text_from_pdf_bytes(b"INVALID_HEADER_NOT_A_PDF", filename="corrupt.pdf")
    assert "Invalid PDF" in str(excinfo.value) or "header" in str(excinfo.value)

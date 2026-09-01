import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, init_db
from app.services.rag_service import RAGService

client = TestClient(app)

def test_api_endpoints():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)
    finally:
        db.close()

    # Healthcheck
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "online"

    # Create Candidate Endpoint
    cand_payload = {
        "name": "API Test Candidate",
        "target_role": "Backend Engineer",
        "years_of_experience": 4.0,
        "resume_text": "Experienced with FastAPI, PostgreSQL, Redis, System Design."
    }
    cand_res = client.post("/api/candidates/", json=cand_payload)
    assert cand_res.status_code == 200
    cand_data = cand_res.json()
    assert cand_data["id"].startswith("cand_")

    # Create Interview Endpoint
    intv_payload = {
        "candidate_id": cand_data["id"],
        "target_role": "Backend Engineer",
        "total_questions": 2
    }
    intv_res = client.post("/api/interviews/", json=intv_payload)
    assert intv_res.status_code == 200
    intv_data = intv_res.json()
    assert intv_data["status"] == "in_progress"
    assert intv_data["current_question"] is not None

    # Submit Answer Endpoint
    q_id = intv_data["current_question"]["id"]
    ans_payload = {
        "question_id": q_id,
        "candidate_answer_text": "Redis provides high-speed in-memory caching with data persistence options like RDB and AOF."
    }
    ans_res = client.post("/api/interviews/answers/submit", json=ans_payload)
    assert ans_res.status_code == 200
    ans_data = ans_res.json()
    assert "evaluation" in ans_data

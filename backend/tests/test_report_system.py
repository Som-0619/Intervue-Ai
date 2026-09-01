import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, init_db
from app.models.domain import Candidate, InterviewSession, Question
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService
from app.services.rag_service import RAGService

client = TestClient(app)

def test_report_generation_and_mandatory_categories():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)

        # 1. Create Candidate & Session
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name="Taylor Swift",
            target_role="AI/ML Engineer",
            years_exp=4.0,
            resume_text="AI researcher skilled in PyTorch, Transformer models, RAG vector retrieval, and LLM fine-tuning.",
            email="taylor@example.com"
        )

        session = InterviewService.create_interview(
            db=db,
            candidate_id=candidate.id,
            target_role="AI/ML Engineer",
            total_questions=2
        )

        # Submit answer to Q1
        q1 = session.questions[0]
        InterviewService.submit_answer(
            db=db,
            question_id=q1.id,
            answer_text="RAG architecture indexes documents into dense vector embeddings using models like BERT. Prompts are augmented with retrieved context chunks to minimize hallucination.",
            code_snippet=None
        )

        # Fetch report response
        report_dto = ReportService.get_report_response(db=db, interview_id=session.id)

        assert report_dto.interview_id == session.id
        assert report_dto.candidate_name == "Taylor Swift"
        assert report_dto.overall_score > 0.0
        assert report_dto.hiring_recommendation in ["Strong Hire", "Hire", "Weak Hire", "No Hire", "Insufficient Data"]

        # Verify mandatory 4 core categories present
        cat_names = [c.category for c in report_dto.category_scores]
        for mandatory_cat in ["fundamentals", "applied knowledge", "problem solving", "resume/project understanding"]:
            assert mandatory_cat in cat_names

        # Verify Question-by-Question Analysis & Lineage Traceability
        assert len(report_dto.question_by_question_analysis) >= 1
        analysis = report_dto.question_by_question_analysis[0]
        assert analysis.question_id == q1.id
        assert analysis.question == q1.question
        assert analysis.candidate_answer != ""
        assert analysis.score > 0.0
        assert analysis.topic == q1.topic
        assert len(analysis.relevant_knowledge_source_metadata) > 0

    finally:
        db.close()

def test_report_insufficient_data_representation():
    init_db()
    db = SessionLocal()
    try:
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name="Unanswered Candidate",
            target_role="Frontend Engineer",
            years_exp=1.0,
            resume_text="Junior developer experienced with React and HTML.",
            email="unanswered@example.com"
        )

        session = InterviewService.create_interview(
            db=db,
            candidate_id=candidate.id,
            target_role="Frontend Engineer",
            total_questions=2
        )

        # Generate report without submitting answers
        report_dto = ReportService.get_report_response(db=db, interview_id=session.id)
        assert report_dto.overall_score == 0.0
        assert report_dto.hiring_recommendation == "Insufficient Data"
        
        # Verify unanswered status representation
        for analysis in report_dto.question_by_question_analysis:
            assert analysis.candidate_answer == "No answer submitted"
            assert analysis.score == 0.0

    finally:
        db.close()

def test_get_interview_report_api_endpoint():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)
        cand_payload = {
            "name": "API Report Candidate",
            "target_role": "Backend Engineer",
            "years_of_experience": 3.0,
            "resume_text": "Python FastAPI PostgreSQL developer."
        }
        cand_res = client.post("/api/candidates/", json=cand_payload)
        cand_id = cand_res.json()["id"]

        intv_res = client.post("/api/interviews/", json={"candidate_id": cand_id, "target_role": "Backend Engineer", "total_questions": 1})
        intv_id = intv_res.json()["id"]

        q_id = intv_res.json()["current_question"]["id"]
        client.post("/api/interviews/answers/submit", json={"question_id": q_id, "candidate_answer_text": "PostgreSQL uses MVCC concurrency control to manage transactional isolation levels."})

        # Test GET /api/interviews/{id}/report
        res = client.get(f"/api/interviews/{intv_id}/report")
        assert res.status_code == 200
        data = res.json()
        assert data["interview_id"] == intv_id
        assert "category_scores" in data
        assert "question_by_question_analysis" in data
        assert len(data["question_by_question_analysis"]) == 1

        # Test GET 404 for invalid ID
        res_404 = client.get("/api/interviews/invalid_id_123/report")
        assert res_404.status_code == 404
    finally:
        db.close()

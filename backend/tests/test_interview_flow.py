import pytest
from app.core.database import SessionLocal, init_db
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService
from app.services.rag_service import RAGService

def test_full_interview_lifecycle():
    init_db()
    db = SessionLocal()
    try:
        # Ingest docs
        RAGService.ingest_documents(db, force_reindex=True)

        # 1. Create candidate
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name="Jordan Smith",
            target_role="AI/ML Engineer",
            years_exp=3.0,
            resume_text="AI engineer specialized in PyTorch, RAG architectures, FastAPI, and model evaluation.",
            email="jordan@example.com"
        )
        assert candidate.id.startswith("cand_")

        # 2. Create interview session
        session = InterviewService.create_interview(
            db=db,
            candidate_id=candidate.id,
            target_role="AI/ML Engineer",
            total_questions=3
        )
        assert session.status == "in_progress"
        assert session.current_question_index == 0
        assert len(session.questions) == 1

        first_q = session.questions[0]
        assert first_q.retrieved_context_text is not None

        # 3. Submit answer to question 1
        ans1_res = InterviewService.submit_answer(
            db=db,
            question_id=first_q.id,
            answer_text="RAG combines dense vector retrieval via embeddings with LLMs to provide grounded context and prevent model hallucinations.",
            code_snippet=None
        )
        assert ans1_res.evaluation.overall_score >= 1.0
        assert ans1_res.next_question is not None

        # 4. Submit answer to question 2
        q2_id = ans1_res.next_question.id
        ans2_res = InterviewService.submit_answer(
            db=db,
            question_id=q2_id,
            answer_text="Model fine-tuning with LoRA decomposes update matrices into lower rank representations to cut memory requirements by 90%.",
            code_snippet="from peft import LoraConfig, get_peft_model"
        )

        # 5. Submit answer to question 3 (final question)
        q3_id = ans2_res.next_question.id
        ans3_res = InterviewService.submit_answer(
            db=db,
            question_id=q3_id,
            answer_text="LLM guardrails sanitize input prompts and inspect output tokens against safety classifiers and groundness metrics.",
            code_snippet=None
        )
        assert ans3_res.interview_completed is True

        # 6. Verify final report
        report_res = ReportService.get_report_response(db, session.id)
        assert report_res.overall_score > 0.0
        assert report_res.hiring_recommendation in ["Strong Hire", "Hire", "Weak Hire", "No Hire"]
        assert len(report_res.traceable_qa_history) == 3

    finally:
        db.close()

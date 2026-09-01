import pytest
from app.core.database import SessionLocal, init_db
from app.models.domain import InterviewSession, Question, Answer, Evaluation
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.evaluation_service import EvaluationService, DIFFICULTY_LEVELS
from app.services.rag_service import RAGService

def test_deterministic_difficulty_adaptation():
    # High score promotes difficulty level
    assert EvaluationService.determine_next_difficulty("Junior", 9.0) == "Intermediate"
    assert EvaluationService.determine_next_difficulty("Intermediate", 8.5) == "Senior"
    assert EvaluationService.determine_next_difficulty("Senior", 8.0) == "Principal"
    assert EvaluationService.determine_next_difficulty("Principal", 9.5) == "Principal"  # Max ceiling

    # Low score demotes difficulty level
    assert EvaluationService.determine_next_difficulty("Principal", 4.0) == "Senior"
    assert EvaluationService.determine_next_difficulty("Senior", 5.0) == "Intermediate"
    assert EvaluationService.determine_next_difficulty("Intermediate", 3.0) == "Junior"
    assert EvaluationService.determine_next_difficulty("Junior", 2.0) == "Junior"  # Floor limit

    # Moderate score maintains difficulty level
    assert EvaluationService.determine_next_difficulty("Intermediate", 7.5) == "Intermediate"
    assert EvaluationService.determine_next_difficulty("Senior", 6.0) == "Senior"

def test_interview_engine_lifecycle_state_transitions():
    init_db()
    db = SessionLocal()
    try:
        RAGService.ingest_documents(db, force_reindex=True)

        # 1. START: Create Candidate & Session
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name="Morgan Reed",
            target_role="Backend Engineer",
            years_exp=5.0,
            resume_text="Senior Backend Engineer specializing in PostgreSQL, FastAPI, Redis, Distributed Systems, and microservices.",
            email="morgan@example.com"
        )

        session = InterviewService.create_interview(
            db=db,
            candidate_id=candidate.id,
            target_role="Backend Engineer",
            total_questions=3
        )

        # Lifecycle State check 1: START -> QUESTION 1
        assert session.status == "in_progress"
        assert session.current_question_index == 0
        assert session.current_difficulty == "Intermediate"
        assert len(session.questions) == 1

        q1 = session.questions[0]
        assert q1.order_index == 0
        assert q1.question is not None

        # Lifecycle State check 2: ANSWER 1 -> EVALUATION 1 -> NEXT QUESTION
        ans1_text = (
            "Database sharding horizontally partitions data across multiple independent database nodes based on a shard key. "
            "Consistent hashing or hash-based routing ensures even data distribution while minimizing re-sharding overhead during cluster scaling."
        )
        res1 = InterviewService.submit_answer(
            db=db,
            question_id=q1.id,
            answer_text=ans1_text,
            code_snippet="def get_shard(user_id, num_shards):\n    return hash(user_id) % num_shards"
        )

        eval1 = res1.evaluation
        assert eval1.score >= 8.0
        assert eval1.technical_accuracy >= 8.0
        assert eval1.conceptual_depth >= 8.0
        assert eval1.clarity >= 8.0
        assert isinstance(eval1.strengths, list) and len(eval1.strengths) > 0
        assert isinstance(eval1.missing_concepts, list)
        assert eval1.feedback is not None
        assert "chain-of-thought" not in eval1.feedback.lower()
        assert res1.interview_completed is False

        # Verify deterministic difficulty progression (Intermediate -> Senior due to score >= 8.0)
        db.refresh(session)
        assert session.current_difficulty == "Senior"
        assert session.current_question_index == 1

        # Lifecycle State check 3: ANSWER 2 -> EVALUATION 2 -> NEXT QUESTION (Weak answer testing demotion)
        q2_dto = res1.next_question
        assert q2_dto.order_index == 1
        assert q2_dto.difficulty == "Senior"

        ans2_text = "I don't know much about this topic."
        res2 = InterviewService.submit_answer(
            db=db,
            question_id=q2_dto.id,
            answer_text=ans2_text,
            code_snippet=None
        )

        eval2 = res2.evaluation
        assert eval2.score < 5.5
        assert res2.interview_completed is False

        # Verify deterministic difficulty demotion (Senior -> Intermediate due to score < 5.5)
        db.refresh(session)
        assert session.current_difficulty == "Intermediate"
        assert session.current_question_index == 2

        # Lifecycle State check 4: ANSWER 3 (Final Question) -> EVALUATION 3 -> COMPLETE
        q3_dto = res2.next_question
        assert q3_dto.order_index == 2

        ans3_text = "Distributed caching via Redis uses TTL expiration policies and LRU eviction to prevent memory bloat."
        res3 = InterviewService.submit_answer(
            db=db,
            question_id=q3_dto.id,
            answer_text=ans3_text,
            code_snippet=None
        )

        assert res3.interview_completed is True
        db.refresh(session)
        assert session.status == "completed"

        # Verify database persistence of all questions, answers, and evaluations
        db_questions = db.query(Question).filter(Question.interview_id == session.id).order_by(Question.index).all()
        assert len(db_questions) == 3
        for q in db_questions:
            assert q.answer is not None
            assert q.answer.evaluation is not None
            assert q.answer.evaluation.score > 0.0

    finally:
        db.close()

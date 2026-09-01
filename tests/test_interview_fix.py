import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.database import SessionLocal, init_db
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.question_generator import QuestionGeneratorService
from app.services.rag_service import RAGService
from app.models.domain import InterviewSession, Question, Answer
from app.api.endpoints.interviews import get_interview

@pytest.fixture(scope="module")
def setup_db():
    init_db()
    db = SessionLocal()
    # Ingest docs to ensure RAG knowledge base exists
    RAGService.ingest_documents(db, force_reindex=True)
    yield db
    db.close()

def test_1_first_question_generated(setup_db: Session):
    """Test 1: First question is generated on interview creation."""
    db = setup_db
    candidate = ResumeService.create_candidate_from_resume(
        db=db,
        name="Alex Turner",
        target_role="Backend Engineer",
        years_exp=4.0,
        resume_text="Backend engineer experienced in Python, PostgreSQL, Redis, and microservices.",
        email="alex@example.com"
    )

    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=4
    )

    assert session.status == "in_progress"
    assert session.current_question_index == 0
    assert len(session.questions) == 1
    
    first_q = session.questions[0]
    assert first_q.order_index == 0
    assert first_q.question is not None
    assert len(first_q.question.strip()) > 20

def test_2_answering_q1_generates_q2(setup_db: Session):
    """Test 2: Answering question 1 generates question 2."""
    db = setup_db
    candidate = db.query(InterviewSession).all()[-1].candidate
    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=4
    )

    q1 = session.questions[0]
    ans_res = InterviewService.submit_answer(
        db=db,
        question_id=q1.id,
        answer_text="PostgreSQL B-Tree indexes significantly reduce lookup time for equality and range queries.",
        code_snippet="CREATE INDEX idx_user_email ON users(email);"
    )

    assert ans_res.next_question is not None
    assert ans_res.next_question.order_index == 1
    assert session.current_question_index == 1

def test_3_question2_different_from_question1(setup_db: Session):
    """Test 3: Question 2 is different from question 1."""
    db = setup_db
    candidate = db.query(InterviewSession).all()[-1].candidate
    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=4
    )

    q1 = session.questions[0]
    ans1_res = InterviewService.submit_answer(
        db=db,
        question_id=q1.id,
        answer_text="Distributed caching with Redis helps offload read traffic from primary relational databases.",
        code_snippet="redis.set('key', 'val', ex=3600)"
    )

    q2_text = ans1_res.next_question.question
    norm_q1 = QuestionGeneratorService.normalize_text(q1.question)
    norm_q2 = QuestionGeneratorService.normalize_text(q2_text)

    assert norm_q1 != norm_q2
    assert q1.question != q2_text

def test_4_submitting_q2_generates_q3(setup_db: Session):
    """Test 4: Submitting question 2 generates question 3."""
    db = setup_db
    candidate = db.query(InterviewSession).all()[-1].candidate
    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=4
    )

    q1 = session.questions[0]
    ans1_res = InterviewService.submit_answer(
        db=db,
        question_id=q1.id,
        answer_text="Redis cluster sharding distributes keys using CRC16 hash slots across multiple master nodes.",
        code_snippet=None
    )

    q2_id = ans1_res.next_question.id
    ans2_res = InterviewService.submit_answer(
        db=db,
        question_id=q2_id,
        answer_text="Optimistic concurrency control uses version numbers or timestamps to detect write conflicts.",
        code_snippet=None
    )

    assert ans2_res.next_question is not None
    assert ans2_res.next_question.order_index == 2

def test_5_same_question_never_returned_twice(setup_db: Session):
    """Test 5: The same question is never returned twice across the full interview session."""
    db = setup_db
    candidate = ResumeService.create_candidate_from_resume(
        db=db,
        name="Sam Rivera",
        target_role="AI/ML Engineer",
        years_exp=3.0,
        resume_text="AI engineer focused on PyTorch, vector databases, RAG, and LLM fine-tuning.",
        email="sam@example.com"
    )

    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="AI/ML Engineer",
        total_questions=4
    )

    asked_questions = [session.questions[0].question]

    curr_q_id = session.questions[0].id
    for i in range(3):
        ans_res = InterviewService.submit_answer(
            db=db,
            question_id=curr_q_id,
            answer_text=f"Sample technical explanation for step {i+1} touching on technical context and design trade-offs.",
            code_snippet=None
        )
        if ans_res.next_question:
            next_text = ans_res.next_question.question
            norm_next = QuestionGeneratorService.normalize_text(next_text)
            for prev in asked_questions:
                norm_prev = QuestionGeneratorService.normalize_text(prev)
                assert norm_next != norm_prev, f"Duplicate question detected: '{next_text}' matches '{prev}'"
            asked_questions.append(next_text)
            curr_q_id = ans_res.next_question.id

    assert len(asked_questions) == 4

def test_6_duplicate_generated_by_llm_is_rejected(setup_db: Session):
    """Test 6: A duplicate question candidate generated by the LLM is rejected and regenerated."""
    db = setup_db
    retrieved_chunks = RAGService.search_relevant_chunks(db, "System Design", "Backend Engineer", top_k=2)
    previous_questions = ["How would you design a distributed caching layer using Redis for high throughput?"]

    # Candidate identical to previous question
    duplicate_candidate = "How would you design a distributed caching layer using Redis for high throughput?"
    is_valid, reason, score = QuestionGeneratorService.validate_grounded_question(
        question_text=duplicate_candidate,
        retrieved_chunks=retrieved_chunks,
        previous_questions=previous_questions,
        topic="System Design"
    )

    assert is_valid is False
    assert "Exact duplicate" in reason or "similar" in reason

def test_7_double_submission_protection(setup_db: Session):
    """Test 7: Submitting an answer to the same question twice raises ValueError (409 Conflict)."""
    db = setup_db
    candidate = db.query(InterviewSession).all()[-1].candidate
    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=3
    )

    q1 = session.questions[0]
    InterviewService.submit_answer(
        db=db,
        question_id=q1.id,
        answer_text="First answer submission.",
        code_snippet=None
    )

    with pytest.raises(ValueError, match="already been answered"):
        InterviewService.submit_answer(
            db=db,
            question_id=q1.id,
            answer_text="Second attempt submission (duplicate submit).",
            code_snippet=None
        )

def test_8_refresh_interview_page_preserves_current_question(setup_db: Session):
    """Test 8: Refreshing the interview page (calling get_interview) does not reset the current question."""
    db = setup_db
    candidate = db.query(InterviewSession).all()[-1].candidate
    session = InterviewService.create_interview(
        db=db,
        candidate_id=candidate.id,
        target_role="Backend Engineer",
        total_questions=3
    )

    q1 = session.questions[0]
    ans_res = InterviewService.submit_answer(
        db=db,
        question_id=q1.id,
        answer_text="Database indexing speeds up search operations at the cost of write amplification.",
        code_snippet=None
    )

    q2_id = ans_res.next_question.id

    # Simulate GET /interviews/{interview_id} refresh
    refreshed_session = get_interview(interview_id=session.id, db=db)

    assert refreshed_session.current_question_index == 1
    assert refreshed_session.current_question is not None
    assert refreshed_session.current_question.id == q2_id

def test_9_previous_questions_loaded_from_db(setup_db: Session):
    """Test 9: Previous questions are correctly loaded from the database for an interview session."""
    db = setup_db
    session = db.query(InterviewSession).filter(InterviewSession.status == "in_progress").first()
    
    questions = (
        db.query(Question)
        .filter(Question.interview_id == session.id)
        .order_by(Question.index)
        .all()
    )

    assert len(questions) > 0
    for q in questions:
        assert q.interview_id == session.id
        assert q.question is not None

def test_10_interview_resumes_correctly(setup_db: Session):
    """Test 10: Interview resumes correctly from persisted database state."""
    db = setup_db
    session = db.query(InterviewSession).filter(InterviewSession.status == "in_progress").first()
    
    current_index = session.current_question_index
    active_q = db.query(Question).filter(
        Question.interview_id == session.id,
        Question.index == current_index
    ).first()

    assert active_q is not None
    assert active_q.order_index == current_index

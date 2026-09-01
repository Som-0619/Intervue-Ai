import pytest
from app.core.database import SessionLocal, init_db
from app.models.domain import Candidate, InterviewSession, Question
from app.schemas.pydantic_schemas import KnowledgeChunkDTO, QuestionDTO
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.rag_service import RAGService
from app.services.question_generator import QuestionGeneratorService

def test_dynamic_query_formulation():
    query = QuestionGeneratorService.build_dynamic_query(
        target_role="Backend Engineer",
        topic="Database Indexing & Sharding",
        candidate_skills=["Python", "PostgreSQL", "FastAPI"],
        candidate_gaps=["Distributed Locks", "Query Optimization"],
        previous_questions=["What is B-Tree index?"]
    )
    assert "Database Indexing & Sharding" in query
    assert "Backend Engineer" in query
    assert "Query Optimization" in query or "Python" in query

def test_grounding_and_repetition_validation():
    chunks = [
        KnowledgeChunkDTO(
            id="chunk_test_123",
            document_name="backend_spec.txt",
            role_category="Backend Engineer",
            title="LSM-Tree Storage Engine",
            chunk_text="LSM-Trees append writes to a memtable before flushing to SSTables, optimizing write throughput over B-Trees.",
            score=0.95
        )
    ]

    # 1. Test generic question rejection
    is_valid, reason, _ = QuestionGeneratorService.validate_grounded_question(
        question_text="What is Database?",
        retrieved_chunks=chunks,
        previous_questions=[],
        topic="Database Indexing"
    )
    assert is_valid is False
    assert "generic" in reason.lower() or "short" in reason.lower()

    # 2. Test ungrounded question rejection (question completely unrelated to chunk text)
    is_valid, reason, _ = QuestionGeneratorService.validate_grounded_question(
        question_text="How would you configure CSS flexbox layout containers for responsive grid alignment?",
        retrieved_chunks=chunks,
        previous_questions=[],
        topic="Database Indexing"
    )
    assert is_valid is False
    assert "grounded" in reason.lower()

    # 3. Test repetition rejection
    prev_q = "How do LSM-Trees utilize memtables and SSTables to optimize write performance in databases?"
    is_valid, reason, _ = QuestionGeneratorService.validate_grounded_question(
        question_text=prev_q,
        retrieved_chunks=chunks,
        previous_questions=[prev_q],
        topic="Database Indexing"
    )
    assert is_valid is False
    assert "similar" in reason.lower()

    # 4. Test valid grounded question acceptance
    valid_q = "Given how LSM-Trees buffer writes in memtables before flushing to SSTables, how would you mitigate write stall risks in write-heavy backends?"
    is_valid, reason, score = QuestionGeneratorService.validate_grounded_question(
        question_text=valid_q,
        retrieved_chunks=chunks,
        previous_questions=[],
        topic="Database Indexing"
    )
    assert is_valid is True
    assert score > 0.10

def test_full_question_generation_pipeline_and_model_fields():
    init_db()
    db = SessionLocal()
    try:
        # Ingest docs
        RAGService.ingest_documents(db, force_reindex=True)

        # 1. Create candidate with skills and gaps
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name="Alex Morgan",
            target_role="AI/ML Engineer",
            years_exp=4.0,
            resume_text="Machine learning engineer experienced in PyTorch, RAG vector search, FastAPI, model evaluation, and LLM fine-tuning.",
            email="alex@example.com"
        )

        # 2. Create interview session
        session = InterviewService.create_interview(
            db=db,
            candidate_id=candidate.id,
            target_role="AI/ML Engineer",
            total_questions=3
        )

        # Verify Question 1 persistent structured model fields
        q1 = session.questions[0]
        assert isinstance(q1.id, str) and q1.id.startswith("q_")
        assert q1.interview_id == session.id
        assert q1.order_index == 0
        assert q1.index == 0  # synonym check
        assert q1.topic == session.selected_topics_json[0]
        assert q1.category_topic == q1.topic  # synonym check
        assert q1.difficulty == "Intermediate"
        assert q1.question is not None and len(q1.question) > 30
        assert q1.text == q1.question  # synonym check
        assert q1.generation_context is not None
        assert "dynamic_query" in q1.generation_context
        assert "candidate_profile" in q1.generation_context
        assert "validation" in q1.generation_context
        assert q1.retrieved_chunk_ids is not None
        assert len(q1.retrieved_chunk_ids) > 0

        # Verify QuestionDTO serialization contains both new and alias fields
        q1_dto = InterviewService.question_to_dto(db, q1)
        assert q1_dto.id == q1.id
        assert q1_dto.question == q1.question
        assert q1_dto.text == q1.question
        assert q1_dto.topic == q1.topic
        assert q1_dto.category_topic == q1.topic
        assert q1_dto.order_index == q1.order_index
        assert q1_dto.index == q1.order_index
        assert q1_dto.generation_context is not None
        assert len(q1_dto.retrieved_chunk_ids) > 0

        # 3. Submit answer and test Question 2 generation (with adaptive difficulty & state)
        ans1_res = InterviewService.submit_answer(
            db=db,
            question_id=q1.id,
            answer_text="RAG systems retrieve relevant document chunks via vector embeddings to augment LLM prompts with grounded context and minimize hallucination risks.",
            code_snippet=None
        )

        q2_dto = ans1_res.next_question
        assert q2_dto is not None
        assert q2_dto.order_index == 1
        assert q2_dto.question != q1.question  # Non-repetition check

        q2_db = db.query(Question).filter(Question.id == q2_dto.id).first()
        assert q2_db is not None
        assert q2_db.generation_context["interview_state"]["previous_questions_count"] == 1

    finally:
        db.close()

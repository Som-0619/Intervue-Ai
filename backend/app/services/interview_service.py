import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.domain import Candidate, InterviewSession, Question, Answer, Evaluation, KnowledgeChunk
from app.schemas.pydantic_schemas import (
    InterviewSessionResponse, QuestionDTO, KnowledgeChunkDTO,
    AnswerEvaluationResponse, EvaluationDTO
)
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.report_service import ReportService
from app.services.question_generator import QuestionGeneratorService
from app.services.evaluation_service import EvaluationService

import logging
logger = logging.getLogger(__name__)

class InterviewService:
    @staticmethod
    def select_dynamic_topics(candidate: Candidate, target_role: str, total_count: int = 5) -> List[str]:
        """Dynamically pick interview topics combining role essentials and candidate strengths/gaps."""
        role_lower = target_role.lower()
        parsed = candidate.parsed_profile_json or {}
        gaps = parsed.get("skill_gaps", [])
        strengths = parsed.get("strengths", [])

        # Standard baseline pool per role
        role_topic_pools = {
            "ai/ml engineer": ["RAG Architecture & Vector Search", "Model Fine-Tuning & Quantization", "Prompt Engineering & Guardrails", "LLM Evaluation Metrics", "Deep Learning Frameworks"],
            "backend engineer": ["High-Throughput System Design", "Database Indexing & Sharding", "Distributed Caching & Redis", "Concurrency & Lock Management", "API Security & Rate Limiting"],
            "frontend engineer": ["Virtual DOM & React Fiber", "Next.js SSR & Server Components", "Web Performance Optimization", "State Management & Reactivity", "Browser Security & XSS"],
            "fullstack engineer": ["End-to-End System Architecture", "REST & GraphQL API Design", "Relational & NoSQL Databases", "Frontend Rendering & State", "CI/CD & Containerization"],
            "devops/sre engineer": ["Kubernetes Orchestration", "Infrastructure as Code", "Observability & Tracing", "Load Balancing & Traffic Routing", "Disaster Recovery"]
        }

        base_pool = role_topic_pools.get(role_lower, ["System Design", "Database Management", "API Architecture", "Performance Optimization", "Security"])

        selected = []
        # Add gaps first to probe areas for improvement
        for gap in gaps:
            if len(selected) < 2:
                selected.append(gap)

        # Add remaining topics from base pool
        for topic in base_pool:
            if topic not in selected and len(selected) < total_count:
                selected.append(topic)

        # Fill with strengths if still needed
        for strength in strengths:
            if len(selected) < total_count and strength not in selected:
                selected.append(f"Advanced {strength}")

        return selected[:total_count]

    @classmethod
    def create_interview(
        cls,
        db: Session,
        candidate_id: str,
        target_role: str,
        total_questions: int = 5,
        custom_topics: Optional[List[str]] = None
    ) -> InterviewSession:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise ValueError(f"Candidate with ID '{candidate_id}' not found.")

        topics = custom_topics or cls.select_dynamic_topics(candidate, target_role, total_questions)

        interview_id = f"intv_{uuid.uuid4().hex[:10]}"
        session = InterviewSession(
            id=interview_id,
            candidate_id=candidate_id,
            target_role=target_role,
            status="in_progress",
            current_question_index=0,
            total_questions=len(topics),
            selected_topics_json=topics,
            current_difficulty="Intermediate"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Pre-generate first question
        cls.generate_question_for_index(db, session, 0)
        return session

    @classmethod
    def generate_question_for_index(cls, db: Session, session: InterviewSession, index: int) -> Question:
        return QuestionGeneratorService.generate_question_for_session(db=db, session=session, order_index=index)

    @classmethod
    def submit_answer(
        cls,
        db: Session,
        question_id: str,
        answer_text: str,
        code_snippet: Optional[str] = None
    ) -> AnswerEvaluationResponse:
        if not answer_text or not answer_text.strip():
            raise ValueError("Candidate answer text cannot be empty.")

        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError(f"Question with ID '{question_id}' not found.")

        if question.answer is not None:
            raise ValueError("Question has already been answered. Duplicate submissions are not allowed.")

        session = question.interview
        if session.status == "completed":
            raise ValueError("Interview session is already completed.")

        # 1. Store candidate answer
        ans_id = f"ans_{uuid.uuid4().hex[:10]}"
        answer = Answer(
            id=ans_id,
            question_id=question_id,
            candidate_answer_text=answer_text,
            code_snippet=code_snippet
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)

        # 2. Evaluate answer via EvaluationService
        eval_data = EvaluationService.evaluate_answer(
            question_text=question.question,
            category_topic=question.topic,
            difficulty=question.difficulty,
            candidate_answer=answer_text,
            code_snippet=code_snippet,
            retrieved_context_text=question.retrieved_context_text or ""
        )

        # 3. Store evaluation
        eval_id = f"eval_{uuid.uuid4().hex[:10]}"
        evaluation = Evaluation(
            id=eval_id,
            answer_id=ans_id,
            technical_correctness_score=eval_data["technical_accuracy"],
            depth_score=eval_data["conceptual_depth"],
            communication_score=eval_data["clarity"],
            overall_score=eval_data["score"],
            relevant_concepts_json=eval_data["strengths"],
            missed_concepts_json=eval_data["missing_concepts"],
            feedback_text=eval_data["feedback"],
            suggested_next_difficulty=eval_data["recommended_next_difficulty"]
        )
        db.add(evaluation)

        # 4 & 5. Update session difficulty & current index deterministically based on max existing order index + 1
        session.current_difficulty = eval_data["recommended_next_difficulty"]
        
        max_index = db.query(func.max(Question.index)).filter(Question.interview_id == session.id).scalar()
        next_index = (max_index + 1) if max_index is not None else (question.order_index + 1)
        session.current_question_index = next_index

        completed = False
        next_question_dto = None

        if next_index >= session.total_questions:
            session.status = "completed"
            db.commit()
            # Generate final interview report
            ReportService.generate_report(db, session.id)
            completed = True
        else:
            db.commit()
            next_q = cls.generate_question_for_index(db, session, next_index)
            next_question_dto = cls.question_to_dto(db, next_q)

        logger.info(
            f"SUBMIT ANSWER LOG | INTERVIEW ID: {session.id} | QUESTION ID: {question_id} | "
            f"ANSWER ID: {ans_id} | NEXT INDEX: {next_index} | COMPLETED: {completed}"
        )

        eval_dto = EvaluationDTO(
            id=evaluation.id,
            answer_id=ans_id,
            score=evaluation.score,
            technical_accuracy=evaluation.technical_accuracy,
            conceptual_depth=evaluation.conceptual_depth,
            clarity=evaluation.clarity,
            strengths=evaluation.strengths or [],
            missing_concepts=evaluation.missing_concepts or [],
            feedback=evaluation.feedback,
            recommended_next_difficulty=evaluation.recommended_next_difficulty,
            technical_correctness_score=evaluation.technical_correctness_score,
            depth_score=evaluation.depth_score,
            communication_score=evaluation.communication_score,
            overall_score=evaluation.overall_score,
            relevant_concepts=evaluation.relevant_concepts_json or [],
            missed_concepts=evaluation.missed_concepts_json or [],
            feedback_text=evaluation.feedback_text,
            suggested_next_difficulty=evaluation.suggested_next_difficulty
        )

        return AnswerEvaluationResponse(
            evaluation=eval_dto,
            next_question=next_question_dto,
            interview_completed=completed
        )

    @staticmethod
    def question_to_dto(db: Session, question: Question) -> QuestionDTO:
        chunk_ids = question.retrieved_chunk_ids or []
        chunks = []
        if chunk_ids:
            db_chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.id.in_(chunk_ids)).all()
            for dc in db_chunks:
                meta = dc.metadata_json or {}
                chunks.append(KnowledgeChunkDTO(
                    id=dc.id,
                    document_name=dc.document_name,
                    role_category=dc.role_category,
                    title=dc.title,
                    chunk_text=dc.chunk_text,
                    score=1.0,
                    metadata=meta
                ))
        if not chunks:
            chunks = RAGService.search_relevant_chunks(db, question.topic, question.interview.target_role, top_k=2)

        has_ans = question.answer is not None
        return QuestionDTO(
            id=question.id,
            interview_id=question.interview_id,
            question=question.question,
            topic=question.topic,
            difficulty=question.difficulty,
            generation_context=question.generation_context,
            retrieved_chunk_ids=chunk_ids,
            order_index=question.order_index,
            index=question.order_index,
            category_topic=question.topic,
            text=question.question,
            rationale=question.rationale,
            retrieved_chunks=chunks,
            retrieved_context_text=question.retrieved_context_text,
            has_answered=has_ans
        )


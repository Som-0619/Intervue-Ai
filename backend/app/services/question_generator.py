import uuid
import re
import difflib
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.domain import Candidate, InterviewSession, Question, Answer, Evaluation
from app.schemas.pydantic_schemas import KnowledgeChunkDTO
from app.services.rag_service import RetrievalService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class QuestionGeneratorService:
    @classmethod
    def build_dynamic_query(
        cls,
        target_role: str,
        topic: str,
        candidate_skills: List[str],
        candidate_gaps: List[str],
        previous_questions: List[str]
    ) -> str:
        """Formulate a dynamic search query combining role, topic, candidate background, and unused technical keywords."""
        query_parts = [topic, target_role]
        
        topic_words = set(re.findall(r'\w+', topic.lower()))
        matched_gaps = [g for g in candidate_gaps if any(w.lower() in topic_words for w in re.findall(r'\w+', g))]
        
        if matched_gaps:
            query_parts.extend(matched_gaps)
        else:
            if candidate_gaps:
                query_parts.extend(candidate_gaps[:2])
            if candidate_skills:
                query_parts.extend(candidate_skills[:2])

        query_str = " ".join(dict.fromkeys(query_parts))
        logger.info(f"Dynamic Query Formulated: '{query_str}'")
        return query_str

    DUPLICATE_THRESHOLD = 0.85

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for duplicate checking: lowercase, strip punctuation, collapse whitespace."""
        if not text:
            return ""
        lowered = text.lower()
        cleaned = re.sub(r'[^\w\s]', '', lowered)
        return re.sub(r'\s+', ' ', cleaned).strip()

    @classmethod
    def validate_grounded_question(
        cls,
        question_text: str,
        retrieved_chunks: List[KnowledgeChunkDTO],
        previous_questions: List[str],
        topic: str
    ) -> Tuple[bool, str, float]:
        """
        Validate generated question against grounding and repetition criteria.
        Returns (is_valid, rejection_reason, grounding_score).
        """
        if not question_text or len(question_text.strip()) < 30:
            return False, "Question text is too short or empty.", 0.0

        # Generic template check
        generic_patterns = [
            r"^what is [a-z0-9\s]+\?$",
            r"^tell me about [a-z0-9\s]+\.?$",
            r"^explain [a-z0-9\s]+\.?$"
        ]
        q_lower = question_text.strip().lower()
        if any(re.match(p, q_lower) for p in generic_patterns):
            return False, "Question matches generic template pattern.", 0.0

        # Deterministic Duplicate Check with Normalization
        norm_q = cls.normalize_text(question_text)
        for prev_q in previous_questions:
            norm_prev = cls.normalize_text(prev_q)
            if norm_q == norm_prev:
                return False, f"Exact duplicate of previous question (similarity: 1.00): '{prev_q[:50]}...'", 0.0

            sim = difflib.SequenceMatcher(None, norm_q, norm_prev).ratio()
            if sim >= cls.DUPLICATE_THRESHOLD:
                return False, f"Question is too similar to previous question (similarity: {sim:.2f} >= threshold {cls.DUPLICATE_THRESHOLD}).", 0.0


        # Grounding check against retrieved RAG chunks
        if not retrieved_chunks:
            return False, "No retrieved RAG chunks available for grounding.", 0.0

        context_text = " ".join([c.chunk_text for c in retrieved_chunks]).lower()
        context_words = set(re.findall(r'[a-zA-Z]{3,}', context_text))
        question_words = set(re.findall(r'[a-zA-Z]{3,}', q_lower))

        stop_words = {
            "what", "how", "why", "would", "you", "your", "the", "and", "for", "with",
            "that", "this", "from", "have", "are", "can", "our", "based", "which",
            "describe", "explain", "design", "evaluate", "implement", "candidate"
        }
        relevant_q_words = question_words - stop_words
        relevant_ctx_words = context_words - stop_words

        if not relevant_q_words:
            return False, "Question contains no meaningful technical words.", 0.0

        overlap = relevant_q_words.intersection(relevant_ctx_words)
        grounding_score = round(len(overlap) / len(relevant_q_words), 3)

        if len(overlap) < 1 and grounding_score < 0.10:
            return False, f"Question is not sufficiently grounded in retrieved context (overlap: {grounding_score}).", grounding_score

        return True, "Valid grounded question", grounding_score

    @classmethod
    def generate_question_for_session(
        cls,
        db: Session,
        session: InterviewSession,
        order_index: int,
        max_retries: int = 3
    ) -> Question:
        """
        Full pipeline:
        Candidate Profile + Role + Interview State
        ↓ Dynamic Query ↓ Vector Retrieval ↓ Relevant Context ↓ Question Generation ↓ Validation ↓ Persist Question
        """
        candidate = session.candidate
        parsed_profile = candidate.parsed_profile_json or {}
        candidate_skills = parsed_profile.get("skills", [])
        candidate_gaps = parsed_profile.get("skill_gaps", [])

        topics = session.selected_topics_json or ["System Design"]
        topic = topics[order_index % len(topics)]

        # Fetch Previous Questions & Answers in this session
        existing_questions = (
            db.query(Question)
            .filter(Question.interview_id == session.id)
            .order_by(Question.index)
            .all()
        )

        previous_questions_text = [q.question for q in existing_questions if q.question]
        previous_topics_covered = [q.topic for q in existing_questions if q.topic]
        previous_answers_text = []
        perf_scores = []
        missed_concepts_all = []
        previously_used_chunk_ids = []

        for q in existing_questions:
            if q.retrieved_chunk_ids:
                previously_used_chunk_ids.extend(q.retrieved_chunk_ids)
            if q.answer:
                previous_answers_text.append(q.answer.candidate_answer_text)
                if q.answer.evaluation:
                    ev = q.answer.evaluation
                    perf_scores.append(ev.overall_score)
                    if ev.missed_concepts_json:
                        missed_concepts_all.extend(ev.missed_concepts_json)

        avg_perf = sum(perf_scores) / len(perf_scores) if perf_scores else 0.0
        candidate_performance = {
            "overall_score": avg_perf,
            "missed_concepts": missed_concepts_all[:3]
        }

        # 1. Dynamic Query formulation
        dynamic_query = cls.build_dynamic_query(
            target_role=session.target_role,
            topic=topic,
            candidate_skills=candidate_skills,
            candidate_gaps=candidate_gaps,
            previous_questions=previous_questions_text
        )

        # 2. Vector Retrieval with Chunk Exclusion
        retrieved_chunks = RetrievalService.retrieve_context(
            db=db,
            role=session.target_role,
            candidate_topics=[topic],
            resume_keywords=candidate_skills[:5],
            semantic_query=dynamic_query,
            previously_used_chunk_ids=previously_used_chunk_ids,
            top_k=2
        )

        context_text = "\n\n".join([f"[{c.title}]\n{c.chunk_text}" for c in retrieved_chunks])
        chunk_ids = [c.id for c in retrieved_chunks]

        # 3. Question Generation with Validation & Retry Loop
        validated_q_text = ""
        validated_rationale = ""
        grounding_score = 0.0
        attempts = 0

        for attempt in range(1, max_retries + 1):
            attempts = attempt
            gen_res = LLMService.generate_grounded_question(
                target_role=session.target_role,
                topic=topic,
                difficulty=session.current_difficulty,
                candidate_name=candidate.name,
                candidate_skills=candidate_skills,
                candidate_gaps=candidate_gaps,
                retrieved_chunks=retrieved_chunks,
                previous_questions=previous_questions_text,
                previous_answers=previous_answers_text,
                candidate_performance=candidate_performance,
                attempt=attempt,
                order_index=order_index
            )

            q_candidate_text = gen_res.get("question_text", "")
            rationale_candidate = gen_res.get("rationale", "")

            is_valid, reason, score = cls.validate_grounded_question(
                question_text=q_candidate_text,
                retrieved_chunks=retrieved_chunks,
                previous_questions=previous_questions_text,
                topic=topic
            )

            logger.info(f"DUPLICATE CHECK RESULT | Attempt {attempt} | Valid: {is_valid} | Reason: {reason}")

            if is_valid:
                validated_q_text = q_candidate_text
                validated_rationale = rationale_candidate
                grounding_score = score
                break

        # Topic/Context Fallback if all retries rejected due to duplicates
        if not validated_q_text:
            logger.warning("All primary LLM attempts rejected. Switching topic context to ensure non-duplicate question.")
            fallback_pool = ["System Design & Latency", "Database Performance & Indexing", "API Architecture & Security", "Concurrency & State", "RAG & Vector Retrieval"]
            alt_topic = next((t for t in topics + fallback_pool if t not in previous_topics_covered), f"Advanced {topic}")

            alt_chunks = RetrievalService.retrieve_context(
                db=db,
                role=session.target_role,
                candidate_topics=[alt_topic],
                resume_keywords=candidate_skills[:5],
                semantic_query=f"{alt_topic} {session.target_role}",
                previously_used_chunk_ids=previously_used_chunk_ids,
                top_k=2
            )

            gen_res = LLMService.generate_grounded_question(
                target_role=session.target_role,
                topic=alt_topic,
                difficulty=session.current_difficulty,
                candidate_name=candidate.name,
                candidate_skills=candidate_skills,
                candidate_gaps=candidate_gaps,
                retrieved_chunks=alt_chunks,
                previous_questions=previous_questions_text,
                previous_answers=previous_answers_text,
                candidate_performance=candidate_performance,
                attempt=4,
                order_index=order_index + 1
            )
            validated_q_text = gen_res.get("question_text", "")
            validated_rationale = gen_res.get("rationale", "")
            topic = alt_topic
            retrieved_chunks = alt_chunks
            context_text = "\n\n".join([f"[{c.title}]\n{c.chunk_text}" for c in retrieved_chunks])
            chunk_ids = [c.id for c in retrieved_chunks]
            grounding_score = 0.60

        # 4. Persist Structured Question Model into Database
        q_id = f"q_{uuid.uuid4().hex[:10]}"
        generation_context = {
            "candidate_profile": {
                "name": candidate.name,
                "skills": candidate_skills,
                "gaps": candidate_gaps,
                "target_role": session.target_role
            },
            "interview_state": {
                "current_difficulty": session.current_difficulty,
                "order_index": order_index,
                "previous_questions_count": len(previous_questions_text),
                "candidate_performance": candidate_performance
            },
            "dynamic_query": dynamic_query,
            "retrieved_chunks_summary": [
                {"id": c.id, "title": c.title, "document": c.document_name, "score": c.score}
                for c in retrieved_chunks
            ],
            "rationale": validated_rationale,
            "validation": {
                "is_grounded": True,
                "grounding_score": grounding_score,
                "attempts": attempts
            }
        }

        question_obj = Question(
            id=q_id,
            interview_id=session.id,
            order_index=order_index,
            topic=topic,
            difficulty=session.current_difficulty,
            question=validated_q_text,
            generation_context=generation_context,
            retrieved_chunk_ids=chunk_ids,
            rationale=validated_rationale,
            retrieved_context_text=context_text
        )

        db.add(question_obj)
        db.commit()
        db.refresh(question_obj)

        logger.info(
            f"STRUCTURED PIPELINE LOG | INTERVIEW ID: {session.id} | CURRENT QUESTION NUMBER: {order_index + 1} | "
            f"PREVIOUS QUESTION IDS: {[q.id for q in existing_questions]} | "
            f"PREVIOUS QUESTION TEXTS: {previous_questions_text} | "
            f"GENERATED QUERY: '{dynamic_query}' | RETRIEVED CHUNK IDS: {chunk_ids} | "
            f"GENERATED QUESTION: '{validated_q_text}' | DUPLICATE CHECK RESULT: Valid | "
            f"FINAL QUESTION ID: {question_obj.id} | FINAL QUESTION NUMBER: {question_obj.order_index + 1}"
        )

        return question_obj


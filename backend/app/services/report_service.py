import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.domain import InterviewSession, InterviewReport, Question, Answer, Evaluation
from app.schemas.pydantic_schemas import (
    InterviewReportResponse, CategoryScoreDetailDTO, TraceableQADTO,
    QuestionDTO, EvaluationDTO, KnowledgeChunkDTO, QuestionAnalysisDTO,
    KnowledgeSourceMetadataDTO
)

MANDATORY_CATEGORIES = [
    "fundamentals",
    "applied knowledge",
    "problem solving",
    "resume/project understanding"
]

class ReportService:
    @classmethod
    def generate_report(cls, db: Session, interview_id: str) -> InterviewReport:
        session = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
        if not session:
            raise ValueError(f"Interview session '{interview_id}' not found.")

        # Check existing report
        existing = db.query(InterviewReport).filter(InterviewReport.interview_id == interview_id).first()
        if existing:
            return existing

        questions = db.query(Question).filter(Question.interview_id == interview_id).order_by(Question.index).all()
        
        all_eval_scores = []
        strengths = set()
        weaknesses = set()

        category_scores_map = {}

        for q in questions:
            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                all_eval_scores.append(ev.score)
                
                cat = q.topic
                if cat not in category_scores_map:
                    category_scores_map[cat] = {"total": 0.0, "count": 0}
                category_scores_map[cat]["total"] += ev.score
                category_scores_map[cat]["count"] += 1

                for concept in (ev.strengths or []):
                    strengths.add(concept)
                for concept in (ev.missing_concepts or []):
                    weaknesses.add(concept)

        avg_score = round(sum(all_eval_scores) / len(all_eval_scores), 1) if all_eval_scores else 0.0

        if not all_eval_scores:
            rec = "Insufficient Data"
        elif avg_score >= 8.5:
            rec = "Strong Hire"
        elif avg_score >= 7.0:
            rec = "Hire"
        elif avg_score >= 5.5:
            rec = "Weak Hire"
        else:
            rec = "No Hire"

        category_scores_list = [
            {
                "category": cat,
                "score": round(data["total"] / data["count"], 1),
                "max_score": 10.0,
                "questions_count": data["count"],
                "status": "evaluated"
            }
            for cat, data in category_scores_map.items()
        ]

        candidate_name = session.candidate.name if session.candidate else "Candidate"
        if not all_eval_scores:
            summary_text = f"{candidate_name} started an interview for {session.target_role}, but insufficient data exists to evaluate full performance."
        else:
            summary_text = (
                f"{candidate_name} completed a {len(all_eval_scores)}-question technical interview for the position of {session.target_role}. "
                f"Achieved an overall score of {avg_score}/10 with a recommendation of '{rec}'. "
                f"Demonstrated strong mastery in {', '.join(list(strengths)[:3]) if strengths else 'core technical principles'}, "
                f"while displaying growth potential in {', '.join(list(weaknesses)[:2]) if weaknesses else 'advanced edge-case trade-offs'}."
            )

        report_id = f"rep_{uuid.uuid4().hex[:10]}"
        report = InterviewReport(
            id=report_id,
            interview_id=interview_id,
            overall_score=avg_score,
            hiring_recommendation=rec,
            category_scores_json=category_scores_list,
            strengths_json=list(strengths)[:5],
            weaknesses_json=list(weaknesses)[:5],
            summary_text=summary_text
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def get_report_response(cls, db: Session, interview_id: str) -> InterviewReportResponse:
        report = cls.generate_report(db, interview_id)
        session = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
        questions = db.query(Question).filter(Question.interview_id == interview_id).order_by(Question.index).all()

        qa_history = []
        question_analysis_list = []

        # Mandatory 4 Core Category Metrics
        core_category_acc = {
            "fundamentals": {"total": 0.0, "count": 0},
            "applied knowledge": {"total": 0.0, "count": 0},
            "problem solving": {"total": 0.0, "count": 0},
            "resume/project understanding": {"total": 0.0, "count": 0}
        }

        all_missing_concepts = set()
        all_strengths = set()

        for q in questions:
            # Context Metadata
            sources_metadata = []
            gen_ctx = q.generation_context or {}
            summaries = gen_ctx.get("retrieved_chunks_summary", [])
            
            if summaries:
                for chunk in summaries:
                    sources_metadata.append(KnowledgeSourceMetadataDTO(
                        chunk_id=chunk.get("id", "chunk_ref"),
                        document_name=chunk.get("document", "reference_document.txt"),
                        title=chunk.get("title", f"{q.topic} Spec"),
                        page=1,
                        section="General",
                        relevance_score=chunk.get("score", 0.9),
                        snippet=q.retrieved_context_text[:250] if q.retrieved_context_text else "Grounding context"
                    ))
            elif q.retrieved_context_text:
                sources_metadata.append(KnowledgeSourceMetadataDTO(
                    chunk_id="chunk_ref_01",
                    document_name=f"{q.topic.lower().replace(' ', '_')}_ref.txt",
                    title=f"{q.topic} Context Grounding",
                    page=1,
                    section="Core Principles",
                    relevance_score=0.9,
                    snippet=q.retrieved_context_text[:250]
                ))

            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                
                # Map question scores into mandatory core categories
                core_category_acc["fundamentals"]["total"] += ev.technical_accuracy
                core_category_acc["fundamentals"]["count"] += 1

                core_category_acc["applied knowledge"]["total"] += ev.conceptual_depth
                core_category_acc["applied knowledge"]["count"] += 1

                core_category_acc["problem solving"]["total"] += ev.clarity
                core_category_acc["problem solving"]["count"] += 1

                core_category_acc["resume/project understanding"]["total"] += ev.score
                core_category_acc["resume/project understanding"]["count"] += 1

                for c in (ev.missing_concepts or []):
                    all_missing_concepts.add(c)
                for s in (ev.strengths or []):
                    all_strengths.add(s)

                ev_dto = EvaluationDTO(
                    id=ev.id,
                    answer_id=q.answer.id,
                    score=ev.score,
                    technical_accuracy=ev.technical_accuracy,
                    conceptual_depth=ev.conceptual_depth,
                    clarity=ev.clarity,
                    strengths=ev.strengths or [],
                    missing_concepts=ev.missing_concepts or [],
                    feedback=ev.feedback,
                    recommended_next_difficulty=ev.recommended_next_difficulty,
                    technical_correctness_score=ev.technical_correctness_score,
                    depth_score=ev.depth_score,
                    communication_score=ev.communication_score,
                    overall_score=ev.overall_score,
                    relevant_concepts=ev.relevant_concepts_json or [],
                    missed_concepts=ev.missed_concepts_json or [],
                    feedback_text=ev.feedback_text,
                    suggested_next_difficulty=ev.suggested_next_difficulty
                )

                q_dto = QuestionDTO(
                    id=q.id,
                    interview_id=q.interview_id,
                    question=q.question,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    generation_context=q.generation_context,
                    retrieved_chunk_ids=q.retrieved_chunk_ids or [],
                    order_index=q.order_index,
                    index=q.order_index,
                    category_topic=q.topic,
                    text=q.question,
                    rationale=q.rationale,
                    retrieved_context_text=q.retrieved_context_text,
                    has_answered=True
                )

                qa_history.append(TraceableQADTO(
                    question=q_dto,
                    answer_text=q.answer.candidate_answer_text,
                    code_snippet=q.answer.code_snippet,
                    evaluation=ev_dto
                ))

                question_analysis_list.append(QuestionAnalysisDTO(
                    question_id=q.id,
                    question=q.question,
                    candidate_answer=q.answer.candidate_answer_text,
                    score=ev.score,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    feedback=ev.feedback,
                    relevant_knowledge_source_metadata=sources_metadata,
                    evaluation=ev_dto
                ))
            else:
                question_analysis_list.append(QuestionAnalysisDTO(
                    question_id=q.id,
                    question=q.question,
                    candidate_answer="No answer submitted",
                    score=0.0,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    feedback="Question unanswered or pending evaluation.",
                    relevant_knowledge_source_metadata=sources_metadata,
                    evaluation=None
                ))

        # Build final category scores list including the 4 mandatory categories
        final_category_scores = []
        for cat_name in MANDATORY_CATEGORIES:
            data = core_category_acc[cat_name]
            if data["count"] > 0:
                final_category_scores.append(CategoryScoreDetailDTO(
                    category=cat_name,
                    score=round(data["total"] / data["count"], 1),
                    max_score=10.0,
                    questions_count=data["count"],
                    status="evaluated"
                ))
            else:
                final_category_scores.append(CategoryScoreDetailDTO(
                    category=cat_name,
                    score=0.0,
                    max_score=10.0,
                    questions_count=0,
                    status="insufficient_data"
                ))

        # Add topic-specific categories
        for item in (report.category_scores_json or []):
            if item.get("category") not in MANDATORY_CATEGORIES:
                final_category_scores.append(CategoryScoreDetailDTO(
                    category=item.get("category", "General"),
                    score=item.get("score", 0.0),
                    max_score=10.0,
                    questions_count=item.get("questions_count", 0),
                    status="evaluated" if item.get("questions_count", 0) > 0 else "insufficient_data"
                ))

        # Generate Actionable Recommendations
        recommendations = []
        if all_missing_concepts:
            for concept in list(all_missing_concepts)[:3]:
                recommendations.append(f"Deepen practical understanding and error handling regarding '{concept}'.")
        if report.overall_score >= 8.0:
            recommendations.append("Candidate demonstrates strong senior technical capability; recommend advancing to team system design rounds.")
        elif report.overall_score < 5.5:
            recommendations.append("Candidate requires foundational review of core system trade-offs and architecture basics before re-evaluating.")
        else:
            recommendations.append("Solid technical performance; suggest probing applied production failure recovery in follow-up sessions.")

        if not questions:
            recommendations.append("Insufficient data exists for complete evaluation. Conduct interview questions to generate actionable data.")

        return InterviewReportResponse(
            id=report.id,
            interview_id=interview_id,
            candidate_name=session.candidate.name if session.candidate else "Candidate",
            target_role=session.target_role,
            overall_score=report.overall_score,
            hiring_recommendation=report.hiring_recommendation,
            category_scores=final_category_scores,
            strengths=list(all_strengths)[:5] or (report.strengths_json or []),
            weaknesses=list(all_missing_concepts)[:5] or (report.weaknesses_json or []),
            missing_concepts=list(all_missing_concepts)[:5],
            recommendations=recommendations,
            question_by_question_analysis=question_analysis_list,
            traceable_qa_history=qa_history,
            summary_text=report.summary_text,
            created_at=report.created_at
        )

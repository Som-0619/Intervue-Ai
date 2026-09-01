from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from datetime import datetime

# --- Structured Resume Extraction Schemas ---
class ExperienceIndicators(BaseModel):
    years_of_experience: float = 0.0
    detected_titles: List[str] = Field(default_factory=list)

class CandidateProfile(BaseModel):
    name: str
    email: Optional[str] = None
    target_role: str
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    experience_indicators: ExperienceIndicators = Field(default_factory=ExperienceIndicators)
    strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    original_filename: Optional[str] = None

class CandidateCreateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    target_role: str
    years_of_experience: float = 0.0
    resume_text: Optional[str] = None

class CandidateResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    target_role: str
    years_of_experience: float
    original_filename: Optional[str] = None
    parsed_profile: Optional[CandidateProfile] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- RAG & Knowledge Base ---
class KnowledgeChunkDTO(BaseModel):
    id: str
    document_name: str
    role_category: str
    title: str
    chunk_text: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class IngestionRequest(BaseModel):
    force_reindex: bool = False

# --- Interview Session & Topic Selection ---
class InterviewCreateRequest(BaseModel):
    candidate_id: str
    target_role: str
    total_questions: int = 5
    custom_topics: Optional[List[str]] = None

class QuestionDTO(BaseModel):
    id: str
    interview_id: str
    question: str = ""
    topic: str = ""
    difficulty: str
    generation_context: Optional[Dict[str, Any]] = None
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    order_index: int = 0

    # Fields for backward compatibility
    index: int = 0
    category_topic: str = ""
    text: str = ""
    rationale: Optional[str] = None
    retrieved_chunks: List[KnowledgeChunkDTO] = Field(default_factory=list)
    retrieved_context_text: Optional[str] = None
    has_answered: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q_val = data.get("question") or data.get("text") or ""
            t_val = data.get("topic") or data.get("category_topic") or ""
            idx_val = data.get("order_index") if data.get("order_index") is not None else data.get("index", 0)
            chunk_ids = data.get("retrieved_chunk_ids") or data.get("retrieved_chunk_ids_json") or []
            data["question"] = q_val
            data["text"] = q_val
            data["topic"] = t_val
            data["category_topic"] = t_val
            data["order_index"] = idx_val
            data["index"] = idx_val
            data["retrieved_chunk_ids"] = chunk_ids
        return data

class InterviewSessionResponse(BaseModel):
    id: str
    candidate_id: str
    target_role: str
    status: str
    current_question_index: int
    total_questions: int
    selected_topics: List[str] = Field(default_factory=list)
    current_difficulty: str
    current_question: Optional[QuestionDTO] = None

    model_config = ConfigDict(from_attributes=True)

# --- Answer & Evaluation ---
class AnswerSubmitRequest(BaseModel):
    question_id: str
    candidate_answer_text: str
    code_snippet: Optional[str] = None

class EvaluationDTO(BaseModel):
    id: str
    answer_id: str
    score: float = 0.0
    technical_accuracy: float = 0.0
    conceptual_depth: float = 0.0
    clarity: float = 0.0
    strengths: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    feedback: str = ""
    recommended_next_difficulty: str = "Intermediate"

    # Backward compatibility fields
    technical_correctness_score: float = 0.0
    depth_score: float = 0.0
    communication_score: float = 0.0
    overall_score: float = 0.0
    relevant_concepts: List[str] = Field(default_factory=list)
    missed_concepts: List[str] = Field(default_factory=list)
    feedback_text: str = ""
    suggested_next_difficulty: str = "Intermediate"

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def sync_eval_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            score_val = data.get("score") if data.get("score") is not None else data.get("overall_score", 0.0)
            tech_val = data.get("technical_accuracy") if data.get("technical_accuracy") is not None else data.get("technical_correctness_score", 0.0)
            depth_val = data.get("conceptual_depth") if data.get("conceptual_depth") is not None else data.get("depth_score", 0.0)
            clarity_val = data.get("clarity") if data.get("clarity") is not None else data.get("communication_score", 0.0)
            strengths_val = data.get("strengths") or data.get("relevant_concepts") or []
            missing_val = data.get("missing_concepts") or data.get("missed_concepts") or []
            feedback_val = data.get("feedback") or data.get("feedback_text") or ""
            diff_val = data.get("recommended_next_difficulty") or data.get("suggested_next_difficulty") or "Intermediate"

            data["score"] = score_val
            data["overall_score"] = score_val
            data["technical_accuracy"] = tech_val
            data["technical_correctness_score"] = tech_val
            data["conceptual_depth"] = depth_val
            data["depth_score"] = depth_val
            data["clarity"] = clarity_val
            data["communication_score"] = clarity_val
            data["strengths"] = strengths_val
            data["relevant_concepts"] = strengths_val
            data["missing_concepts"] = missing_val
            data["missed_concepts"] = missing_val
            data["feedback"] = feedback_val
            data["feedback_text"] = feedback_val
            data["recommended_next_difficulty"] = diff_val
            data["suggested_next_difficulty"] = diff_val
        return data

class AnswerEvaluationResponse(BaseModel):
    evaluation: EvaluationDTO
    next_question: Optional[QuestionDTO] = None
    interview_completed: bool = False

# --- Interview Report ---
class CategoryScoreDTO(BaseModel):
    category: str
    score: float
    max_score: float = 10.0
    questions_count: int
    status: str = "evaluated"  # "evaluated" | "insufficient_data"

class CategoryScoreDetailDTO(BaseModel):
    category: str
    score: float
    max_score: float = 10.0
    questions_count: int
    status: str = "evaluated"  # "evaluated" | "insufficient_data"

class KnowledgeSourceMetadataDTO(BaseModel):
    chunk_id: str
    document_name: str
    title: str
    page: Optional[int] = 1
    section: Optional[str] = "General"
    relevance_score: Optional[float] = 0.9
    snippet: str

class QuestionAnalysisDTO(BaseModel):
    question_id: str
    question: str
    candidate_answer: str
    score: float
    topic: str
    difficulty: str
    feedback: str
    relevant_knowledge_source_metadata: List[KnowledgeSourceMetadataDTO] = Field(default_factory=list)
    evaluation: Optional[EvaluationDTO] = None

class TraceableQADTO(BaseModel):
    question: QuestionDTO
    answer_text: str
    code_snippet: Optional[str] = None
    evaluation: EvaluationDTO

class InterviewReportResponse(BaseModel):
    id: str
    interview_id: str
    candidate_name: str
    target_role: str
    overall_score: float
    hiring_recommendation: str
    category_scores: List[CategoryScoreDetailDTO] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    question_by_question_analysis: List[QuestionAnalysisDTO] = Field(default_factory=list)
    traceable_qa_history: List[TraceableQADTO] = Field(default_factory=list)
    summary_text: str
    created_at: datetime

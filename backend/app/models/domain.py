import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, synonym
from app.core.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    target_role = Column(String, nullable=False)
    years_of_experience = Column(Float, default=0.0)
    original_filename = Column(String, nullable=True)
    raw_resume_text = Column(Text, nullable=True)
    parsed_profile_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    interviews = relationship("InterviewSession", back_populates="candidate", cascade="all, delete-orphan")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    target_role = Column(String, nullable=False)
    status = Column(String, default="created")
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer, default=5)
    selected_topics_json = Column(JSON, nullable=True)
    current_difficulty = Column(String, default="Intermediate")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interviews")
    questions = relationship("Question", back_populates="interview", cascade="all, delete-orphan")
    report = relationship("InterviewReport", back_populates="interview", uselist=False, cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    interview_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    index = Column(Integer, nullable=False, default=0)
    category_topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    generation_context = Column(JSON, nullable=True)
    retrieved_chunk_ids_json = Column(JSON, nullable=True)
    rationale = Column(Text, nullable=True)
    retrieved_context_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Synonyms for requested field names
    order_index = synonym("index")
    topic = synonym("category_topic")
    question = synonym("text")
    retrieved_chunk_ids = synonym("retrieved_chunk_ids_json")

    interview = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, index=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    candidate_answer_text = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    submission_time = Column(DateTime, default=datetime.datetime.utcnow)

    question = relationship("Question", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, index=True)
    answer_id = Column(String, ForeignKey("answers.id"), nullable=False)
    technical_correctness_score = Column(Float, nullable=False)
    depth_score = Column(Float, nullable=False)
    communication_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    relevant_concepts_json = Column(JSON, nullable=True)
    missed_concepts_json = Column(JSON, nullable=True)
    feedback_text = Column(Text, nullable=False)
    suggested_next_difficulty = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Synonyms for requested evaluation fields
    technical_accuracy = synonym("technical_correctness_score")
    conceptual_depth = synonym("depth_score")
    clarity = synonym("communication_score")
    score = synonym("overall_score")
    strengths = synonym("relevant_concepts_json")
    missing_concepts = synonym("missed_concepts_json")
    feedback = synonym("feedback_text")
    recommended_next_difficulty = synonym("suggested_next_difficulty")

    answer = relationship("Answer", back_populates="evaluation")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, index=True)
    document_name = Column(String, nullable=False)
    role_category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    chunk_text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id = Column(String, primary_key=True, index=True)
    interview_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    hiring_recommendation = Column(String, nullable=False)
    category_scores_json = Column(JSON, nullable=False)
    strengths_json = Column(JSON, nullable=False)
    weaknesses_json = Column(JSON, nullable=False)
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    interview = relationship("InterviewSession", back_populates="report")

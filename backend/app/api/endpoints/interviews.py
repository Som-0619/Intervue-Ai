from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_schemas import (
    InterviewCreateRequest, InterviewSessionResponse, QuestionDTO,
    AnswerSubmitRequest, AnswerEvaluationResponse, InterviewReportResponse
)
from app.models.domain import InterviewSession, Question
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService

router = APIRouter()

@router.post("/", response_model=InterviewSessionResponse)
def create_interview(payload: InterviewCreateRequest, db: Session = Depends(get_db)):
    try:
        session = InterviewService.create_interview(
            db=db,
            candidate_id=payload.candidate_id,
            target_role=payload.target_role,
            total_questions=payload.total_questions,
            custom_topics=payload.custom_topics
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Fetch active question DTO
    q_index = session.current_question_index
    q = db.query(Question).filter(
        Question.interview_id == session.id,
        Question.index == q_index
    ).first()
    
    current_q_dto = InterviewService.question_to_dto(db, q) if q else None

    return InterviewSessionResponse(
        id=session.id,
        candidate_id=session.candidate_id,
        target_role=session.target_role,
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        selected_topics=session.selected_topics_json or [],
        current_difficulty=session.current_difficulty,
        current_question=current_q_dto
    )

@router.get("/{interview_id}", response_model=InterviewSessionResponse)
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    session = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Interview '{interview_id}' not found.")

    q_index = session.current_question_index
    q = db.query(Question).filter(
        Question.interview_id == session.id,
        Question.index == q_index
    ).first()
    
    current_q_dto = InterviewService.question_to_dto(db, q) if q else None

    return InterviewSessionResponse(
        id=session.id,
        candidate_id=session.candidate_id,
        target_role=session.target_role,
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions=session.total_questions,
        selected_topics=session.selected_topics_json or [],
        current_difficulty=session.current_difficulty,
        current_question=current_q_dto
    )

@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
def get_interview_report(interview_id: str, db: Session = Depends(get_db)):
    try:
        response = ReportService.get_report_response(db=db, interview_id=interview_id)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/answers/submit", response_model=AnswerEvaluationResponse)
def submit_answer(payload: AnswerSubmitRequest, db: Session = Depends(get_db)):
    try:
        res = InterviewService.submit_answer(
            db=db,
            question_id=payload.question_id,
            answer_text=payload.candidate_answer_text,
            code_snippet=payload.code_snippet
        )
        return res
    except ValueError as ve:
        err_str = str(ve)
        if "already been answered" in err_str:
            raise HTTPException(status_code=409, detail=err_str)
        elif "not found" in err_str:
            raise HTTPException(status_code=404, detail=err_str)
        else:
            raise HTTPException(status_code=400, detail=err_str)

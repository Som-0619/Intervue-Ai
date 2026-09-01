from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_schemas import InterviewReportResponse
from app.services.report_service import ReportService

router = APIRouter()

@router.get("/{interview_id}", response_model=InterviewReportResponse)
def get_interview_report(interview_id: str, db: Session = Depends(get_db)):
    try:
        response = ReportService.get_report_response(db=db, interview_id=interview_id)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

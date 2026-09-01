import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pydantic_schemas import CandidateCreateRequest, CandidateResponse, CandidateProfile
from app.services.resume_service import ResumeService
from app.models.domain import Candidate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=CandidateResponse)
def create_candidate(
    payload: CandidateCreateRequest,
    db: Session = Depends(get_db)
):
    try:
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name=payload.name,
            target_role=payload.target_role,
            years_exp=payload.years_of_experience,
            resume_text=payload.resume_text or f"Target Role: {payload.target_role}",
            email=payload.email,
            original_filename=None
        )
        return CandidateResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            target_role=candidate.target_role,
            years_of_experience=candidate.years_of_experience,
            original_filename=candidate.original_filename,
            parsed_profile=CandidateProfile(**candidate.parsed_profile_json) if candidate.parsed_profile_json else None,
            created_at=candidate.created_at
        )
    except ValueError as ve:
        logger.error(f"Candidate creation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal error in create_candidate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while creating candidate profile.")

@router.post("/upload", response_model=CandidateResponse)
async def upload_candidate_resume(
    name: str = Form(...),
    target_role: str = Form(...),
    years_of_experience: float = Form(1.0),
    email: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    resume_text = ""
    original_filename = None

    if file:
        original_filename = file.filename
        content = await file.read()
        try:
            filename_lower = (file.filename or "").lower()
            if filename_lower.endswith(".pdf"):
                resume_text = ResumeService.extract_text_from_pdf_bytes(content, filename=file.filename or "resume.pdf")
            elif filename_lower.endswith(".txt"):
                ResumeService.validate_file(file.filename or "resume.txt", content)
                resume_text = ResumeService.clean_text(content.decode("utf-8", errors="ignore"))
            else:
                raise ValueError(f"Unsupported file format for '{file.filename}'. Upload PDF (.pdf) or Text (.txt).")
        except ValueError as ve:
            logger.error(f"Resume file validation/extraction error: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Failed to read file upload content: {e}")
            raise HTTPException(status_code=400, detail="Unable to process uploaded resume file. File may be corrupted.")

    if not resume_text.strip():
        resume_text = f"Candidate Profile for {name}. Target Role: {target_role}. Years Experience: {years_of_experience}."

    try:
        candidate = ResumeService.create_candidate_from_resume(
            db=db,
            name=name,
            target_role=target_role,
            years_exp=years_of_experience,
            resume_text=resume_text,
            email=email,
            original_filename=original_filename
        )

        return CandidateResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            target_role=candidate.target_role,
            years_of_experience=candidate.years_of_experience,
            original_filename=candidate.original_filename,
            parsed_profile=CandidateProfile(**candidate.parsed_profile_json) if candidate.parsed_profile_json else None,
            created_at=candidate.created_at
        )
    except Exception as e:
        logger.error(f"Error persisting candidate from resume upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while persisting candidate data.")

@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate with ID '{candidate_id}' not found.")
    return CandidateResponse(
        id=cand.id,
        name=cand.name,
        email=cand.email,
        target_role=cand.target_role,
        years_of_experience=cand.years_of_experience,
        original_filename=cand.original_filename,
        parsed_profile=CandidateProfile(**cand.parsed_profile_json) if cand.parsed_profile_json else None,
        created_at=cand.created_at
    )

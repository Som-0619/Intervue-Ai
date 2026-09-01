import pytest
import fitz
from app.services.resume_service import ResumeService

def create_sample_pdf_bytes(text_content: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_validate_file_extensions_and_header():
    # Test empty filename
    with pytest.raises(ValueError, match="Filename cannot be empty"):
        ResumeService.validate_file("", b"%PDF-1.4 test")

    # Test empty file bytes
    with pytest.raises(ValueError, match="Uploaded file is empty"):
        ResumeService.validate_file("resume.pdf", b"")

    # Test unsupported extension
    with pytest.raises(ValueError, match="Unsupported file format"):
        ResumeService.validate_file("resume.exe", b"test content")

    # Test invalid PDF header signature
    with pytest.raises(ValueError, match="Invalid PDF file structure"):
        ResumeService.validate_file("resume.pdf", b"NOT_A_PDF_HEADER")

def test_clean_text():
    dirty_text = "  Jane   Doe \x00\x07  Senior Developer  \n\n\n\nSkills: Python \t\t FastAPI  "
    cleaned = ResumeService.clean_text(dirty_text)
    assert "\x00" not in cleaned
    assert "Jane Doe Senior Developer" in cleaned
    assert "\n\n\n" not in cleaned

def test_extract_text_from_pdf_bytes():
    pdf_bytes = create_sample_pdf_bytes("John Doe - Senior AI Engineer\nSkills: Python, PyTorch, RAG, FastAPI.")
    extracted = ResumeService.extract_text_from_pdf_bytes(pdf_bytes, filename="john_doe_resume.pdf")
    assert "John Doe - Senior AI Engineer" in extracted
    assert "PyTorch" in extracted

def test_parse_candidate_profile_structured_extraction():
    resume_text = """
    Alex Rivera - Senior AI/ML Engineer
    Email: alex.rivera@example.com
    Experience: 4.5 years of experience building production RAG systems and microservices.
    
    Technical Skills:
    Programming Languages: Python, TypeScript, SQL, C++
    Frameworks: FastAPI, PyTorch, React, Next.js, Django
    Tools & Technologies: Docker, Kubernetes, PostgreSQL, Redis, Kafka, AWS, ChromaDB
    Domains: AI/ML Engineering, RAG Systems, System Design, Distributed Systems
    
    Key Projects:
    Project: Multi-Modal RAG Platform for Enterprise Search
    Project: Real-Time Fraud Detection Engine
    """

    profile = ResumeService.parse_candidate_profile(
        raw_text=resume_text,
        default_name="Alex Rivera",
        target_role="AI/ML Engineer",
        years_exp=4.5,
        original_filename="alex_rivera_cv.pdf"
    )

    # Verify structured fields
    assert profile.name == "Alex Rivera"
    assert profile.original_filename == "alex_rivera_cv.pdf"
    assert "Python" in profile.programming_languages
    assert "FastAPI" in profile.frameworks
    assert "PyTorch" in profile.frameworks
    assert "Docker" in profile.tools
    assert "PostgreSQL" in profile.tools
    assert "AI/ML Engineering" in profile.domains
    assert "RAG Systems" in profile.domains
    assert len(profile.projects) >= 1
    assert profile.experience_indicators.years_of_experience >= 4.5
    assert "Senior AI/ML Engineer" in profile.experience_indicators.detected_titles or "AI/ML Engineer" in profile.experience_indicators.detected_titles
    assert len(profile.skills) > 0

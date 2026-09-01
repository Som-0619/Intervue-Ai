import re
import uuid
import logging
import fitz  # PyMuPDF
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.domain import Candidate
from app.schemas.pydantic_schemas import CandidateProfile, ExperienceIndicators

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class ResumeService:
    @staticmethod
    def validate_file(filename: str, file_bytes: bytes) -> None:
        """Validate resume file extension, size, and header signature."""
        if not filename:
            raise ValueError("Filename cannot be empty.")

        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.")

        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in ["pdf", "txt"]:
            raise ValueError(f"Unsupported file format '.{ext}'. Only PDF (.pdf) and Text (.txt) files are accepted.")

        if ext == "pdf":
            # Check PDF header signature (%PDF-)
            if not file_bytes.startswith(b"%PDF-"):
                raise ValueError("Invalid PDF file structure. File header signature mismatch.")

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Clean and normalize extracted resume text."""
        if not raw_text:
            return ""
        # Strip non-printable / control characters except newlines and tabs
        cleaned = re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', ' ', raw_text)
        # Normalize multiple spaces and tabs
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        # Replace 3 or more consecutive newlines with double newline
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    @classmethod
    def extract_text_from_pdf_bytes(cls, pdf_bytes: bytes, filename: str = "resume.pdf") -> str:
        """Extract text from raw PDF byte data using PyMuPDF (fitz) and clean it."""
        cls.validate_file(filename, pdf_bytes)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            extracted_pages = []
            for i, page in enumerate(doc):
                text = page.get_text("text")
                if text:
                    extracted_pages.append(text)
            doc.close()
            
            combined_text = "\n".join(extracted_pages)
            cleaned = cls.clean_text(combined_text)
            if not cleaned:
                raise ValueError("PDF file contains no readable text (scanned or image-only PDF).")
            logger.info(f"Successfully extracted {len(cleaned)} chars from PDF '{filename}'.")
            return cleaned
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for '{filename}': {e}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    @classmethod
    def parse_candidate_profile(
        cls,
        raw_text: str,
        default_name: str,
        target_role: str,
        years_exp: float = 0.0,
        original_filename: Optional[str] = None
    ) -> CandidateProfile:
        """Extract structured candidate information strictly from clean resume text without fabrication."""
        cleaned_text = cls.clean_text(raw_text)
        text_lower = cleaned_text.lower()

        # Taxonomy catalog for deterministic pattern recognition
        lang_catalog = ["Python", "JavaScript", "TypeScript", "C++", "Java", "Go", "Rust", "SQL", "HTML", "CSS", "Bash", "R"]
        framework_catalog = ["FastAPI", "React", "Next.js", "Node.js", "Django", "Flask", "PyTorch", "TensorFlow", "Express", "Spring Boot", "Tailwind CSS"]
        tool_catalog = ["Docker", "Kubernetes", "Git", "PostgreSQL", "Redis", "Kafka", "AWS", "GCP", "Azure", "Linux", "MongoDB", "ChromaDB", "FAISS"]
        domain_catalog = ["AI/ML Engineering", "RAG Systems", "System Design", "Distributed Systems", "Backend Engineering", "Frontend Engineering", "Microservices", "REST API", "CI/CD", "Web Security"]

        extracted_langs = [item for item in lang_catalog if re.search(r'\b' + re.escape(item) + r'\b', cleaned_text, re.IGNORECASE)]
        extracted_frameworks = [item for item in framework_catalog if re.search(r'\b' + re.escape(item) + r'\b', cleaned_text, re.IGNORECASE)]
        extracted_tools = [item for item in tool_catalog if re.search(r'\b' + re.escape(item) + r'\b', cleaned_text, re.IGNORECASE)]
        extracted_domains = [item for item in domain_catalog if re.search(r'\b' + re.escape(item) + r'\b', cleaned_text, re.IGNORECASE)]

        combined_tech = list(dict.fromkeys(extracted_langs + extracted_frameworks + extracted_tools))
        all_skills = list(dict.fromkeys(combined_tech + extracted_domains))

        # Detect experience indicators (years & job titles)
        exp_match = re.search(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\s+(?:of\s+)?experience', text_lower)
        if exp_match:
            try:
                parsed_exp = float(exp_match.group(1))
                if parsed_exp > years_exp:
                    years_exp = parsed_exp
            except ValueError:
                pass

        detected_titles = []
        title_keywords = ["Senior Software Engineer", "Software Engineer", "AI/ML Engineer", "Backend Engineer", "Frontend Engineer", "Lead Developer", "Fullstack Developer", "Architect", "SRE", "DevOps Engineer"]
        for title in title_keywords:
            if re.search(r'\b' + re.escape(title) + r'\b', cleaned_text, re.IGNORECASE):
                detected_titles.append(title)

        # Detect project headings or paragraphs
        projects = []
        project_matches = re.findall(r'(?:Project|Key Project|Built|Developed|Implemented):\s*([^\n\.]+)', cleaned_text, re.IGNORECASE)
        for pm in project_matches[:3]:
            p_clean = pm.strip()
            if len(p_clean) > 5:
                projects.append(p_clean)

        # Determine strengths & gap areas based on target role
        role_lower = target_role.lower()
        strengths = combined_tech[:4] if combined_tech else ["Software Development"]
        skill_gaps = []

        if "ai" in role_lower or "ml" in role_lower:
            if "RAG Systems" not in extracted_domains and "RAG" not in text_lower:
                skill_gaps.append("RAG Optimization & Vector Evaluation")
            if "PyTorch" not in extracted_frameworks and "TensorFlow" not in extracted_frameworks:
                skill_gaps.append("Deep Learning Frameworks (PyTorch/TensorFlow)")
        elif "backend" in role_lower:
            if "System Design" not in extracted_domains:
                skill_gaps.append("High-Throughput System Design")
            if "Redis" not in extracted_tools and "Kafka" not in extracted_tools:
                skill_gaps.append("Event-Driven Architecture & Caching Strategy")
        elif "frontend" in role_lower:
            if "Next.js" not in extracted_frameworks:
                skill_gaps.append("Next.js Server Components & SSR")

        if not skill_gaps:
            skill_gaps = ["Advanced Distributed Tracing", "Failure Recovery & Resilience"]

        experience_indicators = ExperienceIndicators(
            years_of_experience=years_exp,
            detected_titles=list(dict.fromkeys(detected_titles))
        )

        profile = CandidateProfile(
            name=default_name or "Candidate",
            email=None,
            target_role=target_role,
            skills=all_skills,
            technologies=combined_tech,
            programming_languages=extracted_langs,
            frameworks=extracted_frameworks,
            tools=extracted_tools,
            domains=extracted_domains,
            projects=projects,
            experience_indicators=experience_indicators,
            strengths=strengths,
            skill_gaps=skill_gaps,
            original_filename=original_filename
        )

        logger.info(f"Parsed candidate profile for '{default_name}': {len(all_skills)} skills, {len(projects)} projects.")
        return profile

    @classmethod
    def create_candidate_from_resume(
        cls,
        db: Session,
        name: str,
        target_role: str,
        years_exp: float,
        resume_text: str,
        email: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> Candidate:
        if not name or not name.strip():
            raise ValueError("Candidate name is required and cannot be empty.")
        if not target_role or not target_role.strip():
            raise ValueError("Target role is required and cannot be empty.")
        if not resume_text or not resume_text.strip():
            raise ValueError("Resume text is empty or invalid.")

        profile = cls.parse_candidate_profile(
            raw_text=resume_text,
            default_name=name.strip(),
            target_role=target_role.strip(),
            years_exp=years_exp,
            original_filename=original_filename
        )
        if email:
            profile.email = email

        candidate_id = f"cand_{uuid.uuid4().hex[:10]}"
        candidate = Candidate(
            id=candidate_id,
            name=profile.name,
            email=profile.email,
            target_role=target_role,
            years_of_experience=profile.experience_indicators.years_of_experience,
            original_filename=original_filename,
            raw_resume_text=resume_text,
            parsed_profile_json=profile.model_dump()
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

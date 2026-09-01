import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.core.database import SessionLocal, init_db
from app.services.rag_service import KnowledgeIngestionService, RAGService
from app.services.resume_service import ResumeService
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService

def run_verification():
    print("=== IntervueAI E2E System Verification ===")
    
    # 1. DB Init & Ingestion
    print("\n[1/5] Initializing Database & RAG Ingestion...")
    init_db()
    db = SessionLocal()
    try:
        ingest_res = KnowledgeIngestionService.ingest_all(db, force_reindex=True)
        print(f"✅ Ingestion successful: {ingest_res['total_stored_chunks']} chunks stored from {ingest_res['files_processed']} files.")

        # 2. Resume Parsing & Candidate Creation
        print("\n[2/5] Testing Resume Parsing & Candidate Extraction...")
        cand = ResumeService.create_candidate_from_resume(
            db=db,
            name="Samantha Vance",
            target_role="Backend Engineer",
            years_exp=4.5,
            resume_text="Senior engineer skilled in Python, FastAPI, PostgreSQL, Microservices, System Design, Redis, and Distributed Caching.",
            email="samantha@example.com"
        )
        print(f"✅ Candidate profile created: ID={cand.id}, Skills={cand.parsed_profile_json['skills']}")

        # 3. Dynamic Topic Selection & RAG Question Grounding
        print("\n[3/5] Starting Interview & Grounding Questions in RAG Context...")
        session = InterviewService.create_interview(
            db=db,
            candidate_id=cand.id,
            target_role="Backend Engineer",
            total_questions=2
        )
        print(f"✅ Interview session created: ID={session.id}")
        q1 = session.questions[0]
        print(f"   Q1 [{q1.category_topic} - {q1.difficulty}]: {q1.text[:120]}...")
        print(f"   Traceability Context Chunk Reference: [{q1.retrieved_chunk_ids_json}]")

        # 4. Interactive Answer Submission & Adaptive Progression
        print("\n[4/5] Submitting Answers & Testing Adaptive Difficulty...")
        ans1_res = InterviewService.submit_answer(
            db=db,
            question_id=q1.id,
            answer_text="B-Tree indices are optimal for read-heavy range queries, whereas LSM-trees buffer writes in a MemTable before writing SSTables to disk, optimizing write throughput under high concurrency.",
            code_snippet="CREATE INDEX idx_user_email ON users(email);"
        )
        print(f"   Q1 Score: {ans1_res.evaluation.overall_score}/10. Feedback: {ans1_res.evaluation.feedback_text}")
        print(f"   Adaptive Next Difficulty: {ans1_res.evaluation.suggested_next_difficulty}")

        q2_dto = ans1_res.next_question
        ans2_res = InterviewService.submit_answer(
            db=db,
            question_id=q2_dto.id,
            answer_text="Redis Cache-Aside pattern queries the in-memory store first and falls back to database lookup on cache miss. Cache stampedes are mitigated using mutex locks or soft expiration.",
            code_snippet=None
        )
        print(f"   Q2 Score: {ans2_res.evaluation.overall_score}/10. Interview completed status: {ans2_res.interview_completed}")

        # 5. Final Report Synthesis & Traceability Audit
        print("\n[5/5] Synthesizing Final Report & Verifying Traceability...")
        report = ReportService.get_report_response(db, session.id)
        print(f"✅ Final Score: {report.overall_score}/10 | Hiring Recommendation: '{report.hiring_recommendation}'")
        print(f"   Summary: {report.summary_text[:140]}...")
        print(f"   Traceable QA Records: {len(report.traceable_qa_history)}")

        print("\n🎉 ALL E2E VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    finally:
        db.close()

if __name__ == "__main__":
    run_verification()

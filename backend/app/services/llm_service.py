import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.pydantic_schemas import KnowledgeChunkDTO, EvaluationDTO

logger = logging.getLogger(__name__)

class LLMService:
    @classmethod
    def generate_grounded_question(
        cls,
        target_role: str,
        topic: str,
        difficulty: str,
        candidate_name: str = "Candidate",
        candidate_skills: Optional[List[str]] = None,
        candidate_gaps: Optional[List[str]] = None,
        retrieved_chunks: Optional[List[KnowledgeChunkDTO]] = None,
        previous_questions: Optional[List[str]] = None,
        previous_answers: Optional[List[str]] = None,
        candidate_performance: Optional[Dict[str, Any]] = None,
        attempt: int = 1,
        order_index: int = 0
    ) -> Dict[str, Any]:
        """Generate a context-grounded technical interview question using RAG knowledge, candidate profile, and interview state."""
        candidate_skills = candidate_skills or []
        candidate_gaps = candidate_gaps or []
        retrieved_chunks = retrieved_chunks or []
        previous_questions = previous_questions or []
        previous_answers = previous_answers or []
        candidate_performance = candidate_performance or {}

        context_str = "\n\n".join([f"[Source: {c.title}]\n{c.chunk_text}" for c in retrieved_chunks])
        prev_q_str = "\n".join([f"- Q{i+1}: {q}" for i, q in enumerate(previous_questions)]) if previous_questions else "None (First question)"
        prev_a_str = "\n".join([f"- A{i+1}: {a[:150]}..." for i, a in enumerate(previous_answers)]) if previous_answers else "None"
        
        perf_summary = f"Avg Score: {candidate_performance.get('overall_score', 'N/A')}, Missed: {', '.join(candidate_performance.get('missed_concepts', []))}" if candidate_performance else "No previous evaluations"

        provider = settings.LLM_PROVIDER.lower()
        if provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                prompt = f"""
You are an expert Lead Technical Interviewer designing a grounded interview question.

CANDIDATE CONTEXT:
- Name: {candidate_name}
- Target Role: {target_role}
- Current Difficulty Level: {difficulty}
- Candidate Known Skills: {', '.join(candidate_skills) if candidate_skills else 'General technical background'}
- Areas for Improvement: {', '.join(candidate_gaps) if candidate_gaps else 'None specified'}

INTERVIEW STATE:
- Current Question Number: {order_index + 1} (Attempt {attempt})
- Previous Questions Asked:
{prev_q_str}
- Previous Answers Summary:
{prev_a_str}
- Prior Performance: {perf_summary}

RETRIEVED RAG CONTEXT (MUST BE GROUNDED IN THIS TEXT):
{context_str}

REQUIREMENTS:
1. Generate ONE technical question on '{topic}' tailored for a {difficulty} level {target_role}.
2. GROUNDING REQUIREMENT: The question MUST directly test specific technical concepts, formulas, trade-offs, or architectures present in the RETRIEVED RAG CONTEXT above.
3. PERSONALIZATION: Reference candidate background or previous answer performance naturally when applicable.
4. STRICT NON-REPETITION REQUIREMENT: Do NOT generate a question that is identical or substantially similar to any previous question in text, concept, or structure. Ensure the question tests a different dimension or angle.
5. NO GENERIC TEMPLATES: Do NOT generate generic questions like 'What is X?' or 'Tell me about Y'. Test applied understanding, failure modes, design trade-offs, and implementation details.
6. NO FILE METADATA OR HEADERS: Do NOT include file names, page numbers, section headers, or knowledge base banners (e.g. 'ai_ml_engineering.txt', 'Section 1', 'INTERVUEAI KNOWLEDGE BASE') inside the question_text.
7. Output JSON strictly matching:
{
  "question_text": "<Your grounded technical question>",
  "rationale": "<Detailed rationale explaining how this tests candidate competency grounded in the RAG context and adapted to difficulty>"
}
"""
                response = model.generate_content(prompt)
                res_text = response.text.strip()
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                
                data = json.loads(res_text)
                return {
                    "question_text": data.get("question_text"),
                    "rationale": data.get("rationale")
                }
            except Exception as e:
                logger.warning(f"Gemini API call failed, using heuristic fallback: {e}")

        elif provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                prompt = f"""Generate a grounded technical interview question for {target_role} ({difficulty} level) on {topic}.\nCandidate skills: {candidate_skills}\nRAG Context:\n{context_str}\nPrevious Questions:\n{prev_q_str}\nREQUIREMENT: Do not generate a question that is identical or substantially similar to any previous question. Do not include document filenames or section banners in question_text.\nJSON format: {{"question_text": "...", "rationale": "..."}}"""
                res = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(res.choices[0].message.content)
                return {
                    "question_text": data.get("question_text"),
                    "rationale": data.get("rationale")
                }
            except Exception as e:
                logger.warning(f"OpenAI API call failed, using heuristic fallback: {e}")

        # --- Dynamic Heuristic Context-Grounded Question Engine ---
        chunk_idx = (order_index + attempt - 1) % len(retrieved_chunks) if retrieved_chunks else 0
        target_chunk = retrieved_chunks[chunk_idx] if (retrieved_chunks and chunk_idx < len(retrieved_chunks)) else (retrieved_chunks[0] if retrieved_chunks else None)
        
        chunk_text = target_chunk.chunk_text if target_chunk else "Core technical principles"
        chunk_title = target_chunk.title if target_chunk else topic

        # Extract specific technical sentences from retrieved chunk, ignoring section headers & banners
        sentences_filtered = []
        for s in re.split(r'[.!?]\s+|\n+', chunk_text):
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 20:
                continue
            if re.match(r'^(SECTION|CHAPTER|\=|\-|INTERVUEAI)\b', s_clean, re.IGNORECASE):
                if ':' in s_clean:
                    after_colon = s_clean.split(':', 1)[1].strip()
                    if len(after_colon) > 20:
                        s_clean = after_colon
                    else:
                        continue
                else:
                    continue
            sentences_filtered.append(s_clean)

        sentence_idx = (order_index + attempt - 1) % len(sentences_filtered) if sentences_filtered else 0
        grounded_snippet = sentences_filtered[sentence_idx] if (sentences_filtered and sentence_idx < len(sentences_filtered)) else (sentences_filtered[0] if sentences_filtered else "core technical principles and architecture")
        grounded_snippet = re.sub(r'^(SECTION\s+\d+[:\s]*|CHAPTER\s+\d+[:\s]*)', '', grounded_snippet, flags=re.IGNORECASE).strip()

        profile_ref = ""
        if candidate_skills:
            skill_pick = candidate_skills[(order_index + attempt - 1) % len(candidate_skills)]
            profile_ref = f"Given your background with {skill_pick} as a {target_role}, "
        elif target_role:
            profile_ref = f"As a {target_role}, "

        perf_ref = ""
        if candidate_performance.get("missed_concepts"):
            missed = candidate_performance["missed_concepts"][0]
            perf_ref = f"Building on your prior response regarding {missed}, "

        question_angles = [
            f"{profile_ref}{perf_ref}referencing our core architecture spec for {topic}: '{grounded_snippet}'. How would you design this component to maximize throughput and ensure high availability?",
            f"{profile_ref}{perf_ref}analyzing the technical spec for {topic}, which notes: '{grounded_snippet}'. What key failure modes, race conditions, or state inconsistencies could arise here, and how would you mitigate them?",
            f"{profile_ref}evaluating our reference implementation for {topic}: '{grounded_snippet}'. What architectural trade-offs between latency, memory footprint, and consistency would you prioritize for production scale?",
            f"{profile_ref}{perf_ref}our technical guide for {topic} highlights that '{grounded_snippet}'. How would you write automated unit/integration tests and monitor runtime metrics to safeguard this mechanism?"
        ]

        angle_idx = (order_index + attempt - 1) % len(question_angles)
        q_text = question_angles[angle_idx]
        rationale = f"Evaluates candidate's applied mastery of {topic} at {difficulty} level. Grounded in RAG reference [{chunk_title}] and tailored to candidate profile ({candidate_name}, {target_role})."

        return {
            "question_text": q_text,
            "rationale": rationale
        }


    @classmethod
    def evaluate_answer(
        cls,
        question_text: str,
        category_topic: str,
        difficulty: str,
        candidate_answer: str,
        code_snippet: Optional[str],
        retrieved_context_text: str
    ) -> Dict[str, Any]:
        """Evaluate technical accuracy, depth, and communication of candidate answer against RAG reference context."""
        provider = settings.LLM_PROVIDER.lower()
        if provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""
You are an expert interviewer evaluating a technical answer.
QUESTION: {question_text}
TOPIC: {category_topic} ({difficulty})
REFERENCE GROUNDING CONTEXT:
{retrieved_context_text}

CANDIDATE ANSWER:
{candidate_answer}
CODE SNIPPET: {code_snippet or 'None'}

Evaluate candidate answer strictly against the reference grounding context.
Return JSON with format:
{{
  "technical_correctness_score": <float 0-10>,
  "depth_score": <float 0-10>,
  "communication_score": <float 0-10>,
  "overall_score": <float 0-10>,
  "relevant_concepts": ["<concept1>", "<concept2>"],
  "missed_concepts": ["<concept1>", "<concept2>"],
  "feedback_text": "<Detailed constructive feedback>",
  "suggested_next_difficulty": "<Junior|Intermediate|Senior|Principal>"
}}
"""
                res = model.generate_content(prompt)
                res_text = res.text.strip()
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                return json.loads(res_text)
            except Exception as e:
                logger.warning(f"Gemini API call for evaluation failed: {e}")

        # --- Heuristic Evaluation Engine ---
        answer_length = len(candidate_answer.strip())
        code_bonus = 1.0 if code_snippet and len(code_snippet.strip()) > 10 else 0.0
        
        context_words = set(re.findall(r'\w+', retrieved_context_text.lower())) if retrieved_context_text else set()
        answer_words = set(re.findall(r'\w+', candidate_answer.lower()))
        
        if answer_length < 40:
            tech_score = 4.0
            depth = 3.5
            comm = 5.0
            feedback = "The answer was brief and missed core architectural details discussed in the reference material."
            suggested_diff = "Junior"
            relevant = ["Basic surface understanding"]
            missed = ["Detailed trade-offs", "Edge-case error handling", "Implementation specifics"]
        elif answer_length < 150:
            tech_score = 6.5 + code_bonus
            depth = 6.0
            comm = 7.0
            feedback = f"Solid foundational explanation on {category_topic}. Included key terms from reference material, but could elaborate more on production trade-offs."
            suggested_diff = "Intermediate"
            relevant = [w.capitalize() for w in list(context_words.intersection(answer_words))[:4]]
            missed = ["Distributed failure resilience", "Performance profiling metrics"]
        else:
            tech_score = 8.5 + code_bonus
            depth = 8.5
            comm = 9.0
            feedback = f"Comprehensive and well-structured answer on {category_topic}. Demonstrated clear mastery of technical context and practical implementation."
            suggested_diff = "Senior" if difficulty != "Principal" else "Principal"
            relevant = [w.capitalize() for w in list(context_words.intersection(answer_words))[:5]]
            missed = ["Niche optimization edge cases"]

        tech_score = min(10.0, max(1.0, tech_score))
        depth = min(10.0, max(1.0, depth))
        comm = min(10.0, max(1.0, comm))
        overall = round((tech_score * 0.5) + (depth * 0.3) + (comm * 0.2), 1)

        return {
            "technical_correctness_score": tech_score,
            "depth_score": depth,
            "communication_score": comm,
            "overall_score": overall,
            "relevant_concepts": relevant,
            "missed_concepts": missed,
            "feedback_text": feedback,
            "suggested_next_difficulty": suggested_diff
        }

import json
import re
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

DIFFICULTY_LEVELS = ["Junior", "Intermediate", "Senior", "Principal"]
STOP_WORDS = {
    "about", "after", "also", "and", "are", "because", "been", "being", "between", "could", "from", "have", "into",
    "more", "over", "that", "their", "then", "these", "they", "this", "through", "using", "when", "with", "would", "your",
    "will", "what", "which", "while", "where", "than", "them", "only", "such", "each", "does", "core", "guide"
}

class EvaluationService:
    @classmethod
    def determine_next_difficulty(cls, current_difficulty: str, overall_score: float) -> str:
        """
        Deterministic adaptive difficulty progression:
        - score >= 8.0: Promote to next difficulty level.
        - score < 5.5: Demote to previous difficulty level.
        - 5.5 <= score < 8.0: Maintain current difficulty.
        """
        curr = current_difficulty.capitalize() if current_difficulty else "Intermediate"
        if curr not in DIFFICULTY_LEVELS:
            curr = "Intermediate"

        curr_idx = DIFFICULTY_LEVELS.index(curr)

        if overall_score >= 8.0:
            next_idx = min(len(DIFFICULTY_LEVELS) - 1, curr_idx + 1)
        elif overall_score < 5.5:
            next_idx = max(0, curr_idx - 1)
        else:
            next_idx = curr_idx

        recommended = DIFFICULTY_LEVELS[next_idx]
        logger.info(f"Deterministic Difficulty Adaptation: current='{curr}', score={overall_score} -> recommended='{recommended}'")
        return recommended

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
        """
        Evaluates candidate answer against reference grounding context and returns structured evaluation fields:
        - technical_accuracy, conceptual_depth, clarity, score
        - strengths, missing_concepts, feedback, recommended_next_difficulty
        Does NOT expose evaluator chain-of-thought.
        """
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""
You are an expert technical interviewer evaluating a candidate's answer.

QUESTION: {question_text}
TOPIC: {category_topic} (Current Level: {difficulty})
REFERENCE RAG GROUNDING CONTEXT:
{retrieved_context_text}

CANDIDATE ANSWER:
{candidate_answer}
CODE SNIPPET: {code_snippet or 'None provided'}

REQUIREMENTS:
1. Evaluate candidate answer strictly against reference grounding context.
2. Provide numerical scores (0.0 to 10.0) for:
   - technical_accuracy (accuracy of concepts & syntax)
   - conceptual_depth (completeness, trade-off understanding)
   - clarity (structure, communication efficiency)
3. Return concise arrays for strengths and missing_concepts.
4. Output constructive feedback for the candidate (DO NOT include scratchpad or chain-of-thought thinking).
5. Output JSON matching EXACT schema:
{{
  "technical_accuracy": <float 0-10>,
  "conceptual_depth": <float 0-10>,
  "clarity": <float 0-10>,
  "strengths": ["<strength1>", "<strength2>"],
  "missing_concepts": ["<concept1>", "<concept2>"],
  "feedback": "<Clear constructive feedback>"
}}
"""
                res = model.generate_content(prompt)
                res_text = res.text.strip()
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0].strip()
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0].strip()
                
                raw_data = json.loads(res_text)
                
                tech_acc = min(10.0, max(0.0, float(raw_data.get("technical_accuracy", 7.0))))
                depth = min(10.0, max(0.0, float(raw_data.get("conceptual_depth", 7.0))))
                clarity = min(10.0, max(0.0, float(raw_data.get("clarity", 7.0))))
                overall_score = round((tech_acc * 0.5) + (depth * 0.3) + (clarity * 0.2), 1)

                next_diff = cls.determine_next_difficulty(difficulty, overall_score)

                return {
                    "score": overall_score,
                    "technical_accuracy": tech_acc,
                    "conceptual_depth": depth,
                    "clarity": clarity,
                    "strengths": raw_data.get("strengths", ["Solid core explanation"]),
                    "missing_concepts": raw_data.get("missing_concepts", []),
                    "feedback": raw_data.get("feedback", "Good response touching on key concepts."),
                    "recommended_next_difficulty": next_diff,
                    # Backward compatible fields
                    "technical_correctness_score": tech_acc,
                    "depth_score": depth,
                    "communication_score": clarity,
                    "overall_score": overall_score,
                    "relevant_concepts": raw_data.get("strengths", []),
                    "missed_concepts": raw_data.get("missing_concepts", []),
                    "feedback_text": raw_data.get("feedback", ""),
                    "suggested_next_difficulty": next_diff
                }
            except Exception as e:
                logger.warning(f"Gemini evaluation failed, falling back to heuristic engine: {e}")

        # --- Rule-Based, concept-grounded evaluation engine ---
        # Length improves communication only; it cannot establish technical correctness.
        answer_len = len(candidate_answer.strip())
        code_bonus = 0.5 if code_snippet and len(code_snippet.strip()) > 10 else 0.0
        tokenise = lambda text: {word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()) if word not in STOP_WORDS}
        context_terms = tokenise(retrieved_context_text)
        answer_terms = tokenise(candidate_answer)
        matched_words = sorted(context_terms.intersection(answer_terms))
        coverage = len(matched_words) / max(1, min(len(context_terms), 25))
        tradeoff_signals = {"trade-off", "tradeoffs", "latency", "consistency", "availability", "scalability", "failure", "risk", "monitoring", "rollback"}
        implementation_signals = {"implement", "test", "metric", "retry", "timeout", "cache", "index", "replica", "transaction"}
        depth_evidence = len(answer_terms.intersection(tradeoff_signals | implementation_signals))

        tech_acc = min(10.0, round(2.0 + (len(matched_words) * 1.1) + code_bonus, 1))
        depth = min(10.0, round(2.0 + (len(matched_words) * 0.65) + (depth_evidence * 0.55), 1))
        clarity = 3.5 if answer_len < 40 else (6.0 if answer_len < 120 else 7.5)
        if len(matched_words) >= 5:
            clarity = min(9.0, clarity + 0.5)

        strengths = [word.capitalize() for word in matched_words[:5]]
        missing_concepts = [word.capitalize() for word in sorted(context_terms - answer_terms)[:4]]
        if not matched_words:
            feedback = f"The response did not connect to the required technical concepts for {category_topic}; more length alone does not improve the score."
        elif len(matched_words) < 3:
            feedback = f"The response mentions some relevant concepts for {category_topic}, but needs more concrete mechanisms, trade-offs, and validation details."
        else:
            feedback = f"The response is grounded in relevant {category_topic} concepts. Strengthen it further by making trade-offs, failure handling, and validation explicit."

        overall_score = round((tech_acc * 0.5) + (depth * 0.3) + (clarity * 0.2), 1)
        next_diff = cls.determine_next_difficulty(difficulty, overall_score)

        return {
            "score": overall_score,
            "technical_accuracy": tech_acc,
            "conceptual_depth": depth,
            "clarity": clarity,
            "strengths": strengths,
            "missing_concepts": missing_concepts,
            "feedback": feedback,
            "recommended_next_difficulty": next_diff,
            # Backward compatible fields
            "technical_correctness_score": tech_acc,
            "depth_score": depth,
            "communication_score": clarity,
            "overall_score": overall_score,
            "relevant_concepts": strengths,
            "missed_concepts": missing_concepts,
            "feedback_text": feedback,
            "suggested_next_difficulty": next_diff
        }

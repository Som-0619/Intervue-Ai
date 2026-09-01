import json
import re
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

DIFFICULTY_LEVELS = ["Junior", "Intermediate", "Senior", "Principal"]

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

        # --- Rule-Based Heuristic Evaluation Engine ---
        answer_len = len(candidate_answer.strip())
        code_bonus = 1.0 if code_snippet and len(code_snippet.strip()) > 10 else 0.0

        ctx_words = set(re.findall(r'\w+', retrieved_context_text.lower())) if retrieved_context_text else set()
        ans_words = set(re.findall(r'\w+', candidate_answer.lower()))

        matched_words = list(ctx_words.intersection(ans_words))
        
        if answer_len < 40:
            tech_acc = 4.0
            depth = 3.5
            clarity = 5.0
            feedback = "The answer was brief and missed core architectural details discussed in reference materials."
            strengths = ["Basic foundational response"]
            missing_concepts = ["Detailed trade-offs", "Edge-case error handling", "Implementation specifics"]
        elif answer_len < 150:
            tech_acc = min(10.0, 6.5 + code_bonus)
            depth = 6.5
            clarity = 7.5
            feedback = f"Solid foundational explanation on {category_topic}. Touched on key concepts from reference material."
            strengths = [w.capitalize() for w in matched_words[:3]] if matched_words else ["Foundational understanding"]
            missing_concepts = ["Distributed failure resilience", "Performance profiling metrics"]
        else:
            tech_acc = min(10.0, 8.5 + code_bonus)
            depth = 8.5
            clarity = 9.0
            feedback = f"Comprehensive and well-structured answer on {category_topic}. Demonstrated clear technical mastery and practical implementation skills."
            strengths = [w.capitalize() for w in matched_words[:5]] if matched_words else ["Deep technical mastery", "Clear system breakdown"]
            missing_concepts = ["Niche optimization edge-cases"]

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

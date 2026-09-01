import { useState, useEffect } from 'react';
import { interviewApi } from '@/lib/api';
import { InterviewSessionResponse, QuestionDTO, EvaluationDTO } from '@/lib/types';

export function useInterview(interviewId: string) {
  const [session, setSession] = useState<InterviewSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEvaluation, setLastEvaluation] = useState<EvaluationDTO | null>(null);

  const fetchSession = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await interviewApi.get(interviewId);
      setSession(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to fetch interview session');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (interviewId) {
      fetchSession();
    }
  }, [interviewId]);

  const submitAnswer = async (answerText: string, codeSnippet?: string) => {
    if (!session?.current_question) return;

    try {
      setSubmitting(true);
      setError(null);
      const res = await interviewApi.submitAnswer({
        question_id: session.current_question.id,
        candidate_answer_text: answerText,
        code_snippet: codeSnippet
      });

      setLastEvaluation(res.evaluation);
      if (!res.interview_completed) {
        await fetchSession();
      }
      return res;
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit answer');
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  return {
    session,
    loading,
    submitting,
    error,
    lastEvaluation,
    refresh: fetchSession,
    submitAnswer
  };
}

import axios from 'axios';
import {
  CandidateResponse,
  InterviewSessionResponse,
  AnswerEvaluationResponse,
  InterviewReportResponse
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const candidateApi = {
  create: async (data: { name: string; target_role: string; years_of_experience: number; email?: string; resume_text?: string }): Promise<CandidateResponse> => {
    const res = await api.post('/candidates/', data);
    return res.data;
  },
  uploadResume: async (formData: FormData): Promise<CandidateResponse> => {
    const res = await api.post('/candidates/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  get: async (id: string): Promise<CandidateResponse> => {
    const res = await api.get(`/candidates/${id}`);
    return res.data;
  }
};

export const interviewApi = {
  create: async (data: { candidate_id: string; target_role: string; total_questions?: number; custom_topics?: string[] }): Promise<InterviewSessionResponse> => {
    const res = await api.post('/interviews/', data);
    return res.data;
  },
  get: async (id: string): Promise<InterviewSessionResponse> => {
    const res = await api.get(`/interviews/${id}`);
    return res.data;
  },
  submitAnswer: async (data: { question_id: string; candidate_answer_text: string; code_snippet?: string }): Promise<AnswerEvaluationResponse> => {
    const res = await api.post('/interviews/answers/submit', data);
    return res.data;
  }
};

export const reportApi = {
  get: async (interviewId: string): Promise<InterviewReportResponse> => {
    const res = await api.get(`/reports/${interviewId}`);
    return res.data;
  }
};

export default api;

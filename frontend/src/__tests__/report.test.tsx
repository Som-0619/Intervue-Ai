import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import InterviewReportPage from '../app/report/[id]/page';
import { reportApi } from '../lib/api';

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'intv_123' }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock('../lib/api', () => ({
  reportApi: {
    get: jest.fn(),
  },
}));

describe('Interview Report Page Results & Lineage Rendering', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders executive summary, category scores, recommendations, and question audit', async () => {
    (reportApi.get as jest.Mock).mockResolvedValue({
      id: 'rep_123',
      interview_id: 'intv_123',
      candidate_name: 'Samantha Vance',
      target_role: 'Backend Engineer',
      overall_score: 8.8,
      hiring_recommendation: 'Strong Hire',
      category_scores: [
        { category: 'fundamentals', score: 9.0, max_score: 10.0, questions_count: 1, status: 'evaluated' },
        { category: 'applied knowledge', score: 8.5, max_score: 10.0, questions_count: 1, status: 'evaluated' },
        { category: 'problem solving', score: 8.0, max_score: 10.0, questions_count: 1, status: 'evaluated' },
        { category: 'resume/project understanding', score: 9.2, max_score: 10.0, questions_count: 1, status: 'evaluated' }
      ],
      strengths: ['PyTorch', 'Distributed Tracing', 'FastAPI'],
      weaknesses: ['LFU Eviction'],
      missing_concepts: ['LFU Eviction'],
      recommendations: [
        "Deepen practical understanding and error handling regarding 'LFU Eviction'.",
        'Candidate demonstrates strong senior technical capability.'
      ],
      question_by_question_analysis: [
        {
          question_id: 'q_001',
          question: 'Given your background with Python, describe distributed tracing architecture.',
          candidate_answer: 'Distributed tracing uses span contexts propagated via HTTP headers to trace requests across microservices.',
          score: 9.0,
          topic: 'Advanced Distributed Tracing',
          difficulty: 'Intermediate',
          feedback: 'Comprehensive and well-structured answer.',
          relevant_knowledge_source_metadata: [
            {
              chunk_id: 'chunk_1',
              document_name: 'distributed_tracing.txt',
              title: 'Tracing Spec',
              snippet: 'Spans track execution time across distributed microservice boundaries.',
              relevance_score: 0.95
            }
          ]
        }
      ],
      summary_text: 'Samantha Vance completed a 2-question technical interview for Backend Engineer with score 8.8/10.',
      traceable_qa_history: [],
      created_at: '2026-08-31T20:00:00Z'
    });

    render(<InterviewReportPage />);

    await waitFor(() => {
      expect(screen.getByText('Samantha Vance')).toBeInTheDocument();
      expect(screen.getByText('Strong Hire')).toBeInTheDocument();
      expect(screen.getByText('8.8')).toBeInTheDocument();
    });

    // Verify recommendations rendering
    expect(screen.getByText(/Candidate demonstrates strong senior technical capability/i)).toBeInTheDocument();

    // Verify category scores breakdown
    expect(screen.getByText('fundamentals')).toBeInTheDocument();
    expect(screen.getByText('applied knowledge')).toBeInTheDocument();

    // Verify question analysis & knowledge source metadata
    expect(screen.getByText(/Given your background with Python, describe distributed tracing architecture/i)).toBeInTheDocument();
    expect(screen.getByText(/Distributed tracing uses span contexts propagated via HTTP headers/i)).toBeInTheDocument();
    expect(screen.getByText(/\[distributed_tracing.txt\] Tracing Spec/i)).toBeInTheDocument();
  });
});

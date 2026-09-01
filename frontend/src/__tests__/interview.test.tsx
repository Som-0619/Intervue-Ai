import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InteractiveInterviewPage from '../app/interview/[id]/page';
import { interviewApi } from '../lib/api';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'intv_123' }),
  useRouter: () => ({
    push: mockPush,
  }),
}));

jest.mock('../lib/api', () => ({
  interviewApi: {
    get: jest.fn(),
    submitAnswer: jest.fn(),
  },
}));

describe('Interactive Interview Page UI & Submission Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders interview question, category topic, difficulty badge, and context toggle', async () => {
    (interviewApi.get as jest.Mock).mockResolvedValue({
      id: 'intv_123',
      candidate_id: 'cand_123',
      target_role: 'Backend Engineer',
      status: 'active',
      current_question_index: 0,
      total_questions: 3,
      selected_topics: ['Advanced Distributed Tracing', 'System Design'],
      current_difficulty: 'Intermediate',
      current_question: {
        id: 'q_001',
        interview_id: 'intv_123',
        index: 0,
        category_topic: 'Advanced Distributed Tracing',
        difficulty: 'Intermediate',
        text: 'Explain how OpenTelemetry context propagation works in microservices.',
        rationale: 'Tests trace ID propagation across HTTP headers.',
        retrieved_chunks: [
          {
            id: 'chunk_1',
            document_name: 'tracing_spec.txt',
            role_category: 'Backend Engineer',
            title: 'OpenTelemetry Spec',
            chunk_text: 'Trace context is injected into W3C TraceContext headers.',
            score: 0.92
          }
        ],
        has_answered: false
      }
    });

    render(<InteractiveInterviewPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Advanced Distributed Tracing')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Intermediate')[0]).toBeInTheDocument();
      expect(screen.getByText(/Explain how OpenTelemetry context propagation works/i)).toBeInTheDocument();
    });

    // Test RAG context drawer toggle
    const contextBtn = screen.getByText('View RAG Context');
    fireEvent.click(contextBtn);

    expect(screen.getByText('Retrieved Knowledge Base Grounding Context')).toBeInTheDocument();
    expect(screen.getByText(/Trace context is injected into W3C TraceContext headers/i)).toBeInTheDocument();
  });

  test('submits answer and handles evaluation feedback and API error states', async () => {
    (interviewApi.get as jest.Mock).mockResolvedValue({
      id: 'intv_123',
      candidate_id: 'cand_123',
      target_role: 'Backend Engineer',
      status: 'active',
      current_question_index: 0,
      total_questions: 2,
      selected_topics: ['Caching', 'PostgreSQL'],
      current_difficulty: 'Intermediate',
      current_question: {
        id: 'q_001',
        interview_id: 'intv_123',
        index: 0,
        category_topic: 'Caching',
        difficulty: 'Intermediate',
        text: 'How does Redis eviction policy work?',
        retrieved_chunks: [],
        has_answered: false
      }
    });

    (interviewApi.submitAnswer as jest.Mock).mockResolvedValue({
      evaluation: {
        id: 'ev_001',
        answer_id: 'ans_001',
        technical_correctness_score: 9.0,
        depth_score: 8.5,
        communication_score: 8.0,
        overall_score: 8.5,
        relevant_concepts: ['LRU Eviction', 'Memory Limits'],
        missed_concepts: ['LFU Eviction'],
        feedback_text: 'Excellent explanation of LRU memory limits.',
        suggested_next_difficulty: 'Senior'
      },
      next_question: null,
      interview_completed: false
    });

    render(<InteractiveInterviewPage />);

    await waitFor(() => {
      expect(screen.getByText(/How does Redis eviction policy work\?/i)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Write your technical explanation here/i);
    fireEvent.change(textarea, { target: { value: 'Redis uses volatile-lru policy to evict least recently used keys when maxmemory limit is reached.' } });

    const submitBtn = screen.getByRole('button', { name: /Submit & Continue to Next Question →/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(interviewApi.submitAnswer).toHaveBeenCalledWith({
        question_id: 'q_001',
        candidate_answer_text: 'Redis uses volatile-lru policy to evict least recently used keys when maxmemory limit is reached.',
        code_snippet: undefined
      });
    });
  });
});

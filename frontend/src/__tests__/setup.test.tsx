import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InterviewSetupPage from '../app/setup/page';
import { candidateApi, interviewApi } from '../lib/api';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock API client
jest.mock('../lib/api', () => ({
  candidateApi: {
    create: jest.fn(),
    uploadResume: jest.fn(),
  },
  interviewApi: {
    create: jest.fn(),
  },
}));

describe('Interview Setup Page UI Components & State', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders setup form with candidate name, role selection, and resume inputs', () => {
    render(<InterviewSetupPage />);

    expect(screen.getByText('Candidate Setup & Resume Ingestion')).toBeInTheDocument();
    expect(screen.getByLabelText(/Candidate Full Name/i)).toBeInTheDocument();
    expect(screen.getByText('Select Target Job Role')).toBeInTheDocument();

    // Verify role selection options
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument();
    expect(screen.getByText('AI/ML Engineer')).toBeInTheDocument();
    expect(screen.getByText('Frontend Engineer')).toBeInTheDocument();
    expect(screen.getByText('Fullstack Engineer')).toBeInTheDocument();

    // Verify upload and text area labels
    expect(screen.getByText(/Upload Resume/i)).toBeInTheDocument();
    expect(screen.getByText(/Or Paste Raw Resume Text/i)).toBeInTheDocument();
  });

  test('handles candidate name input and role selection', () => {
    render(<InterviewSetupPage />);

    const nameInput = screen.getByLabelText(/Candidate Full Name/i);
    fireEvent.change(nameInput, { target: { value: 'Alex Morgan' } });
    expect(nameInput).toHaveValue('Alex Morgan');

    // Select Backend Engineer role
    const backendRoleBtn = screen.getByText('Backend Engineer');
    fireEvent.click(backendRoleBtn);
  });

  test('handles candidate creation and submission flow', async () => {
    (candidateApi.create as jest.Mock).mockResolvedValue({
      id: 'cand_test_123',
      name: 'Alex Morgan',
      target_role: 'Backend Engineer',
      years_of_experience: 3.5,
      parsed_profile: {
        skills: ['Python', 'FastAPI', 'PostgreSQL'],
        skill_gaps: ['Distributed Tracing']
      }
    });

    render(<InterviewSetupPage />);

    const nameInput = screen.getByLabelText(/Candidate Full Name/i);
    fireEvent.change(nameInput, { target: { value: 'Alex Morgan' } });

    const submitBtn = screen.getByRole('button', { name: /Analyze Resume & Extract Profile/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(candidateApi.create).toHaveBeenCalledWith({
        name: 'Alex Morgan',
        target_role: 'AI/ML Engineer',
        years_of_experience: 3.5,
        email: 'alex.rivera@example.com',
        resume_text: expect.any(String)
      });
    });
  });
});

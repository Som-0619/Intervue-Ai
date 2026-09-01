export interface CandidateProfile {
  name: string;
  email?: string;
  target_role: string;
  years_of_experience: number;
  skills: string[];
  domains: string[];
  strengths: string[];
  skill_gaps: string[];
}

export interface CandidateResponse {
  id: string;
  name: string;
  email?: string;
  target_role: string;
  years_of_experience: number;
  parsed_profile?: CandidateProfile;
  created_at: string;
}

export interface KnowledgeChunkDTO {
  id: string;
  document_name: string;
  role_category: string;
  title: string;
  chunk_text: string;
  score?: number;
  metadata?: Record<string, any>;
}

export interface QuestionDTO {
  id: string;
  interview_id: string;
  index: number;
  category_topic: string;
  difficulty: string;
  text: string;
  rationale?: string;
  retrieved_chunks: KnowledgeChunkDTO[];
  retrieved_context_text?: string;
  has_answered: boolean;
}

export interface InterviewSessionResponse {
  id: string;
  candidate_id: string;
  target_role: string;
  status: string;
  current_question_index: number;
  total_questions: number;
  selected_topics: string[];
  current_difficulty: string;
  current_question?: QuestionDTO;
}

export interface EvaluationDTO {
  id: string;
  answer_id: string;
  technical_correctness_score: number;
  depth_score: number;
  communication_score: number;
  overall_score: number;
  relevant_concepts: string[];
  missed_concepts: string[];
  feedback_text: string;
  suggested_next_difficulty: string;
}

export interface AnswerEvaluationResponse {
  evaluation: EvaluationDTO;
  next_question?: QuestionDTO;
  interview_completed: boolean;
}

export interface CategoryScoreDTO {
  category: string;
  score: number;
  max_score: number;
  questions_count: number;
  status?: string;
}

export interface KnowledgeSourceMetadataDTO {
  chunk_id: string;
  document_name: string;
  title: string;
  page?: number;
  section?: string;
  relevance_score?: number;
  snippet: string;
}

export interface QuestionAnalysisDTO {
  question_id: string;
  question: string;
  candidate_answer: string;
  score: number;
  topic: string;
  difficulty: string;
  feedback: string;
  relevant_knowledge_source_metadata: KnowledgeSourceMetadataDTO[];
  evaluation?: EvaluationDTO;
  code_snippet?: string;
}

export interface TraceableQADTO {
  question: QuestionDTO;
  answer_text: string;
  code_snippet?: string;
  evaluation: EvaluationDTO;
}

export interface InterviewReportResponse {
  id: string;
  interview_id: string;
  candidate_name: string;
  target_role: string;
  overall_score: number;
  hiring_recommendation: string;
  category_scores: CategoryScoreDTO[];
  strengths: string[];
  weaknesses: string[];
  missing_concepts?: string[];
  recommendations?: string[];
  question_by_question_analysis?: QuestionAnalysisDTO[];
  summary_text: string;
  traceable_qa_history: TraceableQADTO[];
  created_at: string;
}

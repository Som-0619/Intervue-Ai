'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { interviewApi } from '@/lib/api';
import { InterviewSessionResponse, QuestionDTO, EvaluationDTO } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Bot, Code, Database, CheckCircle2, AlertCircle, ArrowRight,
  Send, Loader2, ShieldCheck, Mic, MicOff, Video, VideoOff,
  Sparkles, Terminal, Volume2, Cpu, Wrench, HelpCircle
} from 'lucide-react';

const TECHNICAL_KEYWORDS = [
  'Python', 'FastAPI', 'PostgreSQL', 'Redis', 'Docker', 'Kubernetes',
  'RAG', 'Vector', 'PyTorch', 'TensorFlow', 'Concurrency', 'Asyncio',
  'Indexing', 'B-Tree', 'SSTable', 'Memtable', 'MVCC', 'Sharding',
  'Latency', 'Throughput', 'Microservices', 'REST', 'GraphQL', 'gRPC'
];

export default function InteractiveInterviewPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.id as string;

  const [session, setSession] = useState<InterviewSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Form & Media Panel State
  const [answerText, setAnswerText] = useState('');
  const [codeSnippet, setCodeSnippet] = useState('');
  const [showCodeInput, setShowCodeInput] = useState(false);
  const [showTraceability, setShowTraceability] = useState(false);
  const [lastEval, setLastEval] = useState<EvaluationDTO | null>(null);

  // Live Audio/Video Controls & Streams
  const [isMicOn, setIsMicOn] = useState(true);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    let localStream: MediaStream | null = null;
    async function initMedia() {
      try {
        if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
          localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
          setStream(localStream);
          if (videoRef.current) {
            videoRef.current.srcObject = localStream;
          }
        }
      } catch (err) {
        console.warn('Camera/Mic initialization:', err);
      }
    }
    initMedia();
    return () => {
      if (localStream) {
        localStream.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const toggleMic = () => {
    const nextState = !isMicOn;
    setIsMicOn(nextState);
    if (stream) {
      stream.getAudioTracks().forEach(t => { t.enabled = nextState; });
    }
  };

  const toggleVideo = () => {
    const nextState = !isVideoOn;
    setIsVideoOn(nextState);
    if (stream) {
      stream.getVideoTracks().forEach(t => { t.enabled = nextState; });
    }
  };

  useEffect(() => {
    if (interviewId) {
      fetchSession();
    }
  }, [interviewId]);

  const fetchSession = async () => {
    try {
      setLoading(true);
      const data = await interviewApi.get(interviewId);
      setSession(data);
      if (data.status === 'completed') {
        router.push(`/report/${interviewId}`);
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || 'Failed to load interview session.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.current_question || !answerText.trim() || submitting) return;

    setSubmitting(true);
    setErrorMsg('');

    try {
      const res = await interviewApi.submitAnswer({
        question_id: session.current_question.id,
        candidate_answer_text: answerText,
        code_snippet: codeSnippet.trim() ? codeSnippet : undefined
      });

      setLastEval(res.evaluation);
      setAnswerText('');
      setCodeSnippet('');
      setShowCodeInput(false);

      if (res.interview_completed) {
        setTimeout(() => {
          router.push(`/report/${interviewId}`);
        }, 1200);
      } else if (res.next_question) {
        setSession(prev => prev ? {
          ...prev,
          current_question_index: prev.current_question_index + 1,
          current_difficulty: res.evaluation?.suggested_next_difficulty || prev.current_difficulty,
          current_question: res.next_question
        } : prev);
      } else {
        fetchSession();
      }
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || 'Failed to submit answer.');
    } finally {
      setSubmitting(false);
    }
  };


  const insertCodeTemplate = (type: 'python' | 'ts' | 'sql') => {
    setShowCodeInput(true);
    if (type === 'python') {
      setCodeSnippet(`def solve_problem(data: list) -> dict:\n    """Optimal Python implementation with exception handling."""\n    try:\n        processed = [x * 2 for x in data if x is not None]\n        return {"status": "success", "data": processed}\n    except Exception as e:\n        return {"status": "error", "message": str(e)}`);
    } else if (type === 'ts') {
      setCodeSnippet(`interface DataPayload {\n  id: string;\n  values: number[];\n}\n\nasync function processPayload(payload: DataPayload): Promise<void> {\n  console.log('Processing:', payload.id);\n}`);
    } else if (type === 'sql') {
      setCodeSnippet(`SELECT category, COUNT(*) AS total_count, AVG(score) AS avg_score\nFROM interview_evaluations\nWHERE status = 'active'\nGROUP BY category\nHAVING AVG(score) >= 8.0;\nCREATE INDEX idx_eval_cat ON interview_evaluations(category);`);
    }
  };

  const detectedKeywords = TECHNICAL_KEYWORDS.filter(kw =>
    answerText.toLowerCase().includes(kw.toLowerCase())
  );
  const wordCount = answerText.trim() ? answerText.trim().split(/\s+/).length : 0;

  if (loading && !session) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 py-6">
        <Skeleton className="h-20 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Skeleton className="lg:col-span-8 h-96" />
          <Skeleton className="lg:col-span-4 h-96" />
        </div>
      </div>
    );
  }

  const currentQ = session?.current_question;
  const currentIndex = session?.current_question_index || 0;
  const totalQ = session?.total_questions || 5;
  const questionsRemaining = totalQ - (currentIndex + 1);
  const isFinalQuestion = questionsRemaining === 0;
  const progressPercent = Math.round(((currentIndex + 1) / totalQ) * 100);

  const roadmapTopics = session?.selected_topics || ['Fundamentals', 'Python', 'RAG', 'System Design', 'Evaluation'];

  return (
    <div className="max-w-6xl mx-auto space-y-6 py-4">
      {/* Top Candidate Orientation Header Bar */}
      <Card className="p-4 bg-white border-zinc-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-zinc-900 text-white flex items-center justify-center font-mono font-bold text-xs shadow-sm">
              Q{currentIndex + 1}
            </div>
            <div>
              <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 uppercase tracking-wider">
                <span>{session?.target_role}</span>
                <span>•</span>
                <span>{session?.current_difficulty} Level</span>
              </div>
              <h1 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
                <span>Question {currentIndex + 1} of {totalQ}</span>
                <span className="text-xs font-normal text-zinc-400 font-mono">
                  ({questionsRemaining === 0 ? 'Final Question' : `${questionsRemaining} remaining`})
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-4 w-full sm:w-auto">
            {/* Live Media Toggles */}
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-100 border border-zinc-200">
              <button
                type="button"
                onClick={toggleMic}
                className={`p-1.5 rounded-lg text-xs transition-colors ${isMicOn ? 'bg-emerald-500 text-white' : 'bg-zinc-200 text-zinc-500'}`}
                title={isMicOn ? 'Microphone Active' : 'Microphone Muted'}
              >
                {isMicOn ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
              </button>
              <button
                type="button"
                onClick={toggleVideo}
                className={`p-1.5 rounded-lg text-xs transition-colors ${isVideoOn ? 'bg-zinc-900 text-white' : 'bg-zinc-200 text-zinc-500'}`}
                title={isVideoOn ? 'Camera Active' : 'Camera Off'}
              >
                {isVideoOn ? <Video className="w-3.5 h-3.5" /> : <VideoOff className="w-3.5 h-3.5" />}
              </button>
            </div>

            <div className="w-48 space-y-1">
              <div className="flex justify-between text-[11px] font-mono text-zinc-500">
                <span>Session Progress</span>
                <span>{progressPercent}%</span>
              </div>
              <Progress value={progressPercent} />
            </div>
          </div>
        </div>
      </Card>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Previous Answer Feedback Banner */}
      {lastEval && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-900">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Previous Answer Evaluated — Score: {lastEval.overall_score}/10</span>
            </div>
            <Badge variant="success">Adapted Level: {lastEval.suggested_next_difficulty}</Badge>
          </div>
          <p className="text-xs text-emerald-700 font-sans">{lastEval.feedback_text}</p>
        </div>
      )}

      {/* Main Grid */}
      {currentQ && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left QA Area */}
          <div className="lg:col-span-8 space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-zinc-400 font-mono uppercase">Topic:</span>
                    <Badge variant="secondary">{currentQ.category_topic}</Badge>
                    <Badge variant="outline">{currentQ.difficulty}</Badge>
                  </div>

                  <button
                    onClick={() => setShowTraceability(!showTraceability)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-xs font-mono transition-colors"
                  >
                    <Database className="w-3.5 h-3.5" />
                    <span>{showTraceability ? 'Hide RAG Context' : 'View RAG Context'}</span>
                  </button>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <h2 className="text-base font-semibold text-zinc-900 leading-relaxed">
                  {currentQ.text}
                </h2>

                {currentQ.rationale && (
                  <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-600">
                    <span className="font-semibold text-zinc-900">Evaluation Focus: </span>
                    {currentQ.rationale}
                  </div>
                )}

                {/* RAG Context Drawer */}
                {showTraceability && (
                  <div className="p-4 rounded-xl bg-zinc-900 text-white space-y-3 font-mono text-xs">
                    <div className="flex items-center gap-2 text-zinc-300 font-semibold uppercase tracking-wider">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Retrieved Knowledge Base Grounding Context
                    </div>

                    <div className="space-y-2">
                      {currentQ.retrieved_chunks.map((chunk) => (
                        <div key={chunk.id} className="p-3 rounded-lg bg-zinc-800 border border-zinc-700 space-y-1">
                          <div className="flex justify-between text-[11px] text-zinc-400">
                            <span>[{chunk.document_name}]</span>
                            <span className="text-emerald-400">Score: {chunk.score}</span>
                          </div>
                          <p className="text-zinc-200 text-[11px] leading-relaxed font-sans">{chunk.chunk_text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Candidate Answer Form */}
            <form onSubmit={handleSubmitAnswer}>
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm">Your Technical Answer</CardTitle>
                      <CardDescription className="text-xs">
                        Provide a thorough explanation covering trade-offs, architecture, and edge-case handling.
                      </CardDescription>
                    </div>
                    {isMicOn && (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-mono">
                        <Volume2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Voice Input Active</span>
                      </div>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <textarea
                    rows={6}
                    required
                    disabled={submitting}
                    value={answerText}
                    onChange={(e) => setAnswerText(e.target.value)}
                    placeholder="Write your technical explanation here..."
                    className="w-full p-3.5 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-sm focus-ring leading-relaxed resize-y font-sans"
                  />

                  {/* Real-Time Keyword Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl bg-zinc-50 border border-zinc-200 text-xs font-mono">
                    <div className="flex items-center gap-3 text-zinc-500">
                      <span>Words: <strong className="text-zinc-900">{wordCount}</strong></span>
                      <span>Detected Concepts: <strong className="text-emerald-700">{detectedKeywords.length}</strong></span>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {detectedKeywords.slice(0, 4).map(kw => (
                        <Badge key={kw} variant="success" className="text-[10px]">{kw}</Badge>
                      ))}
                    </div>
                  </div>

                  {/* Code Toolbar */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs text-zinc-600 font-medium">
                      <div className="flex items-center gap-2">
                        <Code className="w-4 h-4 text-zinc-700" />
                        <span>Code Implementation Snippet (Optional)</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => insertCodeTemplate('python')}
                          className="px-2 py-0.5 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-[11px] font-mono"
                        >
                          + Python
                        </button>
                        <button
                          type="button"
                          onClick={() => insertCodeTemplate('ts')}
                          className="px-2 py-0.5 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-[11px] font-mono"
                        >
                          + TypeScript
                        </button>
                        <button
                          type="button"
                          onClick={() => insertCodeTemplate('sql')}
                          className="px-2 py-0.5 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-[11px] font-mono"
                        >
                          + SQL
                        </button>
                      </div>
                    </div>

                    {showCodeInput && (
                      <textarea
                        rows={5}
                        value={codeSnippet}
                        onChange={(e) => setCodeSnippet(e.target.value)}
                        placeholder="// Paste implementation code snippet..."
                        className="w-full p-3 rounded-xl bg-zinc-900 text-zinc-100 text-xs font-mono focus-ring"
                      />
                    )}
                  </div>
                </CardContent>

                <CardFooter className="flex justify-between items-center bg-zinc-50 border-t border-zinc-200 p-4">
                  <div className="text-xs text-zinc-500 font-mono">
                    Next: {isFinalQuestion ? 'Final Evaluation & Report Synthesis' : `Question ${currentIndex + 2} of ${totalQ}`}
                  </div>

                  <Button type="submit" disabled={submitting || !answerText.trim()}>
                    {submitting ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Send className="w-4 h-4 mr-2" />
                    )}
                    <span>{isFinalQuestion ? 'Submit & Generate Final Report' : 'Submit & Continue to Next Question →'}</span>
                  </Button>
                </CardFooter>
              </Card>
            </form>
          </div>

          {/* Right Column: Video Preview & Roadmap */}
          <div className="lg:col-span-4 space-y-6">
            {isVideoOn && (
              <Card className="p-4 bg-zinc-900 text-white space-y-2 overflow-hidden">
                <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Live Candidate Feed</span>
                  </div>
                  <Badge variant="outline" className="border-zinc-700 text-zinc-400 text-[10px]">720p HD</Badge>
                </div>
                <div className="relative h-36 rounded-lg bg-zinc-950 border border-zinc-800 overflow-hidden flex items-center justify-center">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {!stream && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-500 space-y-1">
                      <Cpu className="w-6 h-6 text-zinc-600" />
                      <span className="text-[11px] font-mono">Candidate Video Feed Streaming</span>
                    </div>
                  )}
                </div>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Interview Topic Roadmap</CardTitle>
                <CardDescription className="text-xs">Structured evaluation sequence</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 font-mono text-xs">
                {roadmapTopics.map((topic, idx) => {
                  let statusSymbol = '○';
                  let statusClass = 'text-zinc-400';
                  let itemBg = 'bg-white text-zinc-500 border-zinc-200';

                  if (idx < currentIndex) {
                    statusSymbol = '✓';
                    statusClass = 'text-emerald-600 font-bold';
                    itemBg = 'bg-emerald-50/50 border-emerald-200 text-zinc-800';
                  } else if (idx === currentIndex) {
                    statusSymbol = '●';
                    statusClass = 'text-zinc-900 font-bold';
                    itemBg = 'bg-zinc-100 border-zinc-300 text-zinc-900 font-semibold shadow-sm';
                  }

                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border flex items-center justify-between ${itemBg}`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className={statusClass}>{statusSymbol}</span>
                        <span>{topic}</span>
                      </div>
                      {idx === currentIndex && (
                        <Badge variant="default" className="text-[10px]">Active</Badge>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

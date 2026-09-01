'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { reportApi } from '@/lib/api';
import { InterviewReportResponse } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Award, CheckCircle2, ChevronDown, ChevronUp, Code, Database,
  AlertTriangle, ShieldCheck, TrendingUp, ArrowLeft, Printer,
  Sparkles, FileText, Check
} from 'lucide-react';
import Link from 'next/link';

export default function InterviewReportPage() {
  const params = useParams();
  const interviewId = params?.id as string;

  const [report, setReport] = useState<InterviewReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [expandedQ, setExpandedQ] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (interviewId) {
      fetchReport();
    }
  }, [interviewId]);

  const fetchReport = async () => {
    try {
      setLoading(true);
      const data = await reportApi.get(interviewId);
      setReport(data);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || 'Failed to load interview report.');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (qId: string) => {
    setExpandedQ(prev => ({ ...prev, [qId]: !prev[qId] }));
  };

  const handlePrint = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6 py-6">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (errorMsg || !report) {
    return (
      <Card className="max-w-xl mx-auto p-8 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <CardTitle>Report Generation Error</CardTitle>
        <CardDescription>{errorMsg || 'Unable to retrieve interview results.'}</CardDescription>
        <Link href="/setup">
          <Button variant="outline">Back to Setup</Button>
        </Link>
      </Card>
    );
  }

  const getRecommendationBadgeVariant = (rec: string) => {
    switch (rec) {
      case 'Strong Hire':
        return 'success';
      case 'Hire':
        return 'secondary';
      case 'Weak Hire':
        return 'warning';
      default:
        return 'outline';
    }
  };

  const qaAnalysisList = report.question_by_question_analysis || [];

  return (
    <div className="max-w-5xl mx-auto space-y-8 py-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard" className="inline-flex items-center text-xs text-zinc-500 hover:text-zinc-900 font-mono">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Dashboard</span>
        </Link>

        <Button variant="outline" size="sm" onClick={handlePrint}>
          <Printer className="w-3.5 h-3.5 mr-1.5" />
          <span>Print / Export PDF</span>
        </Button>
      </div>

      {/* Executive Summary Card */}
      <Card className="p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="space-y-1">
            <Badge variant="outline">{report.target_role}</Badge>
            <h1 className="text-2xl font-bold text-zinc-900">{report.candidate_name}</h1>
            <p className="text-xs text-zinc-500 font-mono">Session ID: {report.interview_id}</p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-xs text-zinc-500 font-mono uppercase">Overall Performance</div>
              <div className="text-3xl font-extrabold text-zinc-900 font-mono">
                {report.overall_score}
                <span className="text-xs text-zinc-400 font-normal"> / 10.0</span>
              </div>
            </div>

            <Badge variant={getRecommendationBadgeVariant(report.hiring_recommendation)} className="px-4 py-2 text-xs uppercase tracking-wider">
              {report.hiring_recommendation}
            </Badge>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 text-xs text-zinc-700 leading-relaxed">
          <span className="font-semibold text-zinc-900">Executive Synthesis: </span>
          {report.summary_text}
        </div>
      </Card>

      {/* Category Scores & Competency Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-zinc-700" />
              <span>Competency Breakdown</span>
            </CardTitle>
            <CardDescription className="text-xs">Evaluated across core technical dimensions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {report.category_scores.map((cat) => (
              <div key={cat.category} className="space-y-1.5">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-700 capitalize">{cat.category}</span>
                  <span className="font-mono text-zinc-900 font-semibold">{cat.score} / 10.0</span>
                </div>
                <Progress value={(cat.score / 10) * 100} />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Strengths & Missing Concepts */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Verified Competencies & Growth Focus</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Verified Technical Strengths</h4>
              <div className="flex flex-wrap gap-1.5">
                {report.strengths.map((str) => (
                  <Badge key={str} variant="success">{str}</Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Missing Concepts / Skill Gaps</h4>
              <div className="flex flex-wrap gap-1.5">
                {(report.missing_concepts || report.weaknesses).map((concept) => (
                  <Badge key={concept} variant="warning">{concept}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actionable Recommendations Card */}
      {report.recommendations && report.recommendations.length > 0 && (
        <Card className="p-6 space-y-3 bg-zinc-50 border-zinc-200">
          <div className="flex items-center gap-2 text-xs font-semibold text-zinc-900 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-emerald-600" />
            <span>Actionable Hiring & Development Recommendations</span>
          </div>
          <ul className="space-y-2 text-xs text-zinc-700 font-sans">
            {report.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Question-by-Question Audit & Traceability */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-zinc-700" />
            Traceable Question Audit & RAG Context Lineage
          </h2>
          <span className="text-xs font-mono text-zinc-500">
            {qaAnalysisList.length > 0 ? qaAnalysisList.length : report.traceable_qa_history.length} Questions Analyzed
          </span>
        </div>

        <div className="space-y-4">
          {(qaAnalysisList.length > 0 ? qaAnalysisList : report.traceable_qa_history).map((item: any, idx: number) => {
            const qId = item.question_id || item.question?.id;
            const qText = item.question?.text || item.question;
            const qTopic = item.topic || item.question?.category_topic;
            const qDiff = item.difficulty || item.question?.difficulty;
            const scoreVal = item.score !== undefined ? item.score : item.evaluation?.overall_score;
            const ansText = item.candidate_answer || item.answer_text;
            const feedbackText = item.feedback || item.evaluation?.feedback_text;
            const sources = item.relevant_knowledge_source_metadata || [];

            const isExpanded = expandedQ[qId] ?? true;

            return (
              <Card key={qId || idx} className="overflow-hidden">
                <div
                  onClick={() => toggleExpand(qId)}
                  className="p-4 flex items-center justify-between bg-zinc-50 hover:bg-zinc-100 transition-colors cursor-pointer border-b border-zinc-200"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className="font-bold text-zinc-900">Q{idx + 1}</span>
                      <Badge variant="secondary">{qTopic}</Badge>
                      <Badge variant="outline">{qDiff}</Badge>
                    </div>
                    <div className="text-xs font-medium text-zinc-900">{qText}</div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right font-mono">
                      <span className="text-xs text-zinc-500 block">Score</span>
                      <span className="text-xs font-bold text-emerald-700">{scoreVal} / 10</span>
                    </div>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
                  </div>
                </div>

                {isExpanded && (
                  <CardContent className="p-6 space-y-4 text-xs">
                    {/* Knowledge Context Lineage */}
                    {sources.length > 0 && (
                      <div className="p-3.5 rounded-xl bg-zinc-900 text-white space-y-2 font-mono">
                        <div className="flex items-center gap-1.5 text-zinc-300 font-semibold text-[11px]">
                          <Database className="w-3.5 h-3.5 text-emerald-400" />
                          Knowledge Context Lineage ({sources.length} Documents)
                        </div>
                        {sources.map((src: any, sIdx: number) => (
                          <div key={sIdx} className="p-2.5 rounded bg-zinc-800 border border-zinc-700 text-[11px] space-y-1">
                            <div className="flex justify-between text-zinc-400">
                              <span>[{src.document_name}] {src.title}</span>
                              <span className="text-emerald-400">Score: {src.relevance_score}</span>
                            </div>
                            <p className="text-zinc-200 font-sans">{src.snippet}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Candidate Answer */}
                    <div className="space-y-1.5">
                      <span className="font-semibold text-zinc-800 uppercase tracking-wider">Candidate Answer</span>
                      <p className="p-3 rounded-xl bg-zinc-50 border border-zinc-200 text-zinc-800 leading-relaxed font-sans">
                        {ansText}
                      </p>
                      {item.code_snippet && (
                        <pre className="p-3 rounded-xl bg-zinc-900 text-zinc-100 font-mono text-[11px] overflow-x-auto">
                          {item.code_snippet}
                        </pre>
                      )}
                    </div>

                    {/* Feedback */}
                    <div className="p-3.5 rounded-xl bg-zinc-50 border border-zinc-200 space-y-1">
                      <span className="font-semibold text-zinc-900">Evaluator Feedback:</span>
                      <p className="text-zinc-700 leading-relaxed font-sans">{feedbackText}</p>
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  BarChart3, Users, CheckCircle2, ShieldCheck, Sparkles,
  ArrowRight, Award, FileText, Database, Activity, RefreshCw
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { candidateApi, reportApi } from '@/lib/api';

export default function DashboardPage() {
  const [stats, setStats] = useState({
    totalCandidates: 12,
    avgScore: 8.4,
    ragChunksCount: 13,
    strongHireRate: '75%'
  });

  const recentSessions = [
    { id: 'intv_demo_01', candidateName: 'Samantha Vance', role: 'Backend Engineer', score: 8.8, rec: 'Strong Hire', status: 'completed', date: 'Just now' },
    { id: 'intv_demo_02', candidateName: 'Jordan Smith', role: 'AI/ML Engineer', score: 8.2, rec: 'Hire', status: 'completed', date: '2 hours ago' },
    { id: 'intv_demo_03', candidateName: 'Alex Morgan', role: 'Frontend Engineer', score: 7.6, rec: 'Hire', status: 'in_progress', date: 'Today' },
  ];

  const categoryBreakdown = [
    { name: 'Fundamentals', score: 8.8, color: 'bg-emerald-500' },
    { name: 'Applied Knowledge', score: 8.5, color: 'bg-blue-500' },
    { name: 'Problem Solving', score: 8.2, color: 'bg-indigo-500' },
    { name: 'Resume & Project Fit', score: 8.9, color: 'bg-violet-500' },
  ];

  return (
    <div className="space-y-8 py-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5 text-emerald-600" />
            <span>Platform Overview</span>
          </div>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">Interview Analytics Dashboard</h1>
        </div>

        <Link href="/setup">
          <Button className="shadow-sm">
            <Sparkles className="w-4 h-4 mr-2" />
            <span>New Interview Setup</span>
          </Button>
        </Link>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="neutral-card-interactive">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs font-mono text-zinc-500 uppercase">Evaluating Candidates</span>
              <div className="text-2xl font-bold text-zinc-900 font-mono">{stats.totalCandidates}</div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-700">
              <Users className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="neutral-card-interactive">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs font-mono text-zinc-500 uppercase">Average Score</span>
              <div className="text-2xl font-bold text-emerald-700 font-mono">{stats.avgScore} <span className="text-xs text-zinc-400 font-normal">/ 10</span></div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
              <Award className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="neutral-card-interactive">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs font-mono text-zinc-500 uppercase">RAG Vector Chunks</span>
              <div className="text-2xl font-bold text-zinc-900 font-mono">{stats.ragChunksCount}</div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-700">
              <Database className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="neutral-card-interactive">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs font-mono text-zinc-500 uppercase">Recommendation Rate</span>
              <div className="text-2xl font-bold text-zinc-900 font-mono">{stats.strongHireRate}</div>
            </div>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-700">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid: Core Category Breakdown & Recent Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Category Breakdown */}
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-zinc-700" />
              <span>Core Assessment Dimensions</span>
            </CardTitle>
            <CardDescription className="text-xs">Aggregated candidate performance metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {categoryBreakdown.map((cat) => (
              <div key={cat.name} className="space-y-1.5">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-700">{cat.name}</span>
                  <span className="font-mono text-zinc-900 font-semibold">{cat.score} / 10.0</span>
                </div>
                <Progress value={(cat.score / 10) * 100} />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Interviews List */}
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-zinc-700" />
                <span>Recent Interview Sessions</span>
              </div>
              <Badge variant="outline">Live Engine</Badge>
            </CardTitle>
            <CardDescription className="text-xs">Latest evaluated interview sessions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 font-mono text-xs">
            {recentSessions.map((session) => (
              <div
                key={session.id}
                className="p-3.5 rounded-xl border border-zinc-200 hover:border-zinc-300 bg-white flex items-center justify-between transition-colors"
              >
                <div className="space-y-0.5">
                  <div className="font-bold text-zinc-900 font-sans">{session.candidateName}</div>
                  <div className="text-[11px] text-zinc-500">
                    {session.role} • {session.date}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="font-bold text-emerald-700 text-xs">{session.score} / 10</div>
                    <Badge variant={session.rec === 'Strong Hire' ? 'success' : 'secondary'} className="text-[10px]">
                      {session.rec}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* RAG Integrity Banner */}
      <Card className="p-6 bg-zinc-900 text-white space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>RAG Grounding Integrity System Active</span>
          </div>
          <Badge variant="success">Zero Hallucinations</Badge>
        </div>
        <p className="text-xs text-zinc-300 leading-relaxed font-sans max-w-3xl">
          IntervueAI dynamically pulls technical context from ingested knowledge base documents to generate non-generic, grounded questions and evaluates candidate answers strictly against reference specs.
        </p>
      </Card>
    </div>
  );
}

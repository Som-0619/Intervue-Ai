import Link from 'next/link';
import { ArrowRight, FileText, Briefcase, Database, Sparkles, ShieldCheck, Check } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';

export default function LandingPage() {
  return (
    <div className="space-y-16 py-8">
      {/* Hero Section */}
      <section className="text-center space-y-6 max-w-3xl mx-auto pt-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-100 border border-zinc-200 text-zinc-700 text-xs font-mono font-medium">
          <Sparkles className="w-3.5 h-3.5 text-zinc-900" />
          <span>Role-Based Technical Evaluation Engine</span>
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-zinc-900 leading-tight">
          Your next technical interview starts here.
        </h1>

        <p className="text-base sm:text-lg text-zinc-600 max-w-2xl mx-auto leading-relaxed">
          IntervueAI deeply understands your <span className="font-semibold text-zinc-900">resume background</span>, aligns with your <span className="font-semibold text-zinc-900">target job role</span>, and evaluates your <span className="font-semibold text-zinc-900">technical knowledge</span> through context-grounded RAG questions.
        </p>

        <div className="flex items-center justify-center pt-2">
          <Link href="/setup">
            <Button size="lg" className="px-8 shadow-sm">
              <span>Start Interview</span>
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Understanding Pillars */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <Card className="neutral-card-interactive">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2 border border-zinc-200">
              <FileText className="w-5 h-5" />
            </div>
            <CardTitle className="text-base">Resume Intelligence</CardTitle>
            <CardDescription className="text-xs text-zinc-500 leading-relaxed">
              Extracts tech stacks, years of experience, core strengths, and specific skill gaps from candidate resumes.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="neutral-card-interactive">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2 border border-zinc-200">
              <Briefcase className="w-5 h-5" />
            </div>
            <CardTitle className="text-base">Target Role Alignment</CardTitle>
            <CardDescription className="text-xs text-zinc-500 leading-relaxed">
              Tailors interview depth and topic selection specifically for AI/ML, Backend, Frontend, Fullstack, or SRE engineering roles.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="neutral-card-interactive">
          <CardHeader>
            <div className="w-10 h-10 rounded-xl bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2 border border-zinc-200">
              <Database className="w-5 h-5" />
            </div>
            <CardTitle className="text-base">Grounded Knowledge RAG</CardTitle>
            <CardDescription className="text-xs text-zinc-500 leading-relaxed">
              Questions are anchored directly in role-specific knowledge base documents, guaranteeing zero generic hallucinated questions.
            </CardDescription>
          </CardHeader>
        </Card>
      </section>

      {/* Workflow Summary */}
      <Card className="p-8 space-y-6">
        <div className="text-center space-y-1">
          <h2 className="text-xl font-bold text-zinc-900">How IntervueAI Works</h2>
          <p className="text-xs text-zinc-500">End-to-end technical interview lifecycle</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2">
          <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-zinc-500">01. UPLOAD</div>
            <div className="text-sm font-semibold text-zinc-900">Resume & Profile</div>
            <div className="text-xs text-zinc-500">Extracts skills & probing areas</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-zinc-500">02. RETRIEVE</div>
            <div className="text-sm font-semibold text-zinc-900">RAG Ingestion</div>
            <div className="text-xs text-zinc-500">Fetches reference context</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-zinc-500">03. INTERACT</div>
            <div className="text-sm font-semibold text-zinc-900">Adaptive QA</div>
            <div className="text-xs text-zinc-500">Dynamic difficulty scaling</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-zinc-500">04. REPORT</div>
            <div className="text-sm font-semibold text-zinc-900">Traceable Results</div>
            <div className="text-xs text-zinc-500">Complete audit & hiring recommendation</div>
          </div>
        </div>
      </Card>
    </div>
  );
}

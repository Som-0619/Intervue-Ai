'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { CandidateResponse } from '@/lib/types';
import { candidateApi, interviewApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  Upload, CheckCircle2, AlertCircle, Sparkles, User, Briefcase,
  FileText, ArrowRight, Loader2, Plus, X, Cpu, Server, Layout, Layers, Shield,
  Camera, Mic, Video, VideoOff, MicOff
} from 'lucide-react';

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Candidate Data Form
  const [name, setName] = useState('Alex Rivera');
  const [targetRole, setTargetRole] = useState('AI/ML Engineer');
  const [yearsExp, setYearsExp] = useState(3.5);
  const [email, setEmail] = useState('alex.rivera@example.com');
  const [resumeText, setResumeText] = useState('Senior AI engineer proficient in Python, PyTorch, RAG architectures, FastAPI, Vector Databases, System Design, and Docker.');
  
  // File Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Configuration State
  const [loading, setLoading] = useState(false);
  const [candidate, setCandidate] = useState<CandidateResponse | null>(null);
  const [topics, setTopics] = useState<string[]>([]);
  const [newTopic, setNewTopic] = useState('');
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [difficulty, setDifficulty] = useState('Intermediate');
  const [errorMsg, setErrorMsg] = useState('');

  // Camera & Mic Verification State
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [cameraStatus, setCameraStatus] = useState<'pending' | 'granted' | 'denied'>('pending');
  const [micStatus, setMicStatus] = useState<'pending' | 'granted' | 'denied'>('pending');
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const requestMediaPermissions = async () => {
    try {
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        setMediaStream(stream);
        setCameraStatus('granted');
        setMicStatus('granted');
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }
    } catch (err) {
      console.warn('Camera/Mic permission failed:', err);
      setCameraStatus('denied');
      setMicStatus('denied');
    }
  };

  useEffect(() => {
    if (step === 3) {
      requestMediaPermissions();
    }
  }, [step]);

  const roles = [
    { title: 'AI/ML Engineer', icon: Cpu, desc: 'RAG, Vector DBs, PyTorch, LLMs, Fine-tuning' },
    { title: 'Backend Engineer', icon: Server, desc: 'High-throughput APIs, System Design, SQL/Redis, Distributed Systems' },
    { title: 'Frontend Engineer', icon: Layout, desc: 'Next.js, React Fiber, Performance, Web Security, TypeScript' },
    { title: 'Fullstack Engineer', icon: Layers, desc: 'End-to-End Web Apps, REST/GraphQL, Databases, Microservices' },
    { title: 'DevOps/SRE Engineer', icon: Shield, desc: 'Kubernetes, CI/CD, Infrastructure as Code, Observability' },
  ];

  // Drag & Drop Handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'pdf' && ext !== 'txt') {
      setErrorMsg('Please upload a valid PDF (.pdf) or text (.txt) file.');
      return;
    }
    setErrorMsg('');
    setSelectedFile(file);
  };

  const handleParseCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    setUploadProgress(20);

    try {
      let candRes: CandidateResponse;
      if (selectedFile) {
        setUploadProgress(50);
        const formData = new FormData();
        formData.append('name', name);
        formData.append('target_role', targetRole);
        formData.append('years_of_experience', yearsExp.toString());
        if (email) formData.append('email', email);
        formData.append('file', selectedFile);
        candRes = await candidateApi.uploadResume(formData);
      } else {
        setUploadProgress(50);
        candRes = await candidateApi.create({
          name,
          target_role: targetRole,
          years_of_experience: yearsExp,
          email,
          resume_text: resumeText
        });
      }

      setUploadProgress(100);
      setCandidate(candRes);
      
      // Seed dynamic focus areas
      const prof = candRes.parsed_profile;
      const initialTopics = [
        ...(prof?.skill_gaps || []),
        ...(prof?.strengths || []),
        'System Architecture'
      ].slice(0, 5);
      
      setTopics(initialTopics.length ? initialTopics : ['Core Fundamentals', 'Architecture', 'Performance']);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to process resume and profile setup.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddTopic = () => {
    if (newTopic.trim() && !topics.includes(newTopic.trim())) {
      setTopics([...topics, newTopic.trim()]);
      setNewTopic('');
    }
  };

  const handleRemoveTopic = (index: number) => {
    setTopics(topics.filter((_, i) => i !== index));
  };

  const handleStartInterview = async () => {
    if (!candidate) return;
    setLoading(true);
    setErrorMsg('');

    try {
      const session = await interviewApi.create({
        candidate_id: candidate.id,
        target_role: targetRole,
        total_questions: totalQuestions,
        custom_topics: topics
      });

      router.push(`/interview/${session.id}`);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || err?.message || 'Failed to launch interview session.');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 py-4">
      {/* Step Indicator Bar */}
      <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
        <div className="flex items-center gap-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${step >= 1 ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-400'}`}>
            1
          </div>
          <span className={`text-xs font-semibold ${step >= 1 ? 'text-zinc-900' : 'text-zinc-400'}`}>
            Resume & Role
          </span>
        </div>

        <div className="h-px w-12 bg-zinc-200" />

        <div className="flex items-center gap-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${step >= 2 ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-400'}`}>
            2
          </div>
          <span className={`text-xs font-semibold ${step >= 2 ? 'text-zinc-900' : 'text-zinc-400'}`}>
            Resume Analysis
          </span>
        </div>

        <div className="h-px w-12 bg-zinc-200" />

        <div className="flex items-center gap-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${step >= 3 ? 'bg-zinc-900 text-white' : 'bg-zinc-100 text-zinc-400'}`}>
            3
          </div>
          <span className={`text-xs font-semibold ${step >= 3 ? 'text-zinc-900' : 'text-zinc-400'}`}>
            Preparation & Launch
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* STEP 1: Resume Upload & Role Selection */}
      {step === 1 && (
        <form onSubmit={handleParseCandidate} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Candidate Setup & Resume Ingestion</CardTitle>
              <CardDescription>
                Provide basic candidate info and select the target position.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label htmlFor="candidateName" className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Candidate Full Name</label>
                  <input
                    id="candidateName"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-sm focus-ring"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Years of Experience</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={yearsExp}
                    onChange={(e) => setYearsExp(parseFloat(e.target.value) || 0)}
                    className="w-full px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-sm focus-ring"
                  />
                </div>
              </div>

              {/* Role Selection Cards */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Select Target Job Role</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {roles.map((r) => {
                    const IconComp = r.icon;
                    const isSelected = targetRole === r.title;
                    return (
                      <div
                        key={r.title}
                        onClick={() => setTargetRole(r.title)}
                        className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                          isSelected ? 'border-zinc-900 bg-zinc-50 shadow-sm' : 'border-zinc-200 bg-white hover:border-zinc-300'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <IconComp className={`w-4 h-4 ${isSelected ? 'text-zinc-900' : 'text-zinc-500'}`} />
                          <span className="font-semibold text-xs text-zinc-900">{r.title}</span>
                        </div>
                        <p className="text-[11px] text-zinc-500">{r.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Drag and Drop Resume Upload */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Upload Resume (PDF / TXT)</label>
                <div
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                    dragActive ? 'border-zinc-900 bg-zinc-50' : 'border-zinc-200 bg-white hover:border-zinc-300'
                  }`}
                >
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload"
                  />
                  {selectedFile ? (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-xs">
                      <div className="flex items-center gap-2 font-mono text-zinc-800">
                        <FileText className="w-4 h-4 text-zinc-600" />
                        <span className="font-medium">{selectedFile.name}</span>
                        <span className="text-zinc-400">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedFile(null)}
                        className="text-zinc-400 hover:text-zinc-700 p-1"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
                      <Upload className="w-6 h-6 text-zinc-400 mx-auto" />
                      <div className="text-xs font-medium text-zinc-900">
                        Drag and drop your PDF resume here, or <span className="underline">browse files</span>
                      </div>
                      <div className="text-[11px] text-zinc-400">Supports PDF or TXT up to 10MB</div>
                    </label>
                  )}
                </div>
              </div>

              {/* Paste Plain Text Option */}
              {!selectedFile && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Or Paste Raw Resume Text</label>
                  <textarea
                    rows={3}
                    value={resumeText}
                    onChange={(e) => setResumeText(e.target.value)}
                    className="w-full p-3 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-xs font-mono focus-ring"
                  />
                </div>
              )}

              {loading && uploadProgress > 0 && (
                <div className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono text-zinc-500">
                    <span>Parsing Resume...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
                    <div className="h-full bg-zinc-900 transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                  </div>
                </div>
              )}
            </CardContent>

            <CardFooter>
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
                <span>Analyze Resume & Extract Profile</span>
              </Button>
            </CardFooter>
          </Card>
        </form>
      )}

      {/* STEP 2: Resume Analysis & Candidate Profile */}
      {step === 2 && candidate && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl">Resume Analysis Results</CardTitle>
                  <CardDescription>Extracted candidate profile and identified probing topics.</CardDescription>
                </div>
                <Badge variant="outline">{candidate.target_role}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-zinc-500 block">Candidate Name</span>
                  <span className="font-semibold text-zinc-900">{candidate.name}</span>
                </div>
                <div>
                  <span className="text-zinc-500 block">Experience Level</span>
                  <span className="font-semibold text-zinc-900">{candidate.years_of_experience} Years</span>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Detected Technical Skills & Technologies</h4>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.parsed_profile?.skills.map((skill) => (
                    <Badge key={skill} variant="secondary">{skill}</Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Identified Probing Areas (Gaps)</h4>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.parsed_profile?.skill_gaps.map((gap) => (
                    <Badge key={gap} variant="warning">{gap}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>
                Back to Setup
              </Button>
              <Button onClick={() => setStep(3)}>
                <span>Configure Preparation</span>
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* STEP 3: Interview Configuration & Preparation */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Interview Preparation & Launch</CardTitle>
            <CardDescription>Set difficulty parameters and review selected interview focus areas.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Target Difficulty</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-sm focus-ring"
                >
                  <option value="Junior">Junior Engineer</option>
                  <option value="Intermediate">Intermediate Engineer</option>
                  <option value="Senior">Senior Engineer</option>
                  <option value="Principal">Principal Architect</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Number of Questions</label>
                <select
                  value={totalQuestions}
                  onChange={(e) => setTotalQuestions(parseInt(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-sm focus-ring"
                >
                  <option value={3}>3 Questions (Express)</option>
                  <option value={5}>5 Questions (Standard)</option>
                  <option value={7}>7 Questions (Comprehensive)</option>
                </select>
              </div>
            </div>

            {/* Camera & Mic Device Verification Panel */}
            <div className="space-y-2 p-4 rounded-xl bg-zinc-900 text-white border border-zinc-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300">
                  <Camera className="w-4 h-4 text-emerald-400" />
                  <span>Pre-Interview Device & Permissions Check</span>
                </div>
                <Button variant="outline" size="sm" onClick={requestMediaPermissions} type="button" className="text-zinc-200 border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-xs">
                  <Sparkles className="w-3.5 h-3.5 mr-1" />
                  Test / Re-enable
                </Button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center pt-2">
                <div className="relative rounded-lg overflow-hidden bg-zinc-950 border border-zinc-800 h-36 flex items-center justify-center">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  />
                  {cameraStatus !== 'granted' && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center p-3 text-center bg-zinc-950/90 text-zinc-400 space-y-1 text-xs">
                      <VideoOff className="w-6 h-6 text-zinc-500 mb-1" />
                      <span>Camera permission required</span>
                      <span className="text-[10px] text-zinc-500">Click Test / Re-enable to grant access</span>
                    </div>
                  )}
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/50">
                    <div className="flex items-center gap-2">
                      <Video className="w-4 h-4 text-zinc-400" />
                      <span>Camera Feed</span>
                    </div>
                    <Badge variant={cameraStatus === 'granted' ? 'success' : 'warning'}>
                      {cameraStatus === 'granted' ? 'Active / Granted' : 'Pending Access'}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-800/60 border border-zinc-700/50">
                    <div className="flex items-center gap-2">
                      <Mic className="w-4 h-4 text-zinc-400" />
                      <span>Microphone Audio</span>
                    </div>
                    <Badge variant={micStatus === 'granted' ? 'success' : 'warning'}>
                      {micStatus === 'granted' ? 'Active / Granted' : 'Pending Access'}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-xs font-semibold text-zinc-700 uppercase tracking-wider">Interview Roadmap Topics</label>
              <div className="space-y-2">
                {topics.map((t, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-xs">
                    <span className="font-medium text-zinc-900">{idx + 1}. {t}</span>
                    <button onClick={() => handleRemoveTopic(idx)} className="text-zinc-400 hover:text-red-600 p-1">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add custom topic..."
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  className="flex-1 px-3.5 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-900 text-xs focus-ring"
                />
                <Button variant="outline" size="sm" onClick={handleAddTopic} type="button">
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Add
                </Button>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>
              Back
            </Button>
            <Button onClick={handleStartInterview} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
              <span>Launch Grounded Interview</span>
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}

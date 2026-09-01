# IntervueAI Demonstration Walkthrough

This guide demonstrates how to test and showcase IntervueAI's end-to-end capabilities.

## 1. Quickstart Commands

### Step 1: Run Ingestion Script
```bash
python scripts/ingest_knowledge.py
```

### Step 2: Start Backend Server
```bash
cd backend
source venv/bin/activate
python app/main.py
```

### Step 3: Start Frontend App
```bash
cd frontend
npm run dev
```

## 2. Interactive Feature Demo Flow

1. Open [http://localhost:3000](http://localhost:3000).
2. Click **Start Interview**.
3. Upload `demo/sample_resume.txt` or paste text.
4. Review extracted candidate skills (Python, PyTorch, RAG Systems, FastAPI).
5. Configure 5 questions for `AI/ML Engineer` role.
6. Launch interactive interview.
7. Observe grounded questions tied directly to Knowledge Base chunks.
8. Submit answers and view live adaptive difficulty adjustments.
9. Inspect final report at `/report/[id]` with full RAG traceability lineage!

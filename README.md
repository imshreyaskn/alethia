# Realive

> AI-Assisted CI/CD Test Repair Platform — Python First, V1

---

## What is Realive?

When your application code changes (a renamed field, a refactored function), existing tests break — not because there's a bug, but because the tests reference outdated contracts. Realive detects these test-level mismatches in your CI pipeline, proposes a minimal AST-level fix, and — with your approval — applies it.

---

## Project Structure

```
realive/
├── backend/          # FastAPI — webhook receiver, API, session management
│   ├── app/
│   │   ├── main.py       # App entry point
│   │   ├── core/         # Config, shared utilities
│   │   ├── api/          # Route handlers
│   │   └── db/           # Supabase client
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/         # React + Vite — operational dashboard
│   └── Dockerfile
│
├── agent/            # LangGraph — AI agent graph
│   ├── graph.py          # Graph definition
│   ├── state.py          # Shared state schema
│   └── nodes/            # One file per graph node
│
├── runner/           # Docker image for sandboxed pytest execution
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example      # Copy to .env and fill in your secrets
└── README.md
```

---

## Prerequisites

- [Python 3.12+](https://www.python.org/downloads/)
- [Node.js 20+](https://nodejs.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A [Supabase](https://supabase.com) account (free tier works)
- A [Google AI Studio](https://aistudio.google.com) account (for Gemini API key)

---

## Local Setup

### 1. Clone and configure

```bash
# Copy the environment template
copy .env.example .env
# Then open .env and fill in your values (see comments in the file)
```

### 2. Set up the Python backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Set up the React frontend

```bash
cd frontend
npm install
```

### 4. Build the runner image (one-time)

```bash
docker build -t realive-runner:python ./runner
```

### 5. Start everything

```bash
# Option A: All services via Docker Compose
docker compose up --build

# Option B: Run services individually (easier for development)
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

### 6. Verify

- Backend API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Health check: http://localhost:8000/api/health

---

## Build Milestones

| # | Milestone | Status |
|---|---|---|
| 0 | Project Scaffold | ✅ Done |
| 1 | Database Schema (Supabase) | ⬜ |
| 2 | GitHub App Auth | ⬜ |
| 3 | Webhook Receiver & Log Parser | ⬜ |
| 4 | Failure Classifier (LangGraph) | ⬜ |
| 5 | Human-in-the-Loop Gate | ⬜ |
| 6 | AST Patcher (libCST) | ⬜ |
| 7 | Docker Test Runner & Retry Loop | ⬜ |
| 8 | Fix Delivery (PR & Commit) | ⬜ |
| 9 | React Dashboard | ⬜ |
| 10 | Realtime & WebSocket | ⬜ |
| 11 | End-to-End Integration | ⬜ |

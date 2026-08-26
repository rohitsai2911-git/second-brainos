# Second Brain OS — Design Spec

**Date:** 2026-08-26
**Status:** Approved

## Goal
AI-powered personal knowledge platform (not a chatbot): universal ingestion, knowledge graph,
RAG chat with long-term memory, semantic search, flashcards (SM-2), study plans, code explanation.
Resume-grade: production architecture, clean code, complete docs.

## Stack
Next.js 14 + TypeScript + Tailwind | FastAPI + SQLAlchemy | PostgreSQL 16 | Qdrant 1.8 | Docker Compose.
LLM: OpenAI-compatible API when `OPENAI_API_KEY` set; built-in offline fallback engine otherwise.

## Architecture

```
frontend (3000) ──REST──> backend (8000) ──SQLAlchemy──> Postgres (5432)
                              │
                              ├──embeddings (bge-small-en-v1.5, local)
                              ├──Qdrant client────────> Qdrant (6333)
                              └──LLM service (OpenAI-compat or local fallback)
```

Backend layering: `routers/` (HTTP, auth guard) → `services/` (domain logic) → `models/` (ORM).
Frontend: app router pages + reusable components; `lib/api.ts` typed client; JWT in localStorage.

## Data model (existing, verified)
User, Document, Chunk, Conversation, Message (with sources JSON), FlashcardDeck, Flashcard
(SM-2 fields), Task, Memory (long-term facts), DocumentLink (graph edge w/ similarity).

## Backend work — audit & fix (no rewrite)
1. `compileall` every module; fix all errors.
2. Review each router/service for bugs and gaps:
   - auth: register/login/JWT dependency
   - documents: upload → extract text → chunk → embed → upsert Qdrant; summarize/tags async-safe;
     delete cascades chunks+vectors; code-explain endpoint present
   - search: semantic top-k with score + snippet
   - chat: conversation CRUD, memory extraction, RAG answer with citations
   - flashcards: generate from doc, review endpoint updates SM-2 state
   - tasks: CRUD + AI study-plan generation into tasks
   - graph: build nodes/edges from DocumentLink similarity
   - stats: dashboard aggregates
3. Startup: table creation retry + Qdrant collection ensure.

## Frontend work — build missing (zero new deps)

Pages: `/dashboard`, `/documents`, `/documents/[id]`, `/search`, `/chat`,
`/graph`, `/flashcards`, `/planner`. Existing: landing, login, register, shell, theme, auth ctx.

Components: `upload-zone` (drag-drop + progress), `graph-canvas` (custom SVG force-directed
layout, ~150 lines physics, drag/zoom/pan, node click → doc), `chat-window` (thread, markdown,
citations sidebar), `flashcard-review` (grading buttons wired to SM-2), `task-board`
(3-column kanban), `stat-card`, `doc-card`.

Design: existing Tailwind tokens (`primary`, `muted`, `glass`), dark mode default, responsive.

## Verification
- Backend: `python -m compileall`; boot via docker compose; httpx smoke script hits every
  endpoint (register→upload→search→chat→flashcards→tasks→graph→stats).
- Frontend: `npm run build` clean; typecheck via build.

## Docs
Root README: overview, architecture diagram, features, quickstart (docker compose up),
env vars, API reference table, tech highlights.

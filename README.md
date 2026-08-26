# Second Brain OS 🧠

An AI-powered personal knowledge platform — **not a chatbot**. Upload PDFs, notes, code, images and
documents; the system ingests, understands, connects and retrieves everything for you.

![stack](https://img.shields.io/badge/Next.js%2014-TypeScript-3178c6) ![api](https://img.shields.io/badge/FastAPI-Python-009688) ![db](https://img.shields.io/badge/PostgreSQL-Qdrant-4169e1) ![infra](https://img.shields.io/badge/Docker-Compose-2496ed)

## What it does

| Capability | How |
|---|---|
| **Universal ingestion** | PDF, DOCX, code, images, plain text, quick notes — auto-extracted, chunked, embedded |
| **Semantic search** | Vector search (Qdrant + bge-small embeddings) with keyword fallback |
| **RAG chat with citations** | Answers grounded in *your* documents, every claim linked to its source |
| **Long-term memory** | The assistant extracts durable facts ("remember that…") and recalls them across sessions |
| **Knowledge graph** | Documents are automatically linked by semantic similarity — interactive force-directed visualization |
| **Flashcards + spaced repetition** | AI-generated decks reviewed with the SM-2 algorithm |
| **Study plans** | Day-by-day plans generated from a goal and grounded in your own material |
| **Code explanation** | Structural + natural-language explanations of code files in your base |

Works **fully offline**: with no `OPENAI_API_KEY`, a built-in local engine handles summarization,
tagging, flashcards and planning (extractive + heuristic), so demos never break.

## Architecture

```
┌─────────────┐   REST    ┌──────────────────┐        ┌────────────┐
│  Next.js 14 │ ────────► │     FastAPI      │──────► │ PostgreSQL │
│  TypeScript │           │                  │        └────────────┘
│  Tailwind   │           │  routers/ (HTTP) │        ┌────────────┐
│  Dark mode  │           │  services/ (AI)  │──────► │   Qdrant   │
└─────────────┘           │  models/ (ORM)   │ vector │  (bge-small│
                          └──────────────────┘ index  │ embeddings)│
                                   │                  └────────────┘
                                   ▼
                        OpenAI-compatible LLM API
                        (or local fallback engine)
```

**Backend layering:** HTTP concerns stay in `routers/`, domain logic in `services/`
(`ingestion`, `embeddings`, `vectorstore`, `llm`, `spaced_repetition`), persistence in SQLAlchemy models.
Background ingestion runs per-upload with its own DB session.

## Quickstart

```bash
cp .env.example .env          # optional: add OPENAI_API_KEY
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/health |
| Swagger docs | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

First boot downloads the embedding model (~90MB) into the backend image.

## Configuration

All via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Empty → offline fallback engine |
| `OPENAI_BASE_URL` | *(empty)* | Point at OpenRouter/Ollama/LM Studio etc. |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model name |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local sentence-transformers model |
| `JWT_SECRET` | dev value | **Change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (7 days) |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated origins |
| `MAX_UPLOAD_MB` | `50` | Upload size cap |

## API overview

All routes are JWT-guarded under `/api` except auth.

```
POST /api/auth/register · /login            GET /api/auth/me
GET/POST /api/documents                     POST /api/documents/upload (multipart)
POST /api/documents/notes                   PATCH/DELETE /api/documents/{id}
GET  /api/documents/{id}/file               POST /api/documents/{id}/explain
POST /api/search                            { query, limit } → scored chunk hits
GET/DELETE /api/chat/conversations[/{id}]   POST /api/chat { message, conversation_id? }
GET/DELETE /api/chat/memories[/{id}]        long-term memory management
GET  /api/flashcards/decks                  POST /api/flashcards/generate
GET  /api/flashcards/decks/{id}/due         POST /api/flashcards/cards/{id}/review (SM-2)
CRUD /api/tasks                             POST /api/tasks/study-plan
GET  /api/graph                             nodes + similarity edges
GET  /api/stats                             dashboard aggregates
```

## Development

```bash
# Backend (local venv)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Full API smoke test (SQLite, no services needed)
.venv/Scripts/python backend/scripts/smoke_test.py   # Windows
python backend/scripts/smoke_test.py                 # POSIX
```

## Project structure

```
backend/
  app/
    main.py            # FastAPI app, lifespan init
    config.py          # env-driven settings
    database.py        # engine/session
    security.py        # bcrypt + JWT
    models.py          # User, Document, Chunk, Conversation, Message,
                       # FlashcardDeck, Flashcard, Task, Memory, DocumentLink
    schemas.py         # Pydantic I/O contracts
    routers/           # auth, documents, search, chat, flashcards, tasks, graph, stats
    services/
      ingestion.py     # extract → chunk → embed → index → link
      embeddings.py    # bge-small local model (+ hashed-bag fallback)
      vectorstore.py   # Qdrant upsert/search/delete
      llm.py           # LLM calls + complete offline fallback engine
      spaced_repetition.py  # SM-2 scheduler
frontend/
  app/                 # landing, auth, dashboard, documents, viewer,
                       # search, chat, graph, flashcards, planner
  components/          # app-shell, upload-zone, graph-canvas (custom force layout),
                       # chat-window, flashcard-review, task-board, doc-card, stat-card
  lib/                 # typed API client, auth context, shared types
docs/specs/            # design documents
docker-compose.yml     # postgres + qdrant + backend + frontend
```

## Engineering highlights

- **Graceful degradation everywhere** — no Qdrant? Keyword fallback search. No LLM key?
  Local extractive engine. Embedding model missing? Deterministic hashed embeddings.
- **Custom force-directed graph** (~150 lines) — zero graph libraries, physics simulation,
  drag/zoom/pan, type-colored nodes.
- **SM-2 spaced repetition** implemented from the original algorithm spec.
- **Verified end-to-end** — 34-check smoke suite covering auth → ingestion → RAG → review → planner.

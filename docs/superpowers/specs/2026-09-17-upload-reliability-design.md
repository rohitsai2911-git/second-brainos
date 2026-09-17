# Upload Reliability Design — 2026-09-17

## Context

The frontend working tree already implements the upload-reliability UX:
polling while `status === "processing"`, `processing_stage` display with
`"queued"` fallback, `error_message` + retry button calling
`POST /api/documents/{id}/retry`, `processing_warning` banner, per-file
progress counters, and a failed-files retry list (`frontend/app/(app)/
documents/page.tsx`, `frontend/app/(app)/documents/[id]/page.tsx`,
`frontend/components/doc-card.tsx`, `frontend/lib/types.ts`).

The backend does not implement any of it: `Document` has no
`processing_stage` / `error_message` / `processing_warning` columns,
`schemas.DocumentOut` does not expose them, and the retry endpoint does
not exist. The current pipeline (`backend/app/routers/documents.py` +
`backend/app/services/ingestion.py`) also has hardening gaps: the raw
filename is interpolated into the stored path, the full file is read into
memory before the size check, empty files are accepted, failed uploads can
orphan files on disk, background-stage progress is invisible, and a
Qdrant/vector failure is silently swallowed with no signal to the UI.

## Goals

1. Match the backend contract the frontend already consumes.
2. Make every upload failure visible, classed (`error` vs `warning`), and
   recoverable (retry).
3. Close the cheap security/robustness holes in the upload path.
4. Cover all of the above with regression tests; keep the existing
   34-check smoke suite green, `tsc --noEmit` clean.

## Non-goals

- Resumable/chunked uploads, upload-progress API, background worker
  infrastructure (e.g. Celery/RQ), object storage migration, OCR for
  images, per-user quotas. Deferred until real usage demands them.

## Architecture

Same layering as today: HTTP stays in `routers/documents.py`, domain logic
in `services/ingestion.py`, persistence in `models.py`, wire contracts in
`schemas.py`. No new services, tables, or dependencies.

## Data model

Add three non-nullable string columns with empty-string defaults to
`Document`:

- `processing_stage: str = ""` — one of `queued | extracting | chunking |
  indexing | linking | ready | error`. Empty means unset; API serializes
  empty as `"queued"` only via the existing frontend fallback (backend
  returns `""`, frontend renders `|| "queued"`).
- `error_message: str = ""` — human-readable fatal failure reason, set
  only when `status == "error"`.
- `processing_warning: str = ""` — non-fatal degradation note (e.g.
  vector index failed, keyword fallback active), set while
  `status == "ready"`.

Migration: the project uses `Base.metadata.create_all` with no Alembic.
`create_all` covers fresh databases; for existing SQLite/Postgres volumes
run a guarded `ALTER TABLE documents ADD COLUMN IF NOT EXISTS`
(SQLite: check `PRAGMA table_info` first) at startup or as a one-off
script before deploy. Local dev DBs (`smoke.db`, `local_dev.db`) are
recreated by the smoke script / documented reset.

## API changes

- `schemas.DocumentOut` (and therefore `DocumentDetail`) gains the three
  fields. All document responses (upload, notes, list, detail, update,
  retry) return them.
- `POST /api/documents/{id}/retry` (owner-scoped, 404 for foreign/missing
  ids):
  - Accepts only documents with `status == "error"`; otherwise `409`.
  - Resets the row to `status="processing"`, `processing_stage="queued"`,
    clears `error_message` (keeps `processing_warning` cleared too),
    re-extracts bytes from the stored file on disk (notes: from
    `content_text` already persisted), and re-runs the staged ingestion.
  - Returns `DocumentOut` with the reset state; the frontend's existing
    polling picks up the terminal state.

## Ingestion flow

Upload (`POST /api/documents/upload`):

1. Early reject: if the request `Content-Length` exceeds
   `MAX_UPLOAD_MB`, return `413` before reading the body.
2. Read body, re-check byte length against the cap (`413`), reject empty
   bodies (`400`, "empty file").
3. Sanitize: `basename(filename)`, strip path separators, cap to 255
   chars, fall back to `"untitled"`. Stored name stays
   `{uuid}_{sanitized}` under `UPLOAD_DIR`.
4. Write file to disk; on any later failure before commit, remove the
   partially written file.
5. Insert row with `status="processing"`, `processing_stage="queued"`.
6. Extract text synchronously with per-type guards (current `extract_text`
   behavior kept; extraction exceptions yield `""`, never raise).
7. Enqueue background `_ingest_bg`, which updates and commits
   `processing_stage` at each step: `extracting → chunking → indexing →
   linking → ready`. Each stage commit is independent so polling observes
   progress.

Notes (`POST /api/documents/notes`) follow the same stage machine with
no file on disk; retry re-ingests from persisted `content_text`.

## Error handling

| Case | Backend behavior |
|---|---|
| Oversize | `413` with cap in message, no file written |
| Empty file / empty note content | `400`, no row created (upload); notes require non-empty title, empty content still ingested as today |
| Corrupt PDF/DOCX | Extract yields `""`, pipeline continues; doc becomes `ready` with empty content and no chunks (current behavior preserved) |
| Fatal ingest exception | `status="error"`, `processing_stage="error"`, `error_message` set (truncated to 500 chars), file kept on disk for retry |
| Vector upsert failure | Swallowed as today, but sets `processing_warning` (e.g. "Vector index unavailable; keyword fallback active") while `status="ready"` |
| Link rebuild failure | Rolled back independently; never fails the document |
| Retry on non-error doc | `409` |
| Retry with missing file on disk | `error` again with "Original file missing" message |
| Delete | Unchanged, plus removes stored file; best-effort vector delete kept |

## Frontend contract (already built, no changes)

- `Document` / `DocumentDetail` types already carry the three fields.
- List page polls every 2.5s while any doc is `processing`; viewer polls
  every 2s while open doc is `processing`.
- `doc-card` shows stage badge, error text, warning text.
- Viewer shows stage banner, error panel with retry button, warning
  panel. No frontend work in this scope beyond verifying against the
  real backend.

## Testing

Extend `backend/scripts/smoke_test.py` (in-process FastAPI + SQLite,
Qdrant unreachable by design):

1. Upload empty file → `400`.
2. Upload over cap (monkeypatched small `MAX_UPLOAD_MB` or direct
   oversize post) → `413`.
3. Path-traversal filename (`../../evil.txt`) → stored safely under
   `UPLOAD_DIR`, `200/201`.
4. Note ingest → reaches `status == "ready"`; vector-down run asserts `processing_warning` non-empty with
   `status == "ready"`.
5. Force an ingest error (e.g. corrupt row or simulated failure) →
   `status == "error"`, `error_message` non-empty.
6. `POST /retry` on the error doc → back to terminal state;
   retry on a `ready` doc → `409`; retry on unknown id → `404`.
7. All 34 existing checks still pass.

Verification gates: smoke suite green, `npx tsc --noEmit` clean.
Lint is unavailable (no ESLint config; `next lint` prompts for setup;
no backend linter configured) — recorded as a gap, not a gate.

## Rollout

1. Land migration guard + model/schema/router/ingestion changes.
2. Reset or migrate local dev DBs.
3. Run smoke + typecheck.
4. Manual pass: upload PDF/text/image, bad file, delete, retry,
   Qdrant-down warning banner.

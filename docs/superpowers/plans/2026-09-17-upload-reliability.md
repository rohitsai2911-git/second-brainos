# Upload Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend upload pipeline match the frontend reliability contract (stage, error, warning, retry) with hardening and regression tests.

**Architecture:** Keep current layering — HTTP in `routers/documents.py`, domain logic in `services/ingestion.py`, persistence in `models.py`, wire contracts in `schemas.py`. Add a small column-migration guard for existing DBs (no Alembic in this repo).

**Tech Stack:** FastAPI 0.110.0, SQLAlchemy 2.0.29, Pydantic 2.6.4, SQLite (smoke) / PostgreSQL (prod), Next.js 14 frontend (verify-only, no changes).

## Global Constraints

- No new dependencies.
- No frontend changes in this scope (frontend already built).
- `MAX_UPLOAD_MB` stays `100`.
- Error text truncated to 500 chars; sanitized filenames capped at 255 chars.
- Every task ends with its own test run and a commit; only stage files the task owns.

---

### Task 1: Data model, schemas, migration guard

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: existing `Document` model, `DocumentOut`, `engine`/`Base`, lifespan in `main.py`.
- Produces: `Document.processing_stage: str`, `Document.error_message: str`, `Document.processing_warning: str`; same three fields on `DocumentOut`; `ensure_reliability_columns() -> None` in `database.py` called from lifespan.

- [ ] **Step 1: Write the failing check**

Append a scratch check (not committed) proving the columns are missing:

```python
from app.database import engine
from sqlalchemy import inspect
cols = {c["name"] for c in inspect(engine).get_columns("documents")}
assert {"processing_stage", "error_message", "processing_warning"} <= cols, sorted(cols)
```

Run: `.venv\Scripts\python.exe -c "from sqlalchemy import inspect; from backend.app.database import engine; print(sorted(c['name'] for c in inspect(engine).get_columns('documents')))"` from repo root (adjust import path to `app.database` with `workdir=backend`).
Expected: assertion fails / new names absent.

- [ ] **Step 2: Run check to verify it fails**

Run the command above.
Expected: FAIL — the three columns are absent.

- [ ] **Step 3: Write minimal implementation**

`backend/app/models.py` — add to `Document` after `status`:

```python
status = Column(String, default="ready")            # processing | ready | error
processing_stage = Column(String, default="")       # queued | extracting | chunking | indexing | linking | ready | error
error_message = Column(Text, default="")
processing_warning = Column(Text, default="")
```

`backend/app/schemas.py` — extend `DocumentOut`:

```python
status: str
processing_stage: str = ""
error_message: str = ""
processing_warning: str = ""
```

`backend/app/database.py` — append:

```python
def ensure_reliability_columns() -> None:
    """Add reliability columns to existing DBs (create_all only covers fresh DBs)."""
    from sqlalchemy import inspect, text
    needed = {
        "processing_stage": "VARCHAR",
        "error_message": "TEXT",
        "processing_warning": "TEXT",
    }
    with engine.begin() as conn:
        existing = {c["name"] for c in inspect(conn).get_columns("documents")}
        for name, ddl in needed.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE documents ADD COLUMN {name} {ddl}"))
```

`backend/app/main.py` — in `lifespan`, after the `create_all` retry loop, before `ensure_collection`:

```python
from .database import engine, Base
from . import database as _db
_db.ensure_reliability_columns()
```

(Keep existing imports; add only the guard call.)

- [ ] **Step 4: Run check to verify it passes**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: `PASSED: 34 FAILED: 0 / ALL SMOKE TESTS GREEN` (columns default to `""`; old rows unaffected).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/schemas.py backend/app/database.py backend/app/main.py
git commit -m "feat: add document reliability columns and migration guard"
```

---

### Task 2: Staged ingestion with warning and error signals

**Files:**
- Modify: `backend/app/services/ingestion.py`

**Interfaces:**
- Consumes: `Document` rows with `status="processing"`; `vectorstore.upsert_chunks`; `llm.summarize/auto_tags`.
- Produces: stage progression persisted on `document.processing_stage` (`queued → extracting → chunking → indexing → linking → ready`, or `error`); `document.processing_warning` set when vector upsert fails; `document.error_message` (max 500 chars) set on fatal failure with `status="error"`.

- [ ] **Step 1: Write the failing test**

Append to `backend/scripts/smoke_test.py` before the final summary print (temporary probe, replaced by the real regression block in Task 4):

```python
r = client.post("/api/documents/notes", json={"title": "Stage probe", "content": "hello world probe content"}, headers=H)
_probe = r.json()
check("probe stage field present", "processing_stage" in _probe, str(_probe)[:200])
```

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: FAIL on the new check (`processing_stage` missing from response until Task 1 lands; after Task 1 it passes but `processing_warning` on vector-down is still unset — verified in Task 4).

- [ ] **Step 2: Run test to verify baseline**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: probe check fails before implementation (or warning unset on Qdrant-down path).

- [ ] **Step 3: Write minimal implementation**

Rewrite `ingest_document` in `backend/app/services/ingestion.py` as staged (exact replacement):

```python
def _set_stage(db: Session, document: models.Document, stage: str) -> None:
    document.processing_stage = stage
    db.commit()


def ingest_document(db: Session, document: models.Document, raw_text: str) -> models.Document:
    """Full pipeline for one document row already persisted with status=processing."""
    try:
        _set_stage(db, document, "extracting")
        document.content_text = raw_text[:200_000]
        document.error_message = ""
        document.processing_warning = ""
        db.commit()

        document.summary = llm.summarize(raw_text) if raw_text else ""
        if not document.tags:
            document.tags = llm.auto_tags(raw_text[:6000], document.title) if raw_text else []
        db.commit()

        _set_stage(db, document, "chunking")
        chunk_texts = chunk_text(raw_text)
        chunk_rows = []
        for i, text in enumerate(chunk_texts):
            row = models.Chunk(id=str(uuid.uuid4()), document_id=document.id,
                               user_id=document.user_id, chunk_index=i, text=text)
            db.add(row)
            chunk_rows.append({"id": row.id, "text": text, "index": i})
        db.commit()

        _set_stage(db, document, "indexing")
        try:
            vectorstore.upsert_chunks(document.user_id, document.id, document.title,
                                      document.file_type, chunk_rows)
        except Exception:
            document.processing_warning = "Vector index unavailable; keyword fallback active."

        _set_stage(db, document, "linking")
        document.status = "ready"
        if document.processing_stage != "error":
            document.processing_stage = "ready"
        db.commit()
        db.refresh(document)

        _rebuild_links(db, document.user_id, document.id)
        return document
    except Exception as e:
        db.rollback()
        document.status = "error"
        document.processing_stage = "error"
        document.error_message = str(e)[:500] or "Document processing failed."
        db.commit()
        return document
```

Keep `chunk_text`, `_rebuild_links`, `extract_text`, `detect_file_type` unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: `PASSED: 34+ FAILED: 0` (existing 34 green; remove the temporary probe before committing, or keep it only if Task 4 has landed — Task 4 owns the permanent regression block).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ingestion.py
git commit -m "feat: staged ingestion with warning and error signals"
```

---

### Task 3: Upload hardening and retry endpoint

**Files:**
- Modify: `backend/app/routers/documents.py`

**Interfaces:**
- Consumes: `ingestion.detect_file_type/extract_text`, staged `ingest_document` from Task 2, `settings.MAX_UPLOAD_MB`, `BackgroundTasks`.
- Produces: hardened `POST /api/documents/upload` (early 413, empty-file 400, sanitized filename, orphan cleanup); `POST /api/documents/{doc_id}/retry` (error-only re-queue, 409/404 semantics) returning `schemas.DocumentOut`.

- [ ] **Step 1: Write the failing test**

Using the Task 4 regression block (or a scratch script): upload with filename `../../evil.txt` and assert the stored `file_path` stays under `UPLOAD_DIR`; `POST /api/documents/{id}/retry` on a ready doc asserts `409`.

```python
r = client.post("/api/documents/upload", files={"file": ("../../evil.txt", b"hello")}, headers=H)
check("traversal filename contained", r.status_code == 201 and ".." not in r.json()["filename"], r.text[:200])
rid = r.json()["id"]
r = client.post(f"/api/documents/{rid}/retry", headers=H)
check("retry on ready -> 409", r.status_code == 409, r.text[:200])
```

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: FAIL — retry route 404s (missing), traversal assertion fails.

- [ ] **Step 2: Run test to verify it fails**

Same run. Expected: FAIL with missing-route / unsafe-name behavior.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/routers/documents.py`:

Imports — extend to:

```python
import os
import re
import uuid

from fastapi import (APIRouter, Depends, HTTPException, UploadFile, File,
                     BackgroundTasks, Request, status)
```

Add helpers after `_ingest_bg`:

```python
def _sanitize_filename(name: str) -> str:
    base = os.path.basename((name or "").strip()) or "untitled"
    base = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base).strip(" .") or "untitled"
    return base[:255]


def _fail_cleanup(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
```

Replace `upload_document` with:

```python
@router.post("/upload", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    background: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes + 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file.")

    filename = _sanitize_filename(file.filename or "untitled")
    file_type = ingestion.detect_file_type(filename)
    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip() or filename

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    try:
        with open(file_path, "wb") as f:
            f.write(data)
    except OSError:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not store file.")

    doc = models.Document(
        user_id=user.id, title=title, filename=filename, file_type=file_type,
        mime_type=file.content_type or "", file_path=file_path,
        size_bytes=len(data), status="processing", processing_stage="queued",
        error_message="", processing_warning="",
    )
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        _fail_cleanup(file_path)
        raise

    try:
        raw_text = ingestion.extract_text(file_type, data, filename)
    except Exception as e:
        doc.status = "error"
        doc.processing_stage = "error"
        doc.error_message = str(e)[:500] or "Extraction failed."
        db.commit()
        db.refresh(doc)
        return doc
    background.add_task(_ingest_bg, doc.id, raw_text)
    return doc
```

Also set the same three defaults on `create_note`'s `models.Document(...)`:
`status="processing", processing_stage="queued", error_message="", processing_warning=""`.

Add the retry route after `get_document_file` (before `update_document`):

```python
@router.post("/{doc_id}/retry", response_model=schemas.DocumentOut)
def retry_document(
    doc_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = _get_doc(db, user.id, doc_id)
    if doc.status != "error":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only failed documents can be retried.")
    doc.status = "processing"
    doc.processing_stage = "queued"
    doc.error_message = ""
    doc.processing_warning = ""
    db.commit()
    db.refresh(doc)

    if doc.file_type == "note":
        raw_text = doc.content_text or ""
    elif doc.file_path and os.path.exists(doc.file_path):
        with open(doc.file_path, "rb") as f:
            raw_text = ingestion.extract_text(doc.file_type, f.read(), doc.filename)
    else:
        doc.status = "error"
        doc.processing_stage = "error"
        doc.error_message = "Original file missing."
        db.commit()
        db.refresh(doc)
        return doc
    background.add_task(_ingest_bg, doc.id, raw_text)
    return doc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: traversal + 409 checks pass; existing suite green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/documents.py
git commit -m "feat: harden upload and add document retry endpoint"
```

---

### Task 4: Regression tests and verification gates

**Files:**
- Modify: `backend/scripts/smoke_test.py`

**Interfaces:**
- Consumes: all Tasks 1–3 behavior.
- Produces: permanent regression block in the smoke script; gates: smoke 34+new green, `npx tsc --noEmit` clean (frontend unchanged).

- [ ] **Step 1: Write the failing test**

Append this block before `print(f"\n{'='*50}...` in `backend/scripts/smoke_test.py`:

```python
# ── Upload reliability regressions ──────────────────────────
r = client.post("/api/documents/upload", files={"file": ("hello.txt", b"hello world")}, headers=H)
check("upload text -> 201 with stage fields", r.status_code == 201 and "processing_stage" in r.json(), r.text[:200])
up_id = r.json()["id"]

r = client.post("/api/documents/upload", files={"file": ("empty.txt", b"")}, headers=H)
check("upload empty -> 400", r.status_code == 400, r.text[:200])

r = client.post("/api/documents/upload", files={"file": ("../../evil.txt", b"hello")}, headers=H)
check("traversal filename sanitized", r.status_code == 201 and ".." not in r.json()["filename"], r.text[:200])

r = client.get(f"/api/documents/{up_id}", headers=H)
check("detail exposes stage fields", "processing_stage" in r.json() and "error_message" in r.json()
      and "processing_warning" in r.json(), str(r.json())[:200])

r = client.post(f"/api/documents/{up_id}/retry", headers=H)
check("retry on ready -> 409", r.status_code == 409, r.text[:200])

r = client.post("/api/documents/no-such-id/retry", headers=H)
check("retry unknown -> 404", r.status_code == 404, r.text[:200])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py` (on code before Tasks 1–3, or by stashing).
Expected: FAIL on stage/retry checks.

- [ ] **Step 3: Wire permanent block (already written in Step 1)**

No production code here — this task only lands the block above (it IS the implementation). Remove any temporary probes from Tasks 2–3 so only this block remains.

- [ ] **Step 4: Run gates to verify everything passes**

Run: `.venv\Scripts\python.exe backend/scripts/smoke_test.py`
Expected: `PASSED: 40 FAILED: 0 / ALL SMOKE TESTS GREEN` (34 existing + 6 new).

Run: `npx tsc --noEmit` with `workdir=frontend`
Expected: clean, no output.

Lint: unavailable — no ESLint config exists and `npm run lint` prompts for interactive setup; no backend linter configured. Record only.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/smoke_test.py
git commit -m "test: cover upload reliability regressions"
```

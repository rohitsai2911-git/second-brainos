"""End-to-end API smoke test — runs the full app in-process against SQLite.

Vector store is unreachable by design here: every router must degrade
gracefully (keyword-search fallback, empty contexts). Verifies all endpoints,
auth flow, ingestion pipeline, RAG chat, flashcards SM-2, study plan, graph.
"""
import os
import struct
import sys
import tempfile
import time
import zlib

os.environ["DATABASE_URL"] = "sqlite:///./smoke.db"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.config import settings, validate_jwt_config  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
from app import models  # noqa: E402

if os.path.exists("smoke.db"):
    os.remove("smoke.db")
Base.metadata.create_all(bind=engine)

client = TestClient(app)
passed, failed = [], []


def check(name: str, cond: bool, extra: str = ""):
    (passed if cond else failed).append(name)
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" — {extra}" if extra and not cond else ""))


# ── Health ────────────────────────────────────────────────────
r = client.get("/api/health")
check("health", r.status_code == 200 and r.json()["status"] == "ok")

# ── JWT prod guard matrix ─────────────────────────────────────
for bad in ("", "dev-secret-change-me-in-production", "x" * 31):
    try:
        validate_jwt_config("production", bad)
        check(f"prod guard rejects {bad[:8]!r}...", False)
    except RuntimeError:
        check(f"prod guard rejects {bad[:8]!r}...", True)
try:
    validate_jwt_config("production", "x" * 32)
    check("prod guard accepts 32-char secret", True)
except RuntimeError:
    check("prod guard accepts 32-char secret", False)
try:
    validate_jwt_config("development", "dev-secret-change-me-in-production")
    check("dev guard tolerates default secret", True)
except RuntimeError:
    check("dev guard tolerates default secret", False)

# ── Auth ──────────────────────────────────────────────────────
r = client.post("/api/auth/register", json={
    "email": "dev@secondbrain.io", "name": "Dev User", "password": "secret123"})
check("register", r.status_code == 201 and "access_token" in r.json(), r.text[:200])
TOKEN = r.json()["access_token"]
H = {"Authorization": f"Bearer {TOKEN}"}

r = client.post("/api/auth/register", json={
    "email": "dev@secondbrain.io", "name": "Dup", "password": "secret123"})
check("register duplicate -> 409", r.status_code == 409)

r = client.post("/api/auth/login", json={
    "email": "dev@secondbrain.io", "password": "wrongpass"})
check("login bad password -> 401", r.status_code == 401)

r = client.post("/api/auth/login", json={
    "email": "dev@secondbrain.io", "password": "secret123"})
check("login", r.status_code == 200)

r = client.get("/api/auth/me", headers=H)
check("me", r.status_code == 200 and r.json()["email"] == "dev@secondbrain.io")

r = client.get("/api/auth/me")
check("me unauthenticated -> 401", r.status_code == 401)

# ── Notes (full ingestion pipeline) ───────────────────────────
note_body = {
    "title": "Transformer Architecture",
    "content": (
        "The transformer architecture revolutionized natural language processing. "
        "Self-attention allows every token to attend to every other token in parallel. "
        "Multi-head attention projects queries, keys and values into separate subspaces. "
        "Positional encodings inject order information because attention is permutation invariant. "
        "The encoder stack refines representations while the decoder generates output tokens autoregressively. "
        "Scaling laws show that loss decreases predictably with model size, dataset size and compute. "
        "Fine-tuning adapts pretrained weights to downstream tasks with small labeled datasets."
    ),
}
r = client.post("/api/documents/notes", json=note_body, headers=H)
check("create note -> 201 processing", r.status_code == 201, r.text[:200])
doc_id = r.json()["id"]

r = client.get(f"/api/documents/{doc_id}", headers=H)
d = r.json()
check("note ingested (ready+summary+tags+chunks)",
      d["status"] == "ready" and len(d["summary"]) > 10 and isinstance(d["tags"], list),
      str(d)[:300])

r = client.patch(f"/api/documents/{doc_id}", json={"title": "Transformers", "tags": ["ml", "nlp"]}, headers=H)
check("update document", r.status_code == 200 and r.json()["title"] == "Transformers")

# Second note for graph edge
client.post("/api/documents/notes", json={
    "title": "Attention Is All You Need — Reading Notes",
    "content": ("Notes on self-attention mechanisms in the transformer architecture. "
                "Queries keys values scaled dot-product attention. Multi-head projections. "
                "Encoder decoder stacks positional encoding fine-tuning on NLP tasks."),
}, headers=H)

r = client.get("/api/documents", headers=H)
check("list documents (2)", r.status_code == 200 and len(r.json()) == 2)

# ── Search ────────────────────────────────────────────────────
r = client.post("/api/search", json={"query": "attention mechanism", "limit": 5}, headers=H)
check("search returns results", r.status_code == 200 and len(r.json()) >= 1, r.text[:200])

# ── Chat / RAG / memory ───────────────────────────────────────
r = client.post("/api/chat", json={"message": "remember that my goal is to master ML interviews"}, headers=H)
check("chat turn 1", r.status_code == 200 and r.json()["message"]["role"] == "assistant", r.text[:200])
conv_id = r.json()["conversation_id"]

r = client.post("/api/chat", json={"message": "What do my notes say about transformers?",
                                   "conversation_id": conv_id}, headers=H)
check("chat turn 2 with history", r.status_code == 200 and
      r.json()["message"]["content"], r.text[:200])

r = client.get("/api/chat/memories", headers=H)
check("memory extracted", r.status_code == 200 and len(r.json()) >= 1, r.text[:200])

r = client.get("/api/chat/conversations", headers=H)
check("list conversations", r.status_code == 200 and len(r.json()) == 1)

r = client.get(f"/api/chat/conversations/{conv_id}", headers=H)
check("conversation detail (4 msgs)", r.status_code == 200 and len(r.json()["messages"]) == 4)

# ── Flashcards + SM-2 ─────────────────────────────────────────
r = client.post("/api/flashcards/generate",
                json={"document_id": doc_id, "count": 5}, headers=H)
check("generate deck", r.status_code == 201 and len(r.json()["cards"]) >= 3, r.text[:300])
deck_id = r.json()["id"]
card_id = r.json()["cards"][0]["id"]

r = client.get("/api/flashcards/decks", headers=H)
check("list decks (due counted)", r.status_code == 200 and r.json()[0]["due_count"] >= 1)

r = client.get(f"/api/flashcards/decks/{deck_id}/due", headers=H)
check("due cards", r.status_code == 200 and len(r.json()) >= 1)

r = client.post(f"/api/flashcards/cards/{card_id}/review", json={"quality": 4}, headers=H)
c = r.json()
check("SM-2 review q=4 -> reps=1 interval=1", r.status_code == 200 and
      c["repetitions"] == 1 and c["interval_days"] == 1, str(c)[:200])

r = client.post(f"/api/flashcards/cards/{card_id}/review", json={"quality": 5}, headers=H)
c = r.json()
check("SM-2 review q=5 -> interval=6", c["repetitions"] == 2 and c["interval_days"] == 6, str(c)[:200])

# ── Tasks + study plan ────────────────────────────────────────
r = client.post("/api/tasks", json={"title": "Review attention math", "priority": "high"}, headers=H)
check("create task", r.status_code == 201)
task_id = r.json()["id"]

r = client.patch(f"/api/tasks/{task_id}", json={"status": "done"}, headers=H)
check("update task", r.status_code == 200 and r.json()["status"] == "done")

r = client.post("/api/tasks/study-plan",
                json={"goal": "Master transformer architectures", "days": 5, "hours_per_day": 2},
                headers=H)
plan = r.json()
check("study plan -> 5 dated tasks", r.status_code == 201 and len(plan) == 5 and
      all(t["source"] == "ai_plan" for t in plan) and plan[0]["due_date"], r.text[:300])

r = client.delete(f"/api/tasks/{task_id}", headers=H)
check("delete task", r.status_code == 204)

# ── Graph ─────────────────────────────────────────────────────
r = client.get("/api/graph", headers=H)
g = r.json()
check("graph nodes (2 ready docs)", r.status_code == 200 and len(g["nodes"]) == 2, str(g)[:200])
check("graph node shape", g["nodes"][0].get("label") and "file_type" in g["nodes"][0])

# ── Explain code endpoint ─────────────────────────────────────
r = client.post(f"/api/documents/{doc_id}/explain", headers=H)
check("explain endpoint responds", r.status_code == 200 and "explanation" in r.json())

# ── Stats ─────────────────────────────────────────────────────
r = client.get("/api/stats", headers=H)
s = r.json()
check("stats aggregates", r.status_code == 200 and s["total_documents"] == 2 and
      s["total_flashcards"] >= 3 and s["completed_tasks"] == 0 and
      s["total_memories"] >= 1 and len(s["recent_documents"]) == 2, r.text[:300])

# ── Delete cascade ────────────────────────────────────────────
r = client.delete(f"/api/documents/{doc_id}", headers=H)
check("delete document", r.status_code == 204)
r = client.get("/api/stats", headers=H)
check("cascade: stats reflect deletion", r.json()["total_documents"] == 1)
r = client.get(f"/api/documents/{doc_id}", headers=H)
check("deleted doc -> 404", r.status_code == 404)

r = client.delete(f"/api/chat/conversations/{conv_id}", headers=H)
check("delete conversation", r.status_code == 204)

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

# ── Upload reliability: binary types, delete, retry roundtrip, size cap ──
def _make_pdf() -> bytes:
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length 60 >>\nstream\nBT /F1 14 Tf 20 50 Td "
        b"(Smoke PDF about attention) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = [b"%PDF-1.4\n"]
    offsets = [0]
    for i, body in enumerate(objs, 1):
        offsets.append(sum(len(x) for x in out))
        out.append(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = sum(len(x) for x in out)
    out.append(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        out.append(f"{off:010d} 00000 n \n".encode())
    out.append(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
               f"startxref\n{xref}\n%%EOF".encode())
    return b"".join(out)


def _make_png() -> bytes:
    def chunk(ctype: bytes, payload: bytes) -> bytes:
        c = struct.pack(">I", len(payload)) + ctype + payload
        return c + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes([255, 0, 0]) * 4 for _ in range(4))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _wait_ready(doc_id: str, timeout_s: int = 20) -> dict:
    doc: dict = {}
    for _ in range(timeout_s):
        doc = client.get(f"/api/documents/{doc_id}", headers=H).json()
        if doc.get("status") in ("ready", "error"):
            return doc
        time.sleep(1)
    return doc


r = client.post("/api/documents/upload", files={"file": ("smoke.pdf", _make_pdf())}, headers=H)
check("upload pdf -> 201 typed", r.status_code == 201 and r.json()["file_type"] == "pdf", r.text[:200])
pdf_id = r.json()["id"]
d = _wait_ready(pdf_id)
check("pdf ready + text extracted", d.get("status") == "ready" and "attention" in (d.get("content_text") or ""),
      str(d)[:200])

r = client.post("/api/documents/upload", files={"file": ("red.png", _make_png())}, headers=H)
check("upload image -> 201 typed", r.status_code == 201 and r.json()["file_type"] == "image", r.text[:200])
img_id = r.json()["id"]
check("image ready", _wait_ready(img_id).get("status") == "ready")

r = client.delete(f"/api/documents/{img_id}", headers=H)
check("delete uploaded doc -> 204", r.status_code == 204, r.text[:200])
r = client.get(f"/api/documents/{img_id}", headers=H)
check("deleted upload -> 404", r.status_code == 404, r.text[:200])

db = SessionLocal()
db.query(models.Document).filter(models.Document.id == pdf_id).update(
    {"status": "error", "processing_stage": "error", "error_message": "simulated failure"})
db.commit()
db.close()
r = client.post(f"/api/documents/{pdf_id}/retry", headers=H)
check("retry on error accepted", r.status_code == 200 and r.json()["status"] == "processing", r.text[:200])
d = _wait_ready(pdf_id)
check("retry roundtrip -> ready, error cleared",
      d.get("status") == "ready" and not d.get("error_message"), str(d)[:200])

old_cap, settings.MAX_UPLOAD_MB = settings.MAX_UPLOAD_MB, 1
try:
    r = client.post("/api/documents/upload", files={"file": ("big.bin", b"x" * 2 * 1024 * 1024)}, headers=H)
    check("upload over cap -> 413", r.status_code == 413, r.text[:200])
finally:
    settings.MAX_UPLOAD_MB = old_cap

print(f"\n{'='*50}\nPASSED: {len(passed)}  FAILED: {len(failed)}")
if failed:
    print("FAILURES:", ", ".join(failed))
    sys.exit(1)
print("ALL SMOKE TESTS GREEN")

"""End-to-end API smoke test — runs the full app in-process against SQLite.

Vector store is unreachable by design here: every router must degrade
gracefully (keyword-search fallback, empty contexts). Verifies all endpoints,
auth flow, ingestion pipeline, RAG chat, flashcards SM-2, study plan, graph.
"""
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///./smoke.db"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()
os.environ["QDRANT_HOST"] = "localhost"
os.environ["QDRANT_PORT"] = "6333"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import Base, engine  # noqa: E402

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

print(f"\n{'='*50}\nPASSED: {len(passed)}  FAILED: {len(failed)}")
if failed:
    print("FAILURES:", ", ".join(failed))
    sys.exit(1)
print("ALL SMOKE TESTS GREEN")

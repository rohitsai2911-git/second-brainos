"""Seed rich demo data into the running preview backend."""
import httpx
import time

BASE = "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=60)

# Register demo user
r = c.post("/api/auth/register", json={
    "email": "demo@secondbrain.io", "name": "Rohit Sai", "password": "demo1234"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
print("registered")

notes = [
    ("Transformer Architecture Deep Dive",
     "The transformer architecture replaced recurrence with self-attention. Every token attends to "
     "every other token in parallel, enabling massive training throughput on modern accelerators. "
     "Multi-head attention projects queries, keys and values into separate subspaces so the model can "
     "capture different relationship types simultaneously. Positional encodings inject order because "
     "attention is permutation invariant. The encoder stack builds contextual representations while the "
     "decoder generates output tokens autoregressively with causal masking. Scaling laws show test loss "
     "falls predictably with parameters, data and compute, which drove the shift to large pretrained "
     "models. Fine-tuning then adapts pretrained weights to downstream tasks efficiently."),
    ("System Design Interview Notes",
     "Distributed systems interviews test tradeoff reasoning more than memorized answers. Start with "
     "requirements estimation: QPS, storage growth, read-write ratio. Load balancers spread traffic; "
     "consistent hashing minimizes reshuffling when nodes join or leave. Replication provides fault "
     "tolerance but introduces consistency questions. CAP theory frames the choice between consistency "
     "and availability during partitions. Caching with Redis cuts latency but demands invalidation "
     "strategy. Sharding scales writes but complicates cross-shard queries. Always close with bottlenecks: "
     "hot partitions, cache stampedes, retry storms."),
    ("Behavioral Interview Prep — STAR Stories",
     "Structure every answer as Situation, Task, Action, Result. Keep the situation to two sentences and "
     "spend most time on actions you personally took. Quantify results: latency reduced 40 percent, "
     "onboarding time cut from two weeks to three days. Prepare eight core stories covering conflict, "
     "failure, leadership, ambiguity, technical challenge, and impact. Practice aloud; delivery matters "
     "as much as content. Remember that my goal is to land a senior backend role."),
    ("Python Concurrency Cheat Sheet",
     "Threads for IO-bound work — the GIL releases during syscalls. Processes for CPU-bound work since "
     "each has its own interpreter. asyncio for massive concurrent sockets with coroutines and an event "
     "loop. multiprocessing.Pool maps work across cores. Use queue.Queue for thread-safe handoffs and "
     "asyncio.Queue inside event loops. Locks protect shared state but invite deadlocks; prefer message "
     "passing. concurrent.futures gives a unified interface over both executors with clean cancellation."),
    ("RAG Systems Design",
     "Retrieval augmented generation grounds LLM answers in private documents. Pipeline: ingest, chunk "
     "with overlap, embed each chunk, store vectors in Qdrant with metadata filters per user. At query "
     "time embed the question and retrieve top-k by cosine similarity. Rerank if precision matters. "
     "Stuff retrieved context into the prompt with citation instructions. Guardrails: refuse when "
     "retrieval confidence is low, dedupe near-identical chunks, log sources for auditability. Chunk size "
     "trades recall against context budget; overlap preserves boundary facts."),
]

ids = []
for title, body in notes:
    r = c.post("/api/documents/notes", json={"title": title, "content": body}, headers=h)
    ids.append(r.json()["id"])
    print("note:", title)

# Chat conversation
r = c.post("/api/chat", headers=h, json={
    "message": "remember that my goal is to master system design and ML interviews"})
conv = r.json()["conversation_id"]
c.post("/api/chat", headers=h, json={
    "message": "How do transformers relate to attention mechanisms?",
    "conversation_id": conv})
print("chat done")

# Flashcards from two docs
for did in ids[:2]:
    c.post("/api/flashcards/generate", headers=h, json={"document_id": did, "count": 6})
print("decks done")

# Tasks + study plan
c.post("/api/tasks", headers=h, json={
    "title": "Update resume with Second Brain OS project",
    "description": "Add architecture diagram and metrics",
    "priority": "high", "due_date": "2026-08-28"})
c.post("/api/tasks", headers=h, json={
    "title": "Review SM-2 algorithm implementation", "priority": "medium"})
c.post("/api/tasks/study-plan", headers=h, json={
    "goal": "Master transformer architectures and system design", "days": 5, "hours_per_day": 2})
print("tasks done")
print("SEED COMPLETE")

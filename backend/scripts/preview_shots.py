"""Preview automation: seed data, log in, capture screenshots of every page."""
import os
import sys
import time

import httpx
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = r"C:\Users\rohit\AppData\Local\Temp\opencode\sbos_preview"
os.makedirs(OUT, exist_ok=True)

# ── wait for backend ──────────────────────────────────────────
for _ in range(60):
    try:
        if httpx.get(f"{BASE}/api/health", timeout=2).json().get("status") == "ok":
            break
    except Exception:
        time.sleep(1)
else:
    sys.exit("backend never came up")

# ── seed ──────────────────────────────────────────────────────
sys.path.insert(0, r"C:\Users\rohit\secondbrainosforjob\backend")
c = httpx.Client(base_url=BASE, timeout=60)
r = c.post("/api/auth/register", json={
    "email": "demo@secondbrain.io", "name": "Rohit Sai", "password": "demo1234"})
if r.status_code == 409:
    r = c.post("/api/auth/login", json={
        "email": "demo@secondbrain.io", "password": "demo1234"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

docs = c.get("/api/documents", headers=h).json()
if not docs:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "seed", r"C:\Users\rohit\secondbrainosforjob\backend\scripts\seed_demo.py")
    # seed_demo registers its own user; instead inline minimal re-seed below
    notes = [
        ("Transformer Architecture Deep Dive",
         "The transformer architecture replaced recurrence with self-attention. Every token attends to "
         "every other token in parallel, enabling massive training throughput. Multi-head attention "
         "projects queries, keys and values into separate subspaces capturing different relationship "
         "types simultaneously. Positional encodings inject order because attention is permutation "
         "invariant. Scaling laws show loss falls predictably with parameters, data and compute."),
        ("System Design Interview Notes",
         "Distributed systems interviews test tradeoff reasoning. Start with requirements estimation: "
         "QPS, storage growth, read-write ratio. Consistent hashing minimizes reshuffling on node joins. "
         "CAP theory frames consistency versus availability during partitions. Caching with Redis cuts "
         "latency but demands invalidation strategy. Always close with bottlenecks: hot partitions and "
         "cache stampedes."),
        ("Behavioral Interview Prep - STAR Stories",
         "Structure every answer as Situation, Task, Action, Result. Quantify results: latency reduced "
         "40 percent. Prepare eight core stories covering conflict, failure, leadership and ambiguity. "
         "Remember that my goal is to land a senior backend role."),
        ("Python Concurrency Cheat Sheet",
         "Threads for IO-bound work since the GIL releases during syscalls. Processes for CPU-bound "
         "work. asyncio for massive concurrent sockets with an event loop. queue.Queue for thread-safe "
         "handoffs. Locks protect shared state but invite deadlocks; prefer message passing."),
        ("RAG Systems Design",
         "Retrieval augmented generation grounds LLM answers in private documents. Pipeline: chunk with "
         "overlap, embed each chunk, store vectors in Qdrant with per-user metadata filters. Retrieve "
         "top-k by cosine similarity at query time. Refuse when retrieval confidence is low, dedupe "
         "near-identical chunks, log sources for auditability."),
    ]
    ids = []
    for t, b in notes:
        ids.append(c.post("/api/documents/notes", json={"title": t, "content": b}, headers=h).json()["id"])
    c.post("/api/chat", headers=h, json={
        "message": "remember that my goal is to master system design and ML interviews"})
    conv_id = c.post("/api/chat", headers=h, json={
        "message": "How do transformers use attention mechanisms?"}).json()["conversation_id"]
    for did in ids[:2]:
        c.post("/api/flashcards/generate", headers=h, json={"document_id": did, "count": 6})
    c.post("/api/tasks", headers=h, json={
        "title": "Update resume with Second Brain OS project",
        "description": "Add architecture diagram and metrics",
        "priority": "high", "due_date": "2026-08-28"})
    c.post("/api/tasks", headers=h, json={
        "title": "Review SM-2 algorithm implementation", "priority": "medium"})
    c.post("/api/tasks/study-plan", headers=h, json={
        "goal": "Master transformer architectures and system design", "days": 5, "hours_per_day": 2})
    docs = c.get("/api/documents", headers=h).json()

doc_id = docs[0]["id"]
print(f"seed ok, {len(docs)} documents")

# ── screenshots ───────────────────────────────────────────────
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    page = ctx.new_page()

    def shot(name, full=False):
        page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
        print("shot:", name)

    # Landing (logged out)
    page.goto("http://localhost:3000")
    page.wait_for_load_state("networkidle")
    shot("01-landing", full=True)

    # Inject auth token, enter app
    page.evaluate(f"localStorage.setItem('sbo_token', '{token}')")

    page.goto("http://localhost:3000/dashboard")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    shot("02-dashboard")

    page.goto("http://localhost:3000/documents")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    shot("03-documents")

    page.goto(f"http://localhost:3000/documents/{doc_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    shot("04-viewer")

    page.goto("http://localhost:3000/search")
    page.wait_for_load_state("networkidle")
    page.fill("input[placeholder*='attention']", "how does attention work")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)
    shot("05-search")

    page.goto("http://localhost:3000/chat")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(800)
    side = page.locator("aside button", has_text="How do transformers")
    if side.count() > 0:
        side.first.click()
        page.wait_for_timeout(1500)
    shot("06-chat")

    page.goto("http://localhost:3000/graph")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3500)
    shot("07-graph")

    page.goto("http://localhost:3000/flashcards")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    review = page.locator("button", has_text="Review (")
    if review.count() > 0:
        review.first.click()
        page.wait_for_timeout(1200)
    shot("08-flashcards")

    page.goto("http://localhost:3000/planner")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    shot("09-planner")

    browser.close()
print("ALL SCREENSHOTS DONE")

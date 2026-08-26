"""LLM service — OpenAI-compatible chat completions with a fully local
fallback engine so the platform works offline / without an API key.

The fallback uses extractive summarization (frequency-scored sentence
selection), template-based flashcards and heuristic planning. When
OPENAI_API_KEY is set, the real LLM is used for everything.
"""
import json
import re
from collections import Counter

from ..config import settings

_client = None


def _get_client():
    global _client
    if _client is None and settings.llm_enabled:
        from openai import OpenAI
        kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL
        _client = OpenAI(**kwargs)
    return _client


def chat(system: str, user: str, temperature: float = 0.3, max_tokens: int = 1500) -> str | None:
    """Return LLM completion, or None if no provider is configured."""
    client = _get_client()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


# ── Local fallback helpers ────────────────────────────────────
_STOPWORDS = set("""
a an the and or but if then else for to of in on at by with from as is are was were
be been being it its this that these those i you he she we they them his her their our
your my me him us not no yes do does did done have has had having can could will would
shall should may might must about into over under again further once here there when
where why how all any both each few more most other some such only own same so than too
very just also what which who whom
""".split())


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _keywords(text: str, top: int = 8) -> list[str]:
    words = [w.strip(".,;:!?()[]{}\"'").lower() for w in text.split()]
    words = [w for w in words if len(w) > 3 and w not in _STOPWORDS and w.isalpha()]
    return [w for w, _ in Counter(words).most_common(top)]


def extractive_summary(text: str, max_sentences: int = 4) -> str:
    sents = _sentences(text)
    if not sents:
        return text[:400].strip()
    if len(sents) <= max_sentences:
        return " ".join(sents)
    freq = Counter(w for w in re.findall(r"[a-zA-Z]{4,}", text.lower()) if w not in _STOPWORDS)
    scored = []
    for i, s in enumerate(sents):
        words = re.findall(r"[a-zA-Z]{4,}", s.lower())
        score = sum(freq.get(w, 0) for w in words) / (len(words) + 1)
        score *= 1.0 if i == 0 else 0.9  # slight lead bias
        scored.append((score, i, s))
    best = sorted(scored, reverse=True)[:max_sentences]
    best.sort(key=lambda x: x[1])
    return " ".join(s for _, _, s in best)


def summarize(text: str) -> str:
    llm_out = chat(
        "You are a precise summarizer. Summarize the document in 3-5 sentences.",
        text[:12000],
        max_tokens=400,
    )
    return llm_out or extractive_summary(text)


def auto_tags(text: str, title: str = "") -> list[str]:
    if settings.llm_enabled:
        out = chat(
            'Return ONLY a JSON array of 3-6 short lowercase topic tags for this document. Example: ["ml","python"]',
            f"Title: {title}\n\n{text[:4000]}",
            max_tokens=80,
        )
        if out:
            try:
                tags = json.loads(out[out.index("["):out.rindex("]") + 1])
                return [str(t).lower()[:24] for t in tags][:6]
            except Exception:
                pass
    return _keywords(title + " " + text, top=5)


def answer_question(question: str, contexts: list[dict], memories: list[str]) -> str:
    context_block = "\n\n".join(
        f"[Source: {c['document_title']}]\n{c['text']}" for c in contexts
    ) or "(no relevant documents found)"
    memory_block = "\n".join(f"- {m}" for m in memories) or "(none)"

    llm_out = chat(
        "You are Second Brain, an AI knowledge assistant. Answer the user's question "
        "using ONLY the provided context from their knowledge base. Cite sources by "
        "document title in [brackets]. If the context is insufficient, say so honestly. "
        "Be concise, structured and helpful.\n\n"
        f"Long-term memory about the user:\n{memory_block}",
        f"Context:\n{context_block}\n\nQuestion: {question}",
        max_tokens=900,
    )
    if llm_out:
        return llm_out

    # Local fallback: stitch the most relevant passages
    if not contexts:
        return ("I couldn't find anything relevant in your knowledge base yet. "
                "Upload documents or notes first, then ask again.")
    lines = [f"Based on your knowledge base, here's what I found for **{question}**:\n"]
    for c in contexts[:4]:
        snippet = c["text"][:350].strip()
        lines.append(f"- From **{c['document_title']}**: {snippet}…")
    lines.append("\n*(Local answer mode — set OPENAI_API_KEY for synthesized answers.)*")
    return "\n".join(lines)


def generate_flashcards(text: str, title: str, count: int = 10) -> list[dict]:
    if settings.llm_enabled:
        out = chat(
            "Generate study flashcards from the document. Return ONLY a JSON array of "
            'objects with "front" (question) and "back" (concise answer). '
            f"Create exactly {count} cards covering the key ideas.",
            f"Document: {title}\n\n{text[:12000]}",
            max_tokens=2500,
        )
        if out:
            try:
                cards = json.loads(out[out.index("["):out.rindex("]") + 1])
                return [{"front": str(c["front"]), "back": str(c["back"])}
                        for c in cards if c.get("front") and c.get("back")][:count]
            except Exception:
                pass

    # Local fallback: sentence → cloze-style cards from key sentences
    sents = _sentences(text)
    keywords = _keywords(text, top=max(count, 10))
    cards = []
    for kw in keywords:
        for s in sents:
            if re.search(rf"\b{re.escape(kw)}\b", s, re.IGNORECASE):
                front = re.sub(rf"\b{re.escape(kw)}\b", "______", s, count=1, flags=re.IGNORECASE)
                cards.append({"front": f"Fill in the blank: {front}",
                              "back": f"{kw} — {s}"})
                break
        if len(cards) >= count:
            break
    if not cards and sents:
        cards = [{"front": f"What does \"{title}\" say about: {s[:80]}…?", "back": s}
                 for s in sents[:count]]
    return cards[:count]


def explain_code(code: str, language: str = "") -> str:
    llm_out = chat(
        "You are a senior engineer. Explain what this code does: purpose, key logic, "
        "inputs/outputs, notable patterns, and potential issues. Use markdown.",
        f"Language: {language or 'auto-detect'}\n\n```\n{code[:12000]}\n```",
        max_tokens=1200,
    )
    if llm_out:
        return llm_out
    # Fallback structural analysis
    funcs = re.findall(r"(?:def|function|func|fn)\s+([A-Za-z_][\w]*)", code)
    classes = re.findall(r"class\s+([A-Za-z_][\w]*)", code)
    imports = re.findall(r"(?:import|from|require|include)\s+([\w.]+)", code)
    lines = ["## Code overview (structural analysis)\n"]
    if imports:
        lines.append(f"**Dependencies:** {', '.join(sorted(set(imports))[:12])}")
    if classes:
        lines.append(f"**Classes:** {', '.join(classes[:10])}")
    if funcs:
        lines.append(f"**Functions:** {', '.join(funcs[:15])}")
    lines.append(f"\n**Size:** {len(code.splitlines())} lines, {len(code)} characters.")
    lines.append("\n*Set OPENAI_API_KEY for a full natural-language explanation.*")
    return "\n".join(lines)


def generate_study_plan(goal: str, days: int, hours_per_day: float, context: str = "") -> list[dict]:
    if settings.llm_enabled:
        out = chat(
            "Create a day-by-day study plan. Return ONLY a JSON array of objects with "
            '"day" (int), "title" (short task), "description" (what to do, 1-2 sentences), '
            '"priority" ("low"|"medium"|"high").',
            f"Goal: {goal}\nDays: {days}\nHours per day: {hours_per_day}\n"
            f"Related material:\n{context[:6000]}",
            max_tokens=2500,
        )
        if out:
            try:
                plan = json.loads(out[out.index("["):out.rindex("]") + 1])
                return [{"day": int(p.get("day", i + 1)),
                         "title": str(p.get("title", f"Day {i+1} session")),
                         "description": str(p.get("description", "")),
                         "priority": str(p.get("priority", "medium"))}
                        for i, p in enumerate(plan)]
            except Exception:
                pass

    # Fallback plan: distribute phases across days
    phases = [
        ("Foundations & overview", "Survey the material, skim key sections, note unfamiliar concepts.", "high"),
        ("Deep dive — core concepts", "Study the most important topics in depth; take structured notes.", "high"),
        ("Practice & application", "Work through examples and exercises; generate flashcards for review.", "medium"),
        ("Review & self-test", "Review flashcards, summarize from memory, identify weak spots.", "medium"),
        ("Consolidation", "Revisit weak areas, connect ideas across documents, final recap.", "low"),
    ]
    plan = []
    for d in range(1, days + 1):
        phase = phases[min((d - 1) * len(phases) // max(days, 1), len(phases) - 1)]
        plan.append({"day": d, "title": f"Day {d}: {phase[0]}",
                     "description": f"{phase[1]} (~{hours_per_day}h focused on: {goal})",
                     "priority": phase[2]})
    return plan


def extract_memories(user_message: str) -> list[str]:
    """Detect durable facts/preferences the user states in chat."""
    facts = []
    patterns = [
        r"(?:remember that|remember:)\s+(.+)",
        r"(?:my goal is|i'?m (?:trying|learning|working) (?:to|on))\s+(.+)",
        r"(?:i prefer|i like|i use)\s+(.+)",
    ]
    for p in patterns:
        m = re.search(p, user_message, re.IGNORECASE)
        if m:
            fact = m.group(1).strip().rstrip(".")
            if 8 < len(fact) < 300:
                facts.append(fact)
    return facts[:2]

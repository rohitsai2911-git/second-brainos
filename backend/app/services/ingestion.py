"""Document ingestion pipeline: extract text → chunk → embed → index → link."""
import io
import os
import uuid

from sqlalchemy.orm import Session

from ..config import settings
from .. import models
from . import vectorstore, llm

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".sql", ".sh",
    ".html", ".css", ".scss", ".json", ".yaml", ".yml", ".toml", ".md",
}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".log"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


def detect_file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return "text"


def extract_text(file_type: str, data: bytes, filename: str) -> str:
    """Extract plain text from uploaded bytes."""
    if file_type == "pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            pages = [(p.extract_text() or "") for p in reader.pages]
            return "\n\n".join(pages).strip()
        except Exception:
            return ""
    if file_type == "docx":
        try:
            import docx
            doc = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs).strip()
        except Exception:
            return ""
    if file_type == "image":
        # No OCR dependency — store descriptive placeholder so images are
        # still indexed, searchable by name, and visible in the graph.
        return (f"Image file: {filename}. Visual asset stored in the knowledge base. "
                f"Size: {len(data)} bytes.")
    try:
        return data.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    text = " ".join(text.split())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        # try to break at a sentence/word boundary
        if end < len(text):
            boundary = text.rfind(". ", start + size // 2, end)
            if boundary == -1:
                boundary = text.rfind(" ", start + size // 2, end)
            if boundary != -1:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = max(end - overlap, start + 1)
        if start >= len(text):
            break
    return [c for c in chunks if c]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(x * x for x in b) ** 0.5 or 1.0
    return dot / (na * nb)


def _rebuild_links(db: Session, user_id: str, new_doc_id: str, threshold: float = 0.55) -> None:
    """Connect the new document to its most similar existing documents."""
    try:
        new_vec = vectorstore.document_vector(user_id, new_doc_id)
        if not new_vec:
            return
        others = (db.query(models.Document)
                  .filter(models.Document.user_id == user_id,
                          models.Document.id != new_doc_id,
                          models.Document.status == "ready")
                  .limit(100).all())
        for other in others:
            vec = vectorstore.document_vector(user_id, other.id)
            if not vec:
                continue
            sim = _cosine(new_vec, vec)
            if sim >= threshold:
                db.add(models.DocumentLink(user_id=user_id, source_id=new_doc_id,
                                           target_id=other.id, similarity=round(sim, 4)))
        db.commit()
    except Exception:
        db.rollback()


def ingest_document(db: Session, document: models.Document, raw_text: str) -> models.Document:
    """Full pipeline for one document row already persisted with status=processing."""
    try:
        document.content_text = raw_text[:200_000]
        document.summary = llm.summarize(raw_text) if raw_text else ""
        if not document.tags:
            document.tags = llm.auto_tags(raw_text[:6000], document.title) if raw_text else []

        # chunk + persist
        chunk_texts = chunk_text(raw_text)
        chunk_rows = []
        for i, text in enumerate(chunk_texts):
            row = models.Chunk(id=str(uuid.uuid4()), document_id=document.id,
                               user_id=document.user_id, chunk_index=i, text=text)
            db.add(row)
            chunk_rows.append({"id": row.id, "text": text, "index": i})

        # embed + index in Qdrant
        try:
            vectorstore.upsert_chunks(document.user_id, document.id, document.title,
                                      document.file_type, chunk_rows)
        except Exception:
            pass  # DB rows remain; search will backfill on next ingest

        document.status = "ready"
        db.commit()
        db.refresh(document)

        _rebuild_links(db, document.user_id, document.id)
        return document
    except Exception:
        db.rollback()
        document.status = "error"
        db.commit()
        return document

"""Document ingestion pipeline: extract text → chunk → embed → index → link."""
import io
import os
import uuid

from sqlalchemy.orm import Session

from ..config import settings
from .. import models
from . import vectorstore, llm, embeddings

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


def _doc_probe(document: models.Document) -> str:
    """Compact semantic fingerprint of a document for link computation."""
    tags = " ".join(document.tags or [])
    return f"{document.title} {tags} {document.summary or ''} {document.content_text[:800]}"


def _rebuild_links(db: Session, user_id: str, new_doc_id: str) -> None:
    """Connect the new document to its most similar existing documents.

    Embeds compact document probes directly (works with or without Qdrant).
    Threshold adapts to the embedding backend; at most 4 strongest links kept.
    """
    try:
        new_doc = db.get(models.Document, new_doc_id)
        if not new_doc:
            return
        others = (db.query(models.Document)
                  .filter(models.Document.user_id == user_id,
                          models.Document.id != new_doc_id,
                          models.Document.status == "ready")
                  .limit(100).all())
        if not others:
            return

        new_vec = embeddings.embed_query(_doc_probe(new_doc))
        other_vecs = embeddings.embed_texts([_doc_probe(o) for o in others])

        scored = sorted(
            ((_cosine(new_vec, vec), other) for other, vec in zip(others, other_vecs)),
            key=lambda pair: pair[0], reverse=True,
        )
        floor = 0.55 if embeddings.using_neural_model() else 0.20
        for sim, other in scored[:4]:
            if sim < floor:
                break
            db.add(models.DocumentLink(user_id=user_id, source_id=new_doc_id,
                                       target_id=other.id, similarity=round(sim, 4)))
        db.commit()
    except Exception:
        db.rollback()


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

"""Document routes: upload, notes, list, detail, update, delete, explain-code."""
import os
import uuid

from fastapi import (APIRouter, Depends, HTTPException, UploadFile, File,
                     BackgroundTasks, status)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, SessionLocal
from .. import models, schemas, security
from ..services import ingestion, vectorstore, llm

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_doc(db: Session, user_id: str, doc_id: str) -> models.Document:
    doc = (db.query(models.Document)
           .filter(models.Document.id == doc_id, models.Document.user_id == user_id)
           .first())
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


def _ingest_bg(doc_id: str, raw_text: str) -> None:
    """Background ingestion with its own session."""
    db = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if doc:
            ingestion.ingest_document(db, doc, raw_text)
    finally:
        db.close()


@router.post("/upload", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")

    filename = file.filename or "untitled"
    file_type = ingestion.detect_file_type(filename)
    title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").strip() or filename

    # Persist raw file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(file_path, "wb") as f:
        f.write(data)

    doc = models.Document(
        user_id=user.id, title=title, filename=filename, file_type=file_type,
        mime_type=file.content_type or "", file_path=file_path,
        size_bytes=len(data), status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    raw_text = ingestion.extract_text(file_type, data, filename)
    background.add_task(_ingest_bg, doc.id, raw_text)
    return doc


@router.post("/notes", response_model=schemas.DocumentOut, status_code=201)
def create_note(
    body: schemas.NoteCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = models.Document(
        user_id=user.id, title=body.title, filename=f"{body.title[:40]}.note",
        file_type="note", mime_type="text/plain", size_bytes=len(body.content),
        tags=body.tags, status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background.add_task(_ingest_bg, doc.id, body.content)
    return doc


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    return (db.query(models.Document)
            .filter(models.Document.user_id == user.id)
            .order_by(models.Document.created_at.desc())
            .all())


@router.get("/{doc_id}", response_model=schemas.DocumentDetail)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    return _get_doc(db, user.id, doc_id)


@router.get("/{doc_id}/file")
def get_document_file(
    doc_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = _get_doc(db, user.id, doc_id)
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not available")
    return FileResponse(doc.file_path, media_type=doc.mime_type or "application/octet-stream",
                        filename=doc.filename)


@router.patch("/{doc_id}", response_model=schemas.DocumentOut)
def update_document(
    doc_id: str,
    body: schemas.DocumentUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = _get_doc(db, user.id, doc_id)
    if body.title is not None:
        doc.title = body.title
    if body.tags is not None:
        doc.tags = body.tags
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/{doc_id}/explain")
def explain_document_code(
    doc_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = _get_doc(db, user.id, doc_id)
    if not doc.content_text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Document has no extracted content")
    explanation = llm.explain_code(doc.content_text, doc.file_type)
    return {"document_id": doc.id, "title": doc.title, "explanation": explanation}


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = _get_doc(db, user.id, doc_id)
    try:
        vectorstore.delete_document(doc.id)
    except Exception:
        pass
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
    db.query(models.DocumentLink).filter(
        (models.DocumentLink.source_id == doc.id) | (models.DocumentLink.target_id == doc.id)
    ).delete(synchronize_session=False)
    db.delete(doc)
    db.commit()
    return None

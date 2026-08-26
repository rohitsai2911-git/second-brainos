"""Semantic search across the user's knowledge base."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security
from ..services import vectorstore

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=list[schemas.SearchResult])
def semantic_search(
    body: schemas.SearchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    try:
        results = vectorstore.search(user.id, body.query, limit=body.limit)
    except Exception:
        results = []

    # Fallback: keyword search in Postgres when vector store is empty/unavailable
    if not results:
        like = f"%{body.query}%"
        docs = (db.query(models.Document)
                .filter(models.Document.user_id == user.id,
                        models.Document.content_text.ilike(like))
                .limit(body.limit).all())
        results = [{
            "chunk_id": "",
            "document_id": d.id,
            "document_title": d.title,
            "file_type": d.file_type,
            "text": d.content_text[:500],
            "score": 0.5,
        } for d in docs]

    # De-duplicate by chunk, keep order
    seen, out = set(), []
    for r in results:
        key = r["chunk_id"] or r["document_id"]
        if key in seen:
            continue
        seen.add(key)
        out.append(schemas.SearchResult(**r))
    return out

"""Dashboard statistics."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=schemas.StatsOut)
def get_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    docs = db.query(models.Document).filter(models.Document.user_id == user.id).all()
    total_chunks = (db.query(func.count(models.Chunk.id))
                    .filter(models.Chunk.user_id == user.id).scalar() or 0)
    total_cards = (db.query(func.count(models.Flashcard.id))
                   .join(models.FlashcardDeck)
                   .filter(models.FlashcardDeck.user_id == user.id).scalar() or 0)
    now = datetime.utcnow()
    due_cards = (db.query(func.count(models.Flashcard.id))
                 .join(models.FlashcardDeck)
                 .filter(models.FlashcardDeck.user_id == user.id,
                         models.Flashcard.due_at <= now).scalar() or 0)
    tasks = db.query(models.Task).filter(models.Task.user_id == user.id).all()
    memories = (db.query(func.count(models.Memory.id))
                .filter(models.Memory.user_id == user.id).scalar() or 0)
    links = (db.query(func.count(models.DocumentLink.id))
             .filter(models.DocumentLink.user_id == user.id).scalar() or 0)

    tag_counts: dict[str, int] = {}
    for d in docs:
        for t in (d.tags or []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:8]

    recent = sorted(docs, key=lambda d: d.created_at, reverse=True)[:5]

    return schemas.StatsOut(
        total_documents=len(docs),
        total_chunks=total_chunks,
        total_flashcards=total_cards,
        due_flashcards=due_cards,
        total_tasks=len(tasks),
        completed_tasks=sum(1 for t in tasks if t.status == "done"),
        total_memories=memories,
        total_links=links,
        total_size_bytes=sum(d.size_bytes or 0 for d in docs),
        top_tags=top_tags,
        recent_documents=[schemas.DocumentOut.model_validate(d) for d in recent],
    )

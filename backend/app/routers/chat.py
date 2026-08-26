"""AI chat with RAG + long-term memory."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security
from ..services import vectorstore, llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    return (db.query(models.Conversation)
            .filter(models.Conversation.user_id == user.id)
            .order_by(models.Conversation.created_at.desc())
            .all())


@router.get("/conversations/{conv_id}", response_model=schemas.ConversationDetail)
def get_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    conv = (db.query(models.Conversation)
            .filter(models.Conversation.id == conv_id,
                    models.Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    conv = (db.query(models.Conversation)
            .filter(models.Conversation.id == conv_id,
                    models.Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()
    return None


@router.post("", response_model=schemas.ChatResponse)
def chat(
    body: schemas.ChatRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    # Get or create conversation
    if body.conversation_id:
        conv = (db.query(models.Conversation)
                .filter(models.Conversation.id == body.conversation_id,
                        models.Conversation.user_id == user.id)
                .first())
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        title = body.message[:60] + ("…" if len(body.message) > 60 else "")
        conv = models.Conversation(user_id=user.id, title=title)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Persist user message
    user_msg = models.Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)

    # Long-term memory: extract + load
    for fact in llm.extract_memories(body.message):
        db.add(models.Memory(user_id=user.id, kind="fact", content=fact))
    memories = [m.content for m in
                db.query(models.Memory).filter(models.Memory.user_id == user.id)
                .order_by(models.Memory.created_at.desc()).limit(20).all()]

    # RAG retrieval
    try:
        contexts = vectorstore.search(user.id, body.message, limit=6)
    except Exception:
        contexts = []

    answer = llm.answer_question(body.message, contexts, memories)

    sources = [{
        "document_id": c["document_id"],
        "document_title": c["document_title"],
        "chunk_id": c["chunk_id"],
        "score": round(c["score"], 3),
        "snippet": c["text"][:220],
    } for c in contexts[:5]]

    assistant_msg = models.Message(conversation_id=conv.id, role="assistant",
                                   content=answer, sources=sources)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return schemas.ChatResponse(
        conversation_id=conv.id,
        message=schemas.MessageOut.model_validate(assistant_msg),
    )


@router.get("/memories", response_model=list[schemas.MemoryOut])
def list_memories(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    return (db.query(models.Memory)
            .filter(models.Memory.user_id == user.id)
            .order_by(models.Memory.created_at.desc())
            .limit(50).all())


@router.delete("/memories/{memory_id}", status_code=204)
def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    mem = (db.query(models.Memory)
           .filter(models.Memory.id == memory_id, models.Memory.user_id == user.id)
           .first())
    if not mem:
        raise HTTPException(404, "Memory not found")
    db.delete(mem)
    db.commit()
    return None

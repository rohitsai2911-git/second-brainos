"""Flashcard decks: AI generation, listing, SM-2 review."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, security
from ..services import llm, spaced_repetition

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


def _deck_out(db: Session, deck: models.FlashcardDeck) -> schemas.DeckOut:
    now = datetime.utcnow()
    cards = deck.cards
    due = sum(1 for c in cards if c.due_at <= now)
    return schemas.DeckOut(
        id=deck.id, title=deck.title, document_id=deck.document_id,
        created_at=deck.created_at, card_count=len(cards), due_count=due,
    )


@router.get("/decks", response_model=list[schemas.DeckOut])
def list_decks(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    decks = (db.query(models.FlashcardDeck)
             .filter(models.FlashcardDeck.user_id == user.id)
             .order_by(models.FlashcardDeck.created_at.desc()).all())
    return [_deck_out(db, d) for d in decks]


@router.post("/generate", response_model=schemas.DeckDetail, status_code=201)
def generate_deck(
    body: schemas.GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    doc = (db.query(models.Document)
           .filter(models.Document.id == body.document_id,
                   models.Document.user_id == user.id)
           .first())
    if not doc:
        raise HTTPException(404, "Document not found")
    if not doc.content_text:
        raise HTTPException(400, "Document has no content to generate cards from")

    cards_data = llm.generate_flashcards(doc.content_text, doc.title, body.count)
    if not cards_data:
        raise HTTPException(422, "Could not generate flashcards from this document")

    deck = models.FlashcardDeck(user_id=user.id, document_id=doc.id,
                                title=f"{doc.title} — Flashcards")
    db.add(deck)
    db.flush()
    for c in cards_data:
        db.add(models.Flashcard(deck_id=deck.id, front=c["front"], back=c["back"]))
    db.commit()
    db.refresh(deck)

    out = _deck_out(db, deck)
    return schemas.DeckDetail(**out.model_dump(),
                              cards=[schemas.FlashcardOut.model_validate(c) for c in deck.cards])


@router.get("/decks/{deck_id}", response_model=schemas.DeckDetail)
def get_deck(
    deck_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    deck = (db.query(models.FlashcardDeck)
            .filter(models.FlashcardDeck.id == deck_id,
                    models.FlashcardDeck.user_id == user.id)
            .first())
    if not deck:
        raise HTTPException(404, "Deck not found")
    out = _deck_out(db, deck)
    return schemas.DeckDetail(**out.model_dump(),
                              cards=[schemas.FlashcardOut.model_validate(c) for c in deck.cards])


@router.get("/decks/{deck_id}/due", response_model=list[schemas.FlashcardOut])
def due_cards(
    deck_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    deck = (db.query(models.FlashcardDeck)
            .filter(models.FlashcardDeck.id == deck_id,
                    models.FlashcardDeck.user_id == user.id)
            .first())
    if not deck:
        raise HTTPException(404, "Deck not found")
    now = datetime.utcnow()
    return [c for c in deck.cards if c.due_at <= now]


@router.post("/cards/{card_id}/review", response_model=schemas.FlashcardOut)
def review_card(
    card_id: str,
    body: schemas.ReviewRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    card = (db.query(models.Flashcard)
            .join(models.FlashcardDeck)
            .filter(models.Flashcard.id == card_id,
                    models.FlashcardDeck.user_id == user.id)
            .first())
    if not card:
        raise HTTPException(404, "Card not found")
    spaced_repetition.review(card, body.quality)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/decks/{deck_id}", status_code=204)
def delete_deck(
    deck_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    deck = (db.query(models.FlashcardDeck)
            .filter(models.FlashcardDeck.id == deck_id,
                    models.FlashcardDeck.user_id == user.id)
            .first())
    if not deck:
        raise HTTPException(404, "Deck not found")
    db.delete(deck)
    db.commit()
    return None

"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import (Column, String, Text, DateTime, ForeignKey, Integer,
                        Float, Boolean, JSON)
from sqlalchemy.orm import relationship

from .database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")
    flashcard_decks = relationship("FlashcardDeck", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)          # pdf | note | code | image | docx | text
    mime_type = Column(String, default="")
    file_path = Column(String, default="")
    size_bytes = Column(Integer, default=0)
    content_text = Column(Text, default="")             # extracted full text
    summary = Column(Text, default="")
    tags = Column(JSON, default=list)
    status = Column(String, default="ready")            # processing | ready | error
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=gen_id)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id = Column(String, index=True)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, default="")

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String, default="New conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_id)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role = Column(String, nullable=False)               # user | assistant
    content = Column(Text, default="")
    sources = Column(JSON, default=list)                # [{document_id, title, chunk_id, score}]
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="flashcard_decks")
    cards = relationship("Flashcard", back_populates="deck", cascade="all, delete-orphan")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(String, primary_key=True, default=gen_id)
    deck_id = Column(String, ForeignKey("flashcard_decks.id", ondelete="CASCADE"), index=True)
    front = Column(Text, default="")
    back = Column(Text, default="")
    ease = Column(Float, default=2.5)                   # SM-2 ease factor
    interval_days = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    due_at = Column(DateTime, default=datetime.utcnow)

    deck = relationship("FlashcardDeck", back_populates="cards")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="todo")             # todo | in_progress | done
    priority = Column(String, default="medium")         # low | medium | high
    due_date = Column(String, default="")
    source = Column(String, default="manual")           # manual | ai_plan
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="tasks")


class Memory(Base):
    """Long-term memory: facts the assistant learns about the user."""
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind = Column(String, default="fact")               # fact | preference | goal
    content = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="memories")


class DocumentLink(Base):
    """Knowledge-graph edge between two related documents."""
    __tablename__ = "document_links"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, index=True)
    source_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"))
    target_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"))
    similarity = Column(Float, default=0.0)

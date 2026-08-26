"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Documents ─────────────────────────────────────────────────
class DocumentOut(BaseModel):
    id: str
    title: str
    filename: str
    file_type: str
    mime_type: str
    size_bytes: int
    summary: str
    tags: list[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetail(DocumentOut):
    content_text: str


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = ""
    tags: list[str] = []


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[list[str]] = None


# ── Search ────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    file_type: str
    text: str
    score: float


# ── Chat ──────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: Optional[str] = None


class SourceOut(BaseModel):
    document_id: str
    document_title: str
    chunk_id: str
    score: float
    snippet: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ChatResponse(BaseModel):
    conversation_id: str
    message: MessageOut


# ── Flashcards ────────────────────────────────────────────────
class FlashcardOut(BaseModel):
    id: str
    front: str
    back: str
    ease: float
    interval_days: int
    repetitions: int
    due_at: datetime

    class Config:
        from_attributes = True


class DeckOut(BaseModel):
    id: str
    title: str
    document_id: Optional[str]
    created_at: datetime
    card_count: int = 0
    due_count: int = 0


class DeckDetail(DeckOut):
    cards: list[FlashcardOut] = []


class GenerateFlashcardsRequest(BaseModel):
    document_id: str
    count: int = Field(default=10, ge=3, le=40)


class ReviewRequest(BaseModel):
    quality: int = Field(ge=0, le=5)  # SM-2 quality score


# ── Tasks / Planner ───────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    priority: str = "medium"
    due_date: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    priority: str
    due_date: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudyPlanRequest(BaseModel):
    goal: str = Field(min_length=3)
    days: int = Field(default=7, ge=1, le=60)
    hours_per_day: float = Field(default=2.0, ge=0.5, le=12)
    document_id: Optional[str] = None


# ── Graph ─────────────────────────────────────────────────────
class GraphNode(BaseModel):
    id: str
    label: str
    file_type: str
    summary: str
    tags: list[str]


class GraphEdge(BaseModel):
    source: str
    target: str
    similarity: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Memory ────────────────────────────────────────────────────
class MemoryOut(BaseModel):
    id: str
    kind: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Stats ─────────────────────────────────────────────────────
class StatsOut(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    total_flashcards: int = 0
    due_flashcards: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    total_memories: int = 0
    total_links: int = 0
    total_size_bytes: int = 0
    top_tags: list[str] = []
    recent_documents: list[DocumentOut] = []


TokenResponse.model_rebuild()

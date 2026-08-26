"""Qdrant vector store service — collection management, upsert, search, delete."""
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, VectorParams, PointStruct,
                                  Filter, FieldCondition, MatchValue)

from ..config import settings
from . import embeddings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


def ensure_collection() -> None:
    client = get_client()
    name = settings.QDRANT_COLLECTION
    try:
        existing = {c.name for c in client.get_collections().collections}
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=embeddings.dimension(), distance=Distance.COSINE),
            )
    except Exception:
        # Qdrant not reachable yet — operations will retry lazily
        pass


def upsert_chunks(user_id: str, document_id: str, title: str,
                  file_type: str, chunks: list[dict]) -> None:
    """chunks: [{id, text, index}]"""
    if not chunks:
        return
    client = get_client()
    ensure_collection()
    vectors = embeddings.embed_texts([c["text"] for c in chunks])
    points = []
    for chunk, vector in zip(chunks, vectors):
        points.append(PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk["id"])),
            vector=vector,
            payload={
                "user_id": user_id,
                "document_id": document_id,
                "document_title": title,
                "file_type": file_type,
                "chunk_id": chunk["id"],
                "chunk_index": chunk["index"],
                "text": chunk["text"],
            },
        ))
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)


def search(user_id: str, query: str, limit: int = 10) -> list[dict]:
    client = get_client()
    ensure_collection()
    vector = embeddings.embed_query(query)
    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vector,
        limit=limit,
        query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]),
        with_payload=True,
    )
    return [
        {
            "chunk_id": r.payload.get("chunk_id", ""),
            "document_id": r.payload.get("document_id", ""),
            "document_title": r.payload.get("document_title", ""),
            "file_type": r.payload.get("file_type", ""),
            "text": r.payload.get("text", ""),
            "score": float(r.score),
        }
        for r in results
    ]


def document_vector(user_id: str, document_id: str) -> list[float] | None:
    """Return the first chunk vector of a document (used as its centroid proxy)."""
    client = get_client()
    ensure_collection()
    points, _ = client.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter=Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]),
        limit=1,
        with_vectors=True,
    )
    if points:
        return list(points[0].vector)
    return None


def delete_document(document_id: str) -> None:
    client = get_client()
    ensure_collection()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(must=[
            FieldCondition(key="document_id", match=MatchValue(value=document_id))
        ]),
    )

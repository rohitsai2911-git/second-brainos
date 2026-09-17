"""Local embedding service using sentence-transformers (lazy-loaded singleton)."""
import hashlib
import threading

from ..config import settings

_model = None
_lock = threading.Lock()
_dim = 384  # bge-small-en-v1.5 dimension


def _load_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
                except Exception:
                    _model = False  # fallback mode
    return _model


def _hash_embed(text: str, dim: int = _dim) -> list[float]:
    """Deterministic fallback embedding (hashed token bag) when the
    sentence-transformers model is unavailable. Keeps the whole system
    functional for demos without heavy ML deps."""
    import math
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    if model:
        return [v.tolist() for v in model.encode(texts, normalize_embeddings=True)]
    return [_hash_embed(t) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def dimension() -> int:
    model = _load_model()
    if model:
        try:
            return int(model.get_sentence_embedding_dimension())
        except Exception:
            pass
    return _dim


def using_neural_model() -> bool:
    return bool(_load_model())

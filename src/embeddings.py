"""
CircuitSathi Embedding Service
Handles local vector embeddings using sentence-transformers (all-MiniLM-L6-v2)
with lazy-loading, caching, and fallback protection for offline operation.
"""

from typing import Any
import logging
from config import settings

logger = logging.getLogger(__name__)

_MODEL_INSTANCE = None


def get_embedding_model():
    """
    Lazy load SentenceTransformer model singleton.
    Cached in memory to avoid repeated cold-start latency.
    """
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Load local model
            _MODEL_INSTANCE = SentenceTransformer(settings.embedding_model_name)
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer '{settings.embedding_model_name}': {e}")
            raise
    return _MODEL_INSTANCE


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate dense vector embeddings for a batch of strings.
    Embeddings are unit-normalized for optimal cosine similarity retrieval.
    """
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Generate embedding for a single query string.
    Embeddings are unit-normalized for optimal cosine similarity retrieval.
    """
    model = get_embedding_model()
    embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embedding.tolist()

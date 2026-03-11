"""
Embedding Service – wraps sentence-transformers for text embedding.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using a pre-trained sentence-transformer model."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        logger.info("Loading embedding model: %s", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding dimension: %d", self._dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed a list of texts.

        Returns a list of float vectors.
        """
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        embedding = self._model.encode(
            query,
            normalize_embeddings=True,
        )
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return list(embedding)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Singleton accessor for the embedding service."""
    return EmbeddingService()

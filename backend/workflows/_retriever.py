"""
Shared document retrieval helper for all workflows.

Uses the singleton embedding service + vector store (same instances as RAG pipeline)
so there is no double-loading of the ONNX model.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def retrieve_context(query_text: str, top_k: int = 15) -> str:
    """
    Embed `query_text` and retrieve the top-k matching chunks from the vector store.
    Returns a single concatenated string ready to pass to an LLM.
    Falls back to empty string on any error.
    """
    try:
        from backend.embeddings import get_embedding_service
        from backend.vector_store import get_vector_store

        embedder = get_embedding_service()
        vector_store = get_vector_store(dimension=embedder.dimension)

        query_embedding = embedder.embed_query(query_text)
        results = vector_store.search(query_embedding=query_embedding, top_k=top_k)

        if not results:
            logger.warning("Vector store returned no results for query: %r", query_text[:80])
            return ""

        chunks = []
        for r in results:
            text = r.get("document") or r.get("text") or ""
            if text.strip():
                chunks.append(text.strip())

        combined = "\n\n---\n\n".join(chunks)
        logger.info("Retrieved %d chunks (%d chars) for query: %r", len(chunks), len(combined), query_text[:60])
        return combined

    except Exception as exc:
        logger.warning("Document retrieval failed: %s", exc)
        return ""

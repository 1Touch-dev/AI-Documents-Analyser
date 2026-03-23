"""
RAG Pipeline – orchestrates the full Retrieval-Augmented Generation flow.

embed query → search vector DB → build prompt → call LLM → return answer + citations
"""

from __future__ import annotations

import logging
from typing import Any

from backend.embeddings import EmbeddingService
from backend.llm_router import LLMRouter
from backend.prompt_manager import PromptManager
from backend.vector_store import BaseVectorStore
from config.settings import settings

logger = logging.getLogger(__name__)

MAX_INGEST_CHARS = 300_000
MAX_INGEST_CHUNKS = 600


class RAGPipeline:
    """End-to-end retrieval-augmented generation pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
        llm_router: LLMRouter,
    ) -> None:
        self.embedder = embedding_service
        self.vector_store = vector_store
        self.llm = llm_router

    # ── Document ingestion ───────────────────────────────
    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break on sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                break_point = max(last_period, last_newline)
                if break_point > chunk_size * 0.5:
                    chunk = text[start : start + break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]

    def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Chunk → embed → store.  Returns the number of chunks created.
        """
        if len(text) > MAX_INGEST_CHARS:
            logger.warning(
                "Document %s text too large (%d chars). Truncating to %d chars.",
                doc_id,
                len(text),
                MAX_INGEST_CHARS,
            )
            text = text[:MAX_INGEST_CHARS]

        chunks = self.chunk_text(text)
        if not chunks:
            logger.warning("No chunks produced for doc %s", doc_id)
            return 0

        if len(chunks) > MAX_INGEST_CHUNKS:
            logger.warning(
                "Document %s produced too many chunks (%d). Capping to %d.",
                doc_id,
                len(chunks),
                MAX_INGEST_CHUNKS,
            )
            chunks = chunks[:MAX_INGEST_CHUNKS]

        embeddings = self.embedder.embed_texts(chunks)

        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            m = {
                "doc_id": doc_id,
                "chunk_index": i,
                "char_count": len(chunk),
            }
            if metadata:
                m.update(metadata)
            chunk_metadatas.append(m)

        self.vector_store.add_documents(
            doc_id=doc_id,
            chunks=chunks,
            embeddings=embeddings,
            metadatas=chunk_metadatas,
        )
        logger.info("Ingested doc %s: %d chunks", doc_id, len(chunks))
        return len(chunks)

    # ── Query ────────────────────────────────────────────
    async def query(
        self,
        question: str,
        model_name: str = "auto",
        prompt_template: str | None = None,
        top_k: int | None = None,
        temperature: float = 0.7,
        filter_metadata: dict[str, Any] | None = None,
        api_keys: dict[str, str | None] | None = None,
        full_doc_list: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Full RAG query: embed → search → prompt → LLM → answer.

        Returns
        -------
        dict with keys: ``answer``, ``sources``, ``model_used``
        """
        k = top_k or settings.top_k

        # 1. Resolve model
        resolved_model = self.llm.resolve_model(model_name, question, api_keys)

        # 2. Embed the query
        query_embedding = self.embedder.embed_query(question)

        # 3. Search vector store
        search_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            filter_metadata=filter_metadata,
        )

        # 4. Build context from retrieved chunks
        context_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"[{i}] {result['document']}")
            sources.append(
                {
                    "chunk_id": result["id"],
                    "doc_id": result["metadata"].get("doc_id", ""),
                    "chunk_index": result["metadata"].get("chunk_index", 0),
                    "title": result["metadata"].get("title", ""),
                    "relevance_score": round(1 - result.get("distance", 0), 4),
                    "excerpt": result["document"][:200],
                }
            )

        context = "\n\n".join(context_parts)

        # 5. Build prompt
        library_info = ""
        if full_doc_list:
            titles_str = "\n".join([f"- {t}" for t in full_doc_list])
            library_info = f"Document Library Overview (Total {len(full_doc_list)} documents available):\n{titles_str}\n\n"

        if prompt_template:
            prompt = PromptManager.render(
                prompt_template, {"context": context, "question": question, "library_info": library_info}
            )
        else:
            prompt = (
                "You are a knowledgeable AI assistant. Use the following library overview and context to answer "
                "the user's question. \n\n"
                "Guidelines:\n"
                "1. If the user asks about document counts or names, refer to the Library Overview.\n"
                "2. For content-specific answers, use the Retrieve Context Chunks and cite them using [1], [2], etc.\n"
                "3. Ensure every factual claim is grounded in the provided chunks.\n"
                "4. If you cannot find the answer, be honest.\n\n"
                f"{library_info}"
                f"Retrieved Context Chunks:\n{context}\n\n"
                f"Question: {question}\n\n"
                "Answer:"
            )

        # 6. Call LLM
        messages = [
            {"role": "system", "content": "You are a knowledgeable AI assistant that answers questions based on provided document context. Always cite your sources."},
            {"role": "user", "content": prompt},
        ]
        answer = await self.llm.generate(
            model_name=resolved_model,
            messages=messages,
            temperature=temperature,
            api_keys=api_keys,
        )

        logger.info(
            "RAG query completed: model=%s, sources=%d", resolved_model, len(sources)
        )

        return {
            "answer": answer,
            "sources": sources,
            "model_used": resolved_model,
            "chunks_retrieved": len(search_results),
        }

    # ── Delete document from index ───────────────────────
    def remove_document(self, doc_id: str) -> None:
        """Remove all chunks for a document from the vector store."""
        self.vector_store.delete_document(doc_id)
        logger.info("Removed doc %s from vector store", doc_id)

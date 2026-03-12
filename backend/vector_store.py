"""
Vector Store Service – abstraction over ChromaDB and Qdrant.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Base interface
# ──────────────────────────────────────────────────────────
class BaseVectorStore(ABC):
    """Abstract interface for all vector store backends."""

    @abstractmethod
    def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None: ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> None: ...

    @abstractmethod
    def count(self) -> int: ...


# ──────────────────────────────────────────────────────────
# ChromaDB
# ──────────────────────────────────────────────────────────
class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-backed vector store (default)."""

    COLLECTION_NAME = "documents"

    def __init__(self, persist_dir: str | None = None) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._cleanup_macos_sidecars(chromadb)
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready (%d items)", self.COLLECTION_NAME, self._collection.count())

    @staticmethod
    def _cleanup_macos_sidecars(chromadb_module: Any) -> None:
        """
        Remove macOS AppleDouble files (e.g. ._00001-*.sql) that break Chroma migrations.
        """
        try:
            chroma_root = Path(chromadb_module.__file__).resolve().parent
            migrations_dir = chroma_root / "migrations"
            if not migrations_dir.exists():
                return

            removed = 0
            for sidecar in migrations_dir.rglob("._*"):
                if sidecar.is_file():
                    sidecar.unlink()
                    removed += 1
            if removed:
                logger.warning("Removed %d macOS sidecar file(s) from Chroma migrations.", removed)
        except Exception as exc:
            logger.warning("Failed to clean Chroma migration sidecar files: %s", exc)

    def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        if metadatas is None:
            metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        else:
            for i, m in enumerate(metadatas):
                m.setdefault("doc_id", doc_id)
                m.setdefault("chunk_index", i)

        self._collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info("Added %d chunks for doc %s", len(chunks), doc_id)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata

        results = self._collection.query(**kwargs)

        output: list[dict[str, Any]] = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                }
            )
        return output

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})
        logger.info("Deleted all chunks for doc %s", doc_id)

    def count(self) -> int:
        return self._collection.count()

    def get_all_documents(self, limit: int = 200) -> list[dict[str, Any]]:
        """Retrieve stored documents for analytics."""
        try:
            results = self._collection.get(limit=limit, include=["documents", "metadatas"])
            output = []
            for i in range(len(results["ids"])):
                output.append({
                    "id": results["ids"][i],
                    "document": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
            return output
        except Exception:
            return []


# ──────────────────────────────────────────────────────────
# Qdrant
# ──────────────────────────────────────────────────────────
class QdrantVectorStore(BaseVectorStore):
    """Qdrant-backed vector store (optional)."""

    COLLECTION_NAME = "documents"

    def __init__(self, url: str | None = None, dimension: int = 1024) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._url = url or settings.qdrant_url
        self._client = QdrantClient(url=self._url)
        self._dimension = dimension

        # Create collection if it doesn't exist
        collections = [c.name for c in self._client.get_collections().collections]
        if self.COLLECTION_NAME not in collections:
            self._client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
        logger.info("Qdrant collection '%s' ready", self.COLLECTION_NAME)

    def add_documents(
        self,
        doc_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            payload = {"doc_id": doc_id, "chunk_index": i, "text": chunk}
            if metadatas and i < len(metadatas):
                payload.update(metadatas[i])
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb,
                    payload=payload,
                )
            )
        self._client.upsert(collection_name=self.COLLECTION_NAME, points=points)
        logger.info("Added %d chunks for doc %s (Qdrant)", len(chunks), doc_id)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filter_metadata:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            qdrant_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=qdrant_filter,
        )

        output: list[dict[str, Any]] = []
        for hit in results:
            output.append(
                {
                    "id": str(hit.id),
                    "document": hit.payload.get("text", ""),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                    "distance": hit.score,
                }
            )
        return output

    def delete_document(self, doc_id: str) -> None:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        self._client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        logger.info("Deleted all chunks for doc %s (Qdrant)", doc_id)

    def count(self) -> int:
        info = self._client.get_collection(self.COLLECTION_NAME)
        return info.points_count


# ──────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────
def get_vector_store(dimension: int = 1024) -> BaseVectorStore:
    """Return the configured vector store backend."""
    if settings.vector_store_type == "qdrant":
        return QdrantVectorStore(dimension=dimension)
    return ChromaVectorStore()

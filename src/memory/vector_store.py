"""Vector storage abstractions and search implementations."""

import math
from typing import Any, Protocol

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """Document embedded for episodic or semantic memory."""

    id: str
    text: str
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    """Retrieved document scored by semantic cosine similarity."""

    document: VectorDocument
    similarity_score: float = Field(ge=0.0, le=1.0)


class VectorStore(Protocol):
    """Protocol for vector databases (PgVector, Qdrant, InMemory)."""

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        ...

    async def search(
        self,
        query_vector: list[float],
        limit: int = 3,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        ...


class InMemoryVectorStore(VectorStore):
    """Zero-dependency, thread-safe in-memory vector store for testing and evaluation."""

    def __init__(self) -> None:
        self.documents: list[VectorDocument] = []

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        self.documents.extend(documents)

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        # Normalize to 0.0 - 1.0 range
        sim = dot_product / (norm_a * norm_b)
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    async def search(
        self,
        query_vector: list[float],
        limit: int = 3,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        candidates = self.documents
        if metadata_filters:
            filtered = []
            for doc in candidates:
                match = True
                for k, v in metadata_filters.items():
                    if doc.metadata.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(doc)
            candidates = filtered

        scored: list[VectorSearchResult] = []
        for doc in candidates:
            score = self._cosine_similarity(query_vector, doc.embedding)
            scored.append(VectorSearchResult(document=doc, similarity_score=score))

        scored.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored[:limit]

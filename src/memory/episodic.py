"""Episodic memory manager indexing and retrieving historical incident postmortems."""

from typing import Any

from src.memory.embeddings import EmbeddingProvider, MockEmbeddingProvider
from src.memory.seed_data import HISTORICAL_POSTMORTEMS, HistoricalPostmortem
from src.memory.vector_store import (
    InMemoryVectorStore,
    VectorDocument,
    VectorSearchResult,
    VectorStore,
)
from src.observability.logging import get_logger

logger = get_logger(__name__)


class EpisodicMemoryManager:
    """Manages indexing, semantic vector search, and context budgeting for historical incidents."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.vector_store = vector_store or InMemoryVectorStore()
        self._seeded = False

    def _format_postmortem_text(self, pm: HistoricalPostmortem) -> str:
        """Constructs a dense representation of an incident postmortem for vector indexing."""
        signals_str = "\n".join(f"- {s}" for s in pm.detection_signals)
        remediation_str = "\n".join(f"- {r}" for r in pm.remediation_steps)
        prevention_str = "\n".join(f"- {p}" for p in pm.prevention_measures)

        return (
            f"Incident: {pm.incident_id} - {pm.title}\n"
            f"Service: {pm.service} | Severity: {pm.severity}\n"
            f"Summary: {pm.summary}\n"
            f"Root Cause: {pm.root_cause}\n"
            f"Detection Signals:\n{signals_str}\n"
            f"Remediation Steps:\n{remediation_str}\n"
            f"Prevention Measures:\n{prevention_str}"
        )

    async def index_postmortem(self, pm: HistoricalPostmortem) -> None:
        """Indexes a single postmortem into vector storage."""
        doc_text = pm.full_text if pm.full_text else self._format_postmortem_text(pm)
        embedding = await self.embedding_provider.embed_text(doc_text)

        metadata: dict[str, Any] = {
            "incident_id": pm.incident_id,
            "title": pm.title,
            "service": pm.service,
            "severity": pm.severity,
            "root_cause": pm.root_cause,
            "remediation_steps": pm.remediation_steps,
            **pm.metadata,
        }

        doc = VectorDocument(
            id=pm.incident_id,
            text=doc_text,
            embedding=embedding,
            metadata=metadata,
        )
        await self.vector_store.add_documents([doc])
        logger.info(f"Indexed postmortem [{pm.incident_id}] for service [{pm.service}]")

    async def seed_default_memories(self) -> None:
        """Seeds the vector store with curated historical postmortems."""
        if self._seeded:
            return

        docs: list[VectorDocument] = []
        for pm in HISTORICAL_POSTMORTEMS:
            doc_text = self._format_postmortem_text(pm)
            embedding = await self.embedding_provider.embed_text(doc_text)
            metadata: dict[str, Any] = {
                "incident_id": pm.incident_id,
                "title": pm.title,
                "service": pm.service,
                "severity": pm.severity,
                "root_cause": pm.root_cause,
                "remediation_steps": pm.remediation_steps,
                **pm.metadata,
            }
            docs.append(
                VectorDocument(
                    id=pm.incident_id,
                    text=doc_text,
                    embedding=embedding,
                    metadata=metadata,
                )
            )

        await self.vector_store.add_documents(docs)
        self._seeded = True
        logger.info(f"Seeded episodic memory with {len(docs)} historical postmortems")

    async def search_similar_incidents(
        self,
        query: str,
        service: str | None = None,
        top_k: int = 3,
        max_char_budget: int = 2400,
    ) -> list[VectorSearchResult]:
        """Performs semantic vector search with optional service filtering and budget capping.

        If a service-specific filter returns no matches, falls back to cross-service
        semantic search to surface analogous architectural failure patterns.
        """
        if not self._seeded:
            await self.seed_default_memories()

        query_vector = await self.embedding_provider.embed_text(query)

        results: list[VectorSearchResult] = []
        if service:
            results = await self.vector_store.search(
                query_vector=query_vector,
                limit=top_k,
                metadata_filters={"service": service},
            )

        # Fallback to general search if service-filtered search yields insufficient results
        if not results:
            results = await self.vector_store.search(
                query_vector=query_vector,
                limit=top_k,
            )

        # Enforce context budget constraint
        budgeted_results: list[VectorSearchResult] = []
        accumulated_chars = 0
        for res in results[:top_k]:
            doc_len = len(res.document.text)
            if accumulated_chars + doc_len > max_char_budget and budgeted_results:
                # Truncate text if needed to fit remaining budget
                remaining = max(100, max_char_budget - accumulated_chars)
                truncated_doc = res.document.model_copy(
                    update={"text": res.document.text[:remaining] + "\n...[truncated]"}
                )
                budgeted_results.append(
                    VectorSearchResult(document=truncated_doc, similarity_score=res.similarity_score)
                )
                break
            accumulated_chars += doc_len
            budgeted_results.append(res)

        return budgeted_results

    def format_memories_for_prompt(self, results: list[VectorSearchResult]) -> str:
        """Formats search results into structured, clean markdown for LLM consumption."""
        if not results:
            return "No historical postmortems matching the query were found in memory."

        formatted_blocks = []
        for i, res in enumerate(results, 1):
            doc = res.document
            meta = doc.metadata
            remediation = "\n".join(f"    * {r}" for r in meta.get("remediation_steps", []))
            block = (
                f"### [Historical Match {i}] {doc.id}: {meta.get('title', 'Unknown')}\n"
                f"- **Similarity Score**: {res.similarity_score:.3f}\n"
                f"- **Target Service**: {meta.get('service', 'N/A')}\n"
                f"- **Root Cause**: {meta.get('root_cause', 'N/A')}\n"
                f"- **Proven Remediation**:\n{remediation}\n"
            )
            formatted_blocks.append(block)

        return "\n".join(formatted_blocks)

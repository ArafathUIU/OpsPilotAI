"""Unit tests for vector store, episodic memory manager, and memory tools."""

import pytest

from src.agents.memory_analyst import IncidentMemoryAgent
from src.domain.state import InvestigationTask
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter
from src.memory.embeddings import MockEmbeddingProvider
from src.memory.episodic import EpisodicMemoryManager
from src.memory.seed_data import HISTORICAL_POSTMORTEMS, HistoricalPostmortem
from src.memory.vector_store import InMemoryVectorStore, VectorDocument
from src.tools.memory_tools import SearchIncidentMemoryTool
from src.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_in_memory_vector_store_exact_match():
    store = InMemoryVectorStore()
    doc1 = VectorDocument(
        id="DOC-1",
        text="Redis connection pool starvation",
        embedding=[1.0, 0.0, 0.0],
        metadata={"service": "order-service"},
    )
    doc2 = VectorDocument(
        id="DOC-2",
        text="Database deadlock and transaction abort",
        embedding=[0.0, 1.0, 0.0],
        metadata={"service": "payment-service"},
    )
    await store.add_documents([doc1, doc2])

    # Query with vector identical to doc1
    results = await store.search(query_vector=[1.0, 0.0, 0.0], limit=2)
    assert len(results) == 2
    assert results[0].document.id == "DOC-1"
    assert pytest.approx(results[0].similarity_score, abs=1e-3) == 1.0


@pytest.mark.asyncio
async def test_in_memory_vector_store_metadata_filtering():
    store = InMemoryVectorStore()
    doc1 = VectorDocument(
        id="DOC-1",
        text="Redis pool failure",
        embedding=[0.5, 0.5, 0.0],
        metadata={"service": "order-service"},
    )
    doc2 = VectorDocument(
        id="DOC-2",
        text="Redis pool failure on payment",
        embedding=[0.5, 0.5, 0.0],
        metadata={"service": "payment-service"},
    )
    await store.add_documents([doc1, doc2])

    filtered = await store.search(
        query_vector=[0.5, 0.5, 0.0],
        limit=5,
        metadata_filters={"service": "payment-service"},
    )
    assert len(filtered) == 1
    assert filtered[0].document.id == "DOC-2"


@pytest.mark.asyncio
async def test_episodic_memory_seeding_and_search():
    embedding = MockEmbeddingProvider(dimension=64)
    store = InMemoryVectorStore()
    manager = EpisodicMemoryManager(embedding_provider=embedding, vector_store=store)

    await manager.seed_default_memories()
    assert len(store.documents) == len(HISTORICAL_POSTMORTEMS)

    # Search similar incidents for Redis pool exhaustion
    results = await manager.search_similar_incidents(
        query="Redis connection pool exhausted and timeout",
        service="order-service",
        top_k=2,
    )
    assert len(results) >= 1
    top_match = results[0]
    assert "PM-2025-001" in top_match.document.id
    assert top_match.similarity_score > 0.0

    prompt_formatted = manager.format_memories_for_prompt(results)
    assert "PM-2025-001" in prompt_formatted
    assert "Proven Remediation" in prompt_formatted


@pytest.mark.asyncio
async def test_episodic_memory_dynamic_indexing():
    manager = EpisodicMemoryManager()
    new_pm = HistoricalPostmortem(
        incident_id="PM-2026-999",
        title="Custom Kafka Consumer Lag Spikes",
        service="notification-service",
        severity="SEV-2",
        summary="Kafka rebalancing storm caused message processing delay.",
        root_cause="Heartbeat timeout was configured lower than processing batch time.",
        detection_signals=["consumer group rebalance loop"],
        remediation_steps=["Increased max.poll.interval.ms to 300000"],
    )
    await manager.index_postmortem(new_pm)

    results = await manager.search_similar_incidents(
        query="kafka consumer rebalance timeout",
        service="notification-service",
    )
    assert any(r.document.id == "PM-2026-999" for r in results)


@pytest.mark.asyncio
async def test_search_incident_memory_tool():
    manager = EpisodicMemoryManager()
    tool = SearchIncidentMemoryTool(memory_manager=manager)

    result = await tool.execute(query="redis pool timeout", service="order-service", limit=2)
    assert result.status == "SUCCESS"
    assert result.data["match_count"] >= 1
    assert "PM-2025-001" in result.data["matches"][0]["incident_id"]


@pytest.mark.asyncio
async def test_incident_memory_agent_investigation():
    provider = MockLLMProvider()
    router = ModelRouter([provider])
    registry = ToolRegistry()

    agent = IncidentMemoryAgent(registry=registry, router=router)
    task = InvestigationTask(
        task_id="task-mem-test",
        agent_type="memory_analyst",
        target_service="payment-service",
        query_intent="Historical postmortems for Redis connection exhaustion",
    )

    output = await agent.investigate(task)
    assert output.agent_type == "analyst"
    assert len(output.evidence_items) > 0
    mem_evidence = [e for e in output.evidence_items if e.type == "memory"]
    assert len(mem_evidence) > 0
    assert "PM-2025-001" in mem_evidence[0].raw_reference or "PM-2025-001" in mem_evidence[0].observation

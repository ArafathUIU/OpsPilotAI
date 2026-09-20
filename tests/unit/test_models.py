"""Unit tests for SQLAlchemy models using an isolated in-memory SQLite database."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.persistence.models import (
    Base,
    EvidenceModel,
    HypothesisModel,
    Incident,
)


@pytest.fixture
async def async_test_session():
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_incident_and_evidence_creation(async_test_session: AsyncSession):
    # 1. Create incident
    incident = Incident(
        title="Payment Service Latency Spike P95 > 2.5s",
        description="P95 latency degradation following v2.4.1 deployment",
        severity="SEV1",
        current_stage="INVESTIGATING",
        affected_services=["payment-service", "api-gateway"],
    )
    async_test_session.add(incident)
    await async_test_session.commit()
    await async_test_session.refresh(incident)

    assert incident.id is not None
    assert isinstance(incident.id, uuid.UUID)
    assert incident.current_stage == "INVESTIGATING"

    # 2. Add Evidence
    evidence = EvidenceModel(
        incident_id=incident.id,
        evidence_code="EV-REDIS-01",
        evidence_type="log",
        source="payment-service",
        observation="Redis connection pool exhausted, 142 timeouts in 60s",
        raw_reference="RedisTimeoutException: pool exhausted at Connection.acquire",
        relevance_score=0.95,
        metadata_json={"cluster": "prod-us-east-1", "redis_node": "node-3"},
    )
    async_test_session.add(evidence)

    # 3. Add Hypothesis
    hypothesis = HypothesisModel(
        incident_id=incident.id,
        title="Redis Connection Pool Starvation",
        description=(
            "Deployment v2.4.1 reduced max_connections from 100 to 10 causing thread queue backlog"
        ),
        confidence=0.92,
        supporting_evidence_ids=["EV-REDIS-01"],
        contradicting_evidence_ids=[],
        reasoning_summary="Direct correlation between deploy time and pool exhaustion logs",
        is_selected=True,
    )
    async_test_session.add(hypothesis)
    await async_test_session.commit()

    # Query back and verify relations
    await async_test_session.refresh(incident)
    assert len(incident.evidence_items) == 1
    assert incident.evidence_items[0].evidence_code == "EV-REDIS-01"
    assert len(incident.hypotheses) == 1
    assert incident.hypotheses[0].confidence == 0.92

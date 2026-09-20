"""Unit tests for embedding providers and vector calculations."""

import math

import pytest

from src.memory.embeddings import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_mock_embedding_provider_dimension_and_norm():
    provider = MockEmbeddingProvider(dimension=128)
    vec = await provider.embed_text("Connection pool exhausted in order-service")

    assert len(vec) == 128
    # Verify L2 norm is approximately 1.0 (unit vector)
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, abs=1e-5) == 1.0


@pytest.mark.asyncio
async def test_mock_embedding_provider_determinism():
    provider = MockEmbeddingProvider(dimension=64)
    text = "Redis timeout occurred during flash sale"

    vec1 = await provider.embed_text(text)
    vec2 = await provider.embed_text(text)

    assert vec1 == vec2


@pytest.mark.asyncio
async def test_mock_embedding_provider_distinct_vectors():
    provider = MockEmbeddingProvider(dimension=64)
    vec_redis = await provider.embed_text("redis connection pool timeout")
    vec_db = await provider.embed_text("database postgres deadlock contention")

    assert vec_redis != vec_db


@pytest.mark.asyncio
async def test_mock_embedding_provider_empty_string():
    provider = MockEmbeddingProvider(dimension=32)
    vec = await provider.embed_text("")

    assert len(vec) == 32
    assert vec[0] == 1.0
    assert all(x == 0.0 for x in vec[1:])


@pytest.mark.asyncio
async def test_mock_embedding_provider_batch():
    provider = MockEmbeddingProvider(dimension=64)
    texts = ["service alpha", "service beta", "service gamma"]
    batch = await provider.embed_batch(texts)

    assert len(batch) == 3
    for v in batch:
        assert len(v) == 64
        norm = math.sqrt(sum(x * x for x in v))
        assert pytest.approx(norm, abs=1e-5) == 1.0

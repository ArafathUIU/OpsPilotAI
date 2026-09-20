"""Embedding providers and vector generation abstraction."""

import hashlib
import math
from typing import Protocol

import httpx

from src.core.config import get_settings

settings = get_settings()
DEFAULT_EMBEDDING_DIM = 1536


class EmbeddingProvider(Protocol):
    """Protocol for text embedding generation."""

    async def embed_text(self, text: str) -> list[float]:
        """Generates embedding vector for a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generates embedding vectors for a list of texts."""
        ...


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency embedding provider for offline tests and evaluation.
    Produces repeatable, cosine-comparable 1536-dimensional unit vectors based on text token hashes.
    """

    def __init__(self, dimension: int = DEFAULT_EMBEDDING_DIM) -> None:
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        # Hash words to generate deterministic feature coordinates
        words = text.lower().split()
        vector = [0.0] * self.dimension

        if not words:
            vector[0] = 1.0
            return vector

        for word in words:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            val = ((h >> 8) % 1000) / 500.0 - 1.0  # value between -1.0 and 1.0
            vector[idx] += val

        # L2-normalize to unit vector
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        else:
            vector[0] = 1.0
        return vector

    async def embed_text(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI / OpenAI-compatible embedding API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        dimension: int = DEFAULT_EMBEDDING_DIM,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in data["data"]]

    async def embed_text(self, text: str) -> list[float]:
        res = await self.embed_batch([text])
        return res[0]

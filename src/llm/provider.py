"""LLM provider protocol and response models."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMResponse[T: BaseModel](BaseModel):
    parsed: T
    raw_content: str
    usage: TokenUsage
    provider: str
    model: str
    latency_ms: float = 0.0


class LLMProvider(Protocol):
    """Protocol for pluggable LLM provider adapters."""

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: type[T],
        temperature: float = 0.1,
    ) -> LLMResponse[T]:
        """Generates validated structured output matching response_model."""
        ...

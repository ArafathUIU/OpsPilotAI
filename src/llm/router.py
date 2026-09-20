"""Model routing, tiered model selection, and failover manager."""

from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel

from src.core.config import get_settings
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.adapters.openai_provider import OpenAICompatibleProvider
from src.llm.provider import LLMProvider, LLMResponse, TokenUsage
from src.observability.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)
settings = get_settings()


class TaskTier(StrEnum):
    FAST = "fast"  # Triage, summarization, simple extraction
    REASONING = "reasoning"  # Root cause causal synthesis
    CRITIC = "critic"  # Adversarial debunking & critique


class ModelRouter:
    """Manages tiered model selection, multi-provider failover, and token budgeting."""

    def __init__(self, providers: list[LLMProvider] | None = None) -> None:
        if providers:
            self.providers = providers
        else:
            self.providers = self._build_default_provider_chain()

        self.cumulative_usage = TokenUsage()

    def _build_default_provider_chain(self) -> list[LLMProvider]:
        chain: list[LLMProvider] = []

        # 1. Primary: OpenAI if API key provided
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-mock"):
            chain.append(
                OpenAICompatibleProvider(
                    api_key=settings.OPENAI_API_KEY,
                    model=settings.OPENAI_MODEL,
                    provider_name="openai",
                )
            )

        # 2. Secondary: Groq if API key provided
        if settings.GROQ_API_KEY:
            chain.append(
                OpenAICompatibleProvider(
                    api_key=settings.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1",
                    model=settings.GROQ_MODEL,
                    provider_name="groq",
                )
            )

        # 3. Deterministic high-fidelity mock provider (always present as resilient fallback)
        chain.append(MockLLMProvider(provider_name="mock-fallback", model_name="opspilot-mock-v1"))
        return chain

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: type[T],
        tier: TaskTier = TaskTier.FAST,
        max_retries: int = 2,
    ) -> LLMResponse[T]:
        """Attempts generation with provider failover across configured adapters."""
        last_error: Exception | None = None

        for provider in self.providers:
            for attempt in range(1, max_retries + 1):
                try:
                    response = await provider.generate_structured(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        response_model=response_model,
                    )
                    # Accumulate token metrics
                    self.cumulative_usage.input_tokens += response.usage.input_tokens
                    self.cumulative_usage.output_tokens += response.usage.output_tokens
                    self.cumulative_usage.total_tokens += response.usage.total_tokens
                    self.cumulative_usage.estimated_cost_usd += response.usage.estimated_cost_usd

                    logger.info(
                        f"Structured generation succeeded using [{response.provider}/{response.model}] "
                        f"in {response.latency_ms}ms ({response.usage.total_tokens} tokens)",
                        extra={
                            "provider": response.provider,
                            "model": response.model,
                            "tokens": response.usage.total_tokens,
                            "tier": tier.value,
                        },
                    )
                    return response

                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed on provider [{getattr(provider, 'provider_name', 'unknown')}]: {exc}"
                    )

        raise RuntimeError(
            f"All LLM providers in fallback chain exhausted. Final error: {last_error}"
        )


# Global router singleton
default_router = ModelRouter()

"""Unit tests for LLM provider abstraction, structured generation, and router failover."""

import pytest

from src.domain.state import SupervisorPlan
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter, TaskTier


@pytest.mark.asyncio
async def test_mock_provider_structured_output():
    provider = MockLLMProvider(provider_name="test-mock", model_name="mock-v1")
    response = await provider.generate_structured(
        prompt="Payment service latency spike after deployment",
        system_prompt="Triage alert",
        response_model=SupervisorPlan,
    )

    assert response.provider == "test-mock"
    assert isinstance(response.parsed, SupervisorPlan)
    assert response.parsed.initial_severity == "SEV1"
    assert len(response.parsed.tasks) >= 2
    assert response.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_router_failover_to_secondary_provider():
    failing_primary = MockLLMProvider(provider_name="failing-primary", always_fail=True)
    healthy_secondary = MockLLMProvider(provider_name="healthy-secondary")

    router = ModelRouter(providers=[failing_primary, healthy_secondary])

    response = await router.generate_structured(
        prompt="Test prompt",
        system_prompt="Test system",
        response_model=SupervisorPlan,
        tier=TaskTier.FAST,
    )

    assert response.provider == "healthy-secondary"
    assert isinstance(response.parsed, SupervisorPlan)
    assert router.cumulative_usage.total_tokens > 0

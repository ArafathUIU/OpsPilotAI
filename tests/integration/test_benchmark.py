"""Integration benchmark test verifying multi-agent accuracy against ground truth."""

import pytest

from src.evaluation.runner import EvaluationEngine


@pytest.mark.asyncio
async def test_full_benchmark_accuracy_and_safety():
    """Validates that the multi-agent cognitive architecture satisfies accuracy and safety thresholds."""
    engine = EvaluationEngine()

    # Benchmark demonstration failure scenario
    test_scenarios = [
        "redis_pool_exhaustion",
    ]

    summary = await engine.run_benchmark(test_scenarios)

    # 1. Root Cause Attribution: 100% accuracy on target service
    assert summary.service_attribution_accuracy == 100.0

    # 2. Semantic Similarity / F1 threshold
    assert summary.root_cause_f1_score >= 0.50

    # 3. Safety Compliance: 100% blast radius containment
    assert summary.safety_compliance_rate == 100.0

    # 4. Latency performance: mean investigation under 15,000ms
    assert summary.mean_duration_ms < 15000.0

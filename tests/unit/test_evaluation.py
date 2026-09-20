"""Unit tests for OpsPilot AI evaluation engine and benchmark reporting."""

import json

import pytest

from src.evaluation.metrics import BenchmarkSummary, EvaluationResult
from src.evaluation.runner import EvaluationEngine


@pytest.fixture
def eval_engine():
    return EvaluationEngine()


def test_semantic_similarity_computation(eval_engine: EvaluationEngine):
    # Identical or high overlap
    sim1 = eval_engine._compute_semantic_similarity(
        "Redis connection pool exhausted by unclosed client sessions",
        "Redis connection pool exhaustion due to leaked connections",
    )
    assert sim1 > 0.5

    # Completely disjoint
    sim2 = eval_engine._compute_semantic_similarity(
        "SSL TLS certificate expired on edge gateway",
        "Memory leak OOM killed in order processing worker",
    )
    assert sim2 < sim1


@pytest.mark.asyncio
async def test_evaluate_single_scenario(eval_engine: EvaluationEngine):
    result = await eval_engine.evaluate_scenario("redis_pool_exhaustion")
    assert isinstance(result, EvaluationResult)
    assert result.scenario_id == "redis_pool_exhaustion"
    assert result.ground_truth_service == "payment-service"
    assert result.service_match is True
    assert result.root_cause_similarity > 0.3
    assert result.investigation_duration_ms > 0
    assert result.total_evidence_count > 0


@pytest.mark.asyncio
async def test_run_benchmark_summary(eval_engine: EvaluationEngine):
    # Run benchmark on demonstration scenario
    summary = await eval_engine.run_benchmark(["redis_pool_exhaustion"])
    assert isinstance(summary, BenchmarkSummary)
    assert summary.total_scenarios == 1
    assert summary.service_attribution_accuracy == 100.0
    assert summary.root_cause_f1_score >= 0.5
    assert summary.safety_compliance_rate == 100.0


def test_markdown_and_json_report_generation(eval_engine: EvaluationEngine):
    fake_result = EvaluationResult(
        scenario_id="fake_scenario",
        scenario_name="Fake Test Scenario",
        ground_truth_root_cause="Database deadlock",
        predicted_root_cause="Database deadlock under load",
        ground_truth_service="order-service",
        predicted_service="order-service",
        service_match=True,
        root_cause_similarity=0.95,
        remediation_action_valid=True,
        blast_radius_contained=True,
        critic_challenge_occurred=True,
        investigation_duration_ms=125.4,
        total_evidence_count=5,
        confidence_score=0.92,
    )
    fake_summary = BenchmarkSummary(
        total_scenarios=1,
        successful_attributions=1,
        service_attribution_accuracy=100.0,
        root_cause_f1_score=0.95,
        remediation_validity_rate=100.0,
        safety_compliance_rate=100.0,
        mean_duration_ms=125.4,
        average_confidence=0.92,
        results=[fake_result],
    )

    md = eval_engine.generate_markdown_report(fake_summary)
    assert "# OpsPilot AI — Multi-Agent Evaluation & Benchmark Report" in md
    assert "| `fake_scenario` | `order-service` |" in md

    json_str = eval_engine.generate_json_report(fake_summary)
    parsed = json.loads(json_str)
    assert parsed["total_scenarios"] == 1
    assert parsed["service_attribution_accuracy"] == 100.0

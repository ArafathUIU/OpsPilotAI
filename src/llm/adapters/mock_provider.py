"""Deterministic mock LLM provider for unit testing and offline evaluation."""

import time
from typing import TypeVar, cast

from pydantic import BaseModel

from src.domain.state import (
    AnalystAgentOutput,
    CritiqueResult,
    Evidence,
    Hypothesis,
    InvestigationTask,
    RCAAgentOutput,
    SupervisorPlan,
)
from src.llm.provider import LLMProvider, LLMResponse, TokenUsage

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic provider that simulates LLM reasoning and structured extraction."""

    def __init__(
        self,
        provider_name: str = "mock",
        model_name: str = "mock-model",
        always_fail: bool = False,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self.call_count: int = 0
        self.fail_next: bool = False
        self.always_fail: bool = always_fail

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: type[T],
        temperature: float = 0.1,
    ) -> LLMResponse[T]:
        start_time = time.perf_counter()
        self.call_count += 1

        if self.always_fail or self.fail_next:
            self.fail_next = False
            raise RuntimeError(f"Simulated provider failure on {self.provider_name}")

        prompt_lower = prompt.lower()
        parsed_obj: BaseModel

        if response_model is SupervisorPlan:
            tasks = [
                InvestigationTask(
                    task_id="task-log-01",
                    agent_type="log_analyst",
                    target_service="payment-service",
                    query_intent="Query error logs around deploy time for Redis exceptions",
                    time_window_minutes=15,
                ),
                InvestigationTask(
                    task_id="task-met-01",
                    agent_type="metrics_analyst",
                    target_service="payment-service",
                    query_intent="Inspect P95 latency and active connection pools",
                    time_window_minutes=15,
                ),
            ]
            if "deploy" in prompt_lower or "c3a9f01" in prompt_lower or "2.4" in prompt_lower:
                tasks.append(
                    InvestigationTask(
                        task_id="task-code-01",
                        agent_type="code_analyst",
                        target_service="payment-service",
                        query_intent="Inspect recent commit diffs and configuration changes",
                        time_window_minutes=30,
                    )
                )

            parsed_obj = SupervisorPlan(
                triage_assessment="Critical latency degradation on payment-service following deployment",
                initial_severity="SEV1",
                suspected_domains=["payment-service", "redis-cluster"],
                tasks=tasks,
                reasoning="P95 latency spike indicates resource bottleneck or bad config deployment",
            )

        elif response_model is AnalystAgentOutput:
            evidence_items = []
            if "log" in prompt_lower or "redistimeout" in prompt_lower:
                evidence_items.append(
                    Evidence(
                        id="EV-LOG-REDIS-01",
                        type="log",
                        source="payment-service",
                        observation="RedisTimeoutException: Connection pool exhausted [active=10, max=10]",
                        raw_reference="RedisTimeoutException: Connection pool exhausted at Connection.acquire",
                        relevance_score=0.96,
                    )
                )
            if (
                "metric" in prompt_lower
                or "p95" in prompt_lower
                or "active_connections" in prompt_lower
            ):
                evidence_items.append(
                    Evidence(
                        id="EV-MET-LATENCY-02",
                        type="metric",
                        source="payment-service",
                        observation="P95 latency spiked from 265ms baseline to 2820ms; Redis pool queue depth at 52",
                        raw_reference="http_request_duration_p95_seconds = 2.82s",
                        relevance_score=0.94,
                    )
                )
            if (
                "diff" in prompt_lower
                or "commit" in prompt_lower
                or "max_connections" in prompt_lower
            ):
                evidence_items.append(
                    Evidence(
                        id="EV-CODE-DIFF-03",
                        type="code",
                        source="payment-service",
                        observation="Commit c3a9f01b827e modified redis.yaml reducing max_connections from 100 to 10",
                        raw_reference="Commit c3a9f01b827e in payment-service by dev-engineer",
                        relevance_score=0.98,
                    )
                )

            parsed_obj = AnalystAgentOutput(
                agent_type="analyst",
                service="payment-service",
                findings_summary="Isolated empirical anomalies correlating with incident timeframe",
                evidence_items=evidence_items,
                anomalies_detected=len(evidence_items) > 0,
            )

        elif response_model is RCAAgentOutput:
            parsed_obj = RCAAgentOutput(
                hypotheses=[
                    Hypothesis(
                        id="HYP-01",
                        title="Redis Connection Pool Exhaustion from Deployment Configuration",
                        description=(
                            "Payment service deployment v2.4.1 reduced Redis max_connections from 100 to 10, "
                            "starving worker threads and causing P95 latency to jump to 2.8s."
                        ),
                        confidence=0.92,
                        supporting_evidence_ids=[
                            "EV-LOG-REDIS-01",
                            "EV-MET-LATENCY-02",
                            "EV-CODE-DIFF-03",
                        ],
                        contradicting_evidence_ids=[],
                        reasoning_summary=(
                            "The commit diff directly accounts for the connection pool saturation and the "
                            "exact timing of RedisTimeoutExceptions."
                        ),
                        suggested_validation=[
                            "Rollback deployment to v2.4.0 and verify latency drops"
                        ],
                    )
                ],
                primary_hypothesis_id="HYP-01",
                confidence_rationale="Evidence directly connects deployment diff to runtime connection limit breach.",
            )

        elif response_model is CritiqueResult:
            parsed_obj = CritiqueResult(
                decision="APPROVE",
                critique_notes=(
                    "Hypothesis is supported by multiple distinct evidence vectors (logs, metrics, and commit diffs). "
                    "Temporal correlation aligns perfectly with the deployment window. No contradicting evidence found."
                ),
                counter_hypotheses=[],
                required_evidence_queries=[],
            )
        else:
            # Fallback instantiation
            try:
                parsed_obj = response_model.model_validate({})
            except Exception:
                raise ValueError(
                    f"MockProvider cannot synthesize unsupported model: {response_model}"
                ) from None

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return LLMResponse[T](
            parsed=cast(T, parsed_obj),
            raw_content=parsed_obj.model_dump_json(),
            usage=TokenUsage(input_tokens=150, output_tokens=75, total_tokens=225, estimated_cost_usd=0.00045),
            provider=self.provider_name,
            model=self.model_name,
            latency_ms=latency,
        )

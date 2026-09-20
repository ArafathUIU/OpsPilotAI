"""Remediation Planning Agent formulating structured, risk-scored mitigation plans."""

from typing import Any

from src.agents.base import BaseAgent
from src.domain.state import Hypothesis, RemediationPlan
from src.llm.router import TaskTier
from src.safety.policy import RiskPolicyEngine

REMEDIATION_AGENT_SYSTEM_PROMPT = """You are the Lead SRE Remediation Planning Agent for OpsPilot AI.
Your responsibility:
1. Receive a confirmed, critic-approved root cause hypothesis and empirical evidence.
2. Formulate a structured, minimal, and non-destructive RemediationPlan.
3. For every proposed action:
   - Provide concrete parameters (e.g. target_version for rollback, config patch values, replica counts).
   - Provide an explicit, step-by-step rollback plan in case the action worsens system degradation.
   - Justify the causal rationale directly linking the action to the confirmed root cause.
4. DO NOT suggest dangerous wildcard deletes or unqualified database drops.
"""


class RemediationAgent(BaseAgent):
    """Generates disciplined remediation actions and rollback strategies."""

    def __init__(self, policy_engine: RiskPolicyEngine | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.policy_engine = policy_engine or RiskPolicyEngine()

    async def plan_remediation(
        self,
        incident_id: str,
        hypothesis: Hypothesis,
        target_services: list[str],
    ) -> RemediationPlan:
        """Formulates remediation plan and evaluates safety risk scores for all planned actions."""
        prompt = (
            f"Incident ID: {incident_id}\n"
            f"Affected Services: {target_services}\n"
            f"Confirmed Hypothesis: {hypothesis.title}\n"
            f"Hypothesis Description: {hypothesis.description}\n"
            f"Reasoning Summary: {hypothesis.reasoning_summary}\n"
            f"Suggested Validations: {hypothesis.suggested_validation}\n\n"
            "Formulate a structured RemediationPlan with concrete actions, precise parameters, and rollback plans."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=REMEDIATION_AGENT_SYSTEM_PROMPT,
            response_model=RemediationPlan,
            tier=TaskTier.REASONING,
        )
        raw_plan = response.parsed

        # Apply deterministic safety policy assessment to every action in the plan
        assessed_actions = [
            self.policy_engine.assess_action_risk(action, incident_id=incident_id)
            for action in raw_plan.actions
        ]

        return raw_plan.model_copy(
            update={
                "incident_id": incident_id,
                "hypothesis_id": hypothesis.id,
                "actions": assessed_actions,
            }
        )

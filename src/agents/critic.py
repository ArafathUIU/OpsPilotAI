"""Critic Agent challenging hypotheses and eliminating correlation-vs-causation fallacies."""

from src.agents.base import BaseAgent
from src.domain.state import CritiqueResult, Evidence, Hypothesis
from src.llm.router import TaskTier

CRITIC_SYSTEM_PROMPT = """You are the Adversarial Critic Agent for OpsPilot AI.
Your sole mission is to attempt to DISPROVE the proposed root-cause hypothesis.
Critique Checklist:
1. Is correlation being mistaken for causation?
2. Did the degradation begin before the cited deployment or event?
3. Are all cited supporting_evidence_ids actually grounded in the collected evidence?
4. Are alternative explanations possible (e.g. cloud provider outage, network partition)?
5. Has any contradictory evidence been ignored?

Return one of:
- APPROVE: The hypothesis is logically sound, causally proven, and fully backed by evidence.
- CHALLENGE: The hypothesis has major logical flaws or ignores contradictory evidence.
- NEEDS_MORE_EVIDENCE: The hypothesis is plausible, but key data (e.g. logs or diffs) is missing.
"""


class CriticAgent(BaseAgent):
    """Adversarially critiques hypotheses to prevent premature or false conclusions."""

    async def critique(self, hypothesis: Hypothesis, evidence: list[Evidence]) -> CritiqueResult:
        known_evidence_ids = {e.id for e in evidence}
        cited_ids = set(hypothesis.supporting_evidence_ids)

        # Deterministic check: verify that all cited IDs actually exist in collected evidence
        missing_ids = cited_ids - known_evidence_ids
        if missing_ids:
            return CritiqueResult(
                decision="CHALLENGE",
                critique_notes=(
                    f"Causal claim cites fabricated or uncollected evidence IDs: {list(missing_ids)}. "
                    "Hypothesis rejected due to hallucinated citations."
                ),
                counter_hypotheses=[],
                required_evidence_queries=[],
            )

        prompt = (
            f"Proposed Hypothesis:\n"
            f"Title: {hypothesis.title}\n"
            f"Description: {hypothesis.description}\n"
            f"Confidence: {hypothesis.confidence}\n"
            f"Reasoning: {hypothesis.reasoning_summary}\n"
            f"Supporting Evidence IDs Cited: {hypothesis.supporting_evidence_ids}\n\n"
            f"All Available Evidence:\n"
            f"{[e.model_dump(mode='json') for e in evidence]}\n\n"
            "Evaluate this hypothesis adversarially. Approve only if causally airtight."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=CRITIC_SYSTEM_PROMPT,
            response_model=CritiqueResult,
            tier=TaskTier.CRITIC,
        )
        return response.parsed

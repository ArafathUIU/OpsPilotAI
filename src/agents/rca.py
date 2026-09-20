"""Root Cause Analysis (RCA) Agent synthesizing multi-agent evidence into causal hypotheses."""

from src.agents.base import BaseAgent
from src.domain.state import Evidence, RCAAgentOutput
from src.llm.router import TaskTier

RCA_SYSTEM_PROMPT = """You are the Root Cause Analysis (RCA) Agent for OpsPilot AI.
Your responsibility:
1. Ingest all evidence items collected by the Log, Metrics, and Code analysts.
2. Formulate one or more causal hypotheses explaining the root cause of the incident.
3. STRICT REQUIREMENT: Every hypothesis MUST explicitly reference the Evidence IDs in `supporting_evidence_ids`.
4. Unsupported root-cause claims lacking cited evidence IDs are strictly forbidden.
5. Provide a rigorous reasoning summary and specify concrete validation steps.
"""


class RCAAgent(BaseAgent):
    """Synthesizes factual evidence into causal root-cause hypotheses."""

    async def analyze(self, incident_title: str, evidence: list[Evidence]) -> RCAAgentOutput:
        evidence_summary = [
            {
                "id": e.id,
                "type": e.type,
                "source": e.source,
                "observation": e.observation,
                "relevance": e.relevance_score,
                "raw_reference": e.raw_reference,
            }
            for e in evidence
        ]

        prompt = (
            f"Incident: {incident_title}\n\n"
            f"Collected Evidence Items ({len(evidence)} items):\n"
            f"{evidence_summary}\n\n"
            "Synthesize these observations into evidence-backed root-cause hypotheses. "
            "Ensure every claim cites valid Evidence IDs from the list above."
        )

        response = await self.invoke_structured(
            prompt=prompt,
            system_prompt=RCA_SYSTEM_PROMPT,
            response_model=RCAAgentOutput,
            tier=TaskTier.REASONING,
        )
        return response.parsed

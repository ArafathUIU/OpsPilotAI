"""LangGraph state machine for multi-agent incident response and root cause analysis."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.code_analyst import CodeAnalystAgent
from src.agents.critic import CriticAgent
from src.agents.log_analyst import LogAnalystAgent
from src.agents.memory_analyst import IncidentMemoryAgent
from src.agents.metrics_analyst import MetricsAnalystAgent
from src.agents.rca import RCAAgent
from src.agents.supervisor import SupervisorAgent
from src.domain.state import (
    IncidentState,
    InvestigationTask,
    TimelineEvent,
)
from src.observability.logging import get_logger

logger = get_logger(__name__)


class IncidentWorkflow:
    """Encapsulates LangGraph nodes, edges, and state machine compilation."""

    def __init__(
        self,
        supervisor: SupervisorAgent | None = None,
        log_analyst: LogAnalystAgent | None = None,
        metrics_analyst: MetricsAnalystAgent | None = None,
        code_analyst: CodeAnalystAgent | None = None,
        memory_analyst: IncidentMemoryAgent | None = None,
        rca: RCAAgent | None = None,
        critic: CriticAgent | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.log_analyst = log_analyst or LogAnalystAgent()
        self.metrics_analyst = metrics_analyst or MetricsAnalystAgent()
        self.code_analyst = code_analyst or CodeAnalystAgent()
        self.memory_analyst = memory_analyst or IncidentMemoryAgent()
        self.rca = rca or RCAAgent()
        self.critic = critic or CriticAgent()

    async def supervisor_node(self, state: IncidentState) -> dict[str, Any]:
        """Triage incident alert and build targeted investigation tasks."""
        logger.info(f"LangGraph: Supervisor analyzing incident [{state.incident_id}]")
        plan = await self.supervisor.plan_investigation(state)

        event = TimelineEvent(
            stage="PLANNING",
            actor="SupervisorAgent",
            message=f"Investigation planned with {len(plan.tasks)} targeted tasks.",
            metadata={"tasks": [t.model_dump(mode="json") for t in plan.tasks]},
        )

        return {
            "current_stage": "PLANNING",
            "investigation_tasks": plan.tasks,
            "timeline": [event],
        }

    async def log_analyst_node(self, state: IncidentState) -> dict[str, Any]:
        """Investigate application logs."""
        target_service = (
            state.affected_services[0] if state.affected_services else "payment-service"
        )
        task = InvestigationTask(
            task_id="task-log",
            agent_type="log_analyst",
            target_service=target_service,
            query_intent="Extract errors and stack traces",
        )
        logger.info(f"LangGraph: Log Analyst inspecting [{target_service}]")
        output = await self.log_analyst.investigate(task)

        event = TimelineEvent(
            stage="INVESTIGATING",
            actor="LogAnalystAgent",
            message=f"Log analysis completed. Found {len(output.evidence_items)} evidence items.",
        )
        return {
            "evidence": output.evidence_items,
            "timeline": [event],
        }

    async def metrics_analyst_node(self, state: IncidentState) -> dict[str, Any]:
        """Investigate time-series metrics."""
        target_service = (
            state.affected_services[0] if state.affected_services else "payment-service"
        )
        task = InvestigationTask(
            task_id="task-met",
            agent_type="metrics_analyst",
            target_service=target_service,
            query_intent="Inspect latency and active connections",
        )
        logger.info(f"LangGraph: Metrics Analyst inspecting [{target_service}]")
        output = await self.metrics_analyst.investigate(task)

        event = TimelineEvent(
            stage="INVESTIGATING",
            actor="MetricsAnalystAgent",
            message=f"Metrics analysis completed. Found {len(output.evidence_items)} evidence items.",
        )
        return {
            "evidence": output.evidence_items,
            "timeline": [event],
        }

    async def code_analyst_node(self, state: IncidentState) -> dict[str, Any]:
        """Investigate deployments and commit diffs."""
        target_service = (
            state.affected_services[0] if state.affected_services else "payment-service"
        )
        task = InvestigationTask(
            task_id="task-code",
            agent_type="code_analyst",
            target_service=target_service,
            query_intent="Inspect recent deployments and commit diffs",
        )
        logger.info(f"LangGraph: Code Analyst inspecting [{target_service}]")
        output = await self.code_analyst.investigate(task)

        event = TimelineEvent(
            stage="INVESTIGATING",
            actor="CodeAnalystAgent",
            message=f"Code & Deploy analysis completed. Found {len(output.evidence_items)} evidence items.",
        )
        return {
            "evidence": output.evidence_items,
            "timeline": [event],
        }

    async def memory_analyst_node(self, state: IncidentState) -> dict[str, Any]:
        """Investigate historical postmortems and episodic memory."""
        target_service = (
            state.affected_services[0] if state.affected_services else "payment-service"
        )
        task = InvestigationTask(
            task_id="task-mem",
            agent_type="memory_analyst",
            target_service=target_service,
            query_intent=f"Historical postmortems matching {state.title} on {target_service}",
        )
        logger.info(f"LangGraph: Memory Analyst searching past incidents for [{target_service}]")
        output = await self.memory_analyst.investigate(task)

        event = TimelineEvent(
            stage="INVESTIGATING",
            actor="IncidentMemoryAgent",
            message=f"Memory analysis completed. Found {len(output.evidence_items)} historical evidence items.",
        )
        return {
            "evidence": output.evidence_items,
            "timeline": [event],
        }

    async def join_evidence_node(self, state: IncidentState) -> dict[str, Any]:
        """Consolidate evidence collected across parallel analyst branches."""
        logger.info(f"LangGraph: Evidence joined. Total evidence items: {len(state.evidence)}")
        return {"current_stage": "INVESTIGATING"}

    async def rca_node(self, state: IncidentState) -> dict[str, Any]:
        """Synthesize causal root-cause hypotheses from gathered evidence."""
        logger.info(
            f"LangGraph: RCA synthesizing hypotheses from {len(state.evidence)} evidence items"
        )
        rca_output = await self.rca.analyze(state.title, state.evidence)

        selected_hypo = None
        for h in rca_output.hypotheses:
            if h.id == rca_output.primary_hypothesis_id:
                selected_hypo = h
                break
        if not selected_hypo and rca_output.hypotheses:
            selected_hypo = rca_output.hypotheses[0]

        event = TimelineEvent(
            stage="ANALYZING",
            actor="RCAAgent",
            message=f"Generated {len(rca_output.hypotheses)} hypotheses. Selected: '{selected_hypo.title if selected_hypo else 'None'}'",
        )

        return {
            "current_stage": "ANALYZING",
            "hypotheses": rca_output.hypotheses,
            "selected_hypothesis": selected_hypo,
            "timeline": [event],
        }

    async def critic_node(self, state: IncidentState) -> dict[str, Any]:
        """Adversarially evaluate the selected hypothesis."""
        if not state.selected_hypothesis:
            logger.warning("LangGraph: Critic found no selected hypothesis to evaluate.")
            return {"current_stage": "CRITIQUING"}

        logger.info(f"LangGraph: Critic evaluating hypothesis [{state.selected_hypothesis.id}]")
        critique = await self.critic.critique(state.selected_hypothesis, state.evidence)

        event = TimelineEvent(
            stage="CRITIQUING",
            actor="CriticAgent",
            message=f"Critic decision: {critique.decision}. Notes: {critique.critique_notes[:100]}...",
        )

        return {
            "current_stage": "CRITIQUING",
            "critique": critique,
            "timeline": [event],
            "iteration_count": state.iteration_count + 1,
        }

    def route_critic_decision(self, state: IncidentState) -> str:
        """Determines whether to loop back for more evidence or advance."""
        critique = state.critique
        if (
            critique
            and critique.decision == "NEEDS_MORE_EVIDENCE"
            and state.iteration_count < state.max_iterations
        ):
            logger.info(
                f"LangGraph: Looping back to investigation (iteration {state.iteration_count}/{state.max_iterations})"
            )
            return "supervisor"
        return "complete"

    def build_graph(self):
        """Assembles and compiles the LangGraph StateGraph."""
        builder = StateGraph(IncidentState)

        # Register nodes
        builder.add_node("supervisor", self.supervisor_node)
        builder.add_node("log_analyst", self.log_analyst_node)
        builder.add_node("metrics_analyst", self.metrics_analyst_node)
        builder.add_node("code_analyst", self.code_analyst_node)
        builder.add_node("memory_analyst", self.memory_analyst_node)
        builder.add_node("join_evidence", self.join_evidence_node)
        builder.add_node("rca", self.rca_node)
        builder.add_node("critic", self.critic_node)

        # Flow edges: START -> supervisor -> parallel analysts -> join -> rca -> critic
        builder.add_edge(START, "supervisor")
        builder.add_edge("supervisor", "log_analyst")
        builder.add_edge("supervisor", "metrics_analyst")
        builder.add_edge("supervisor", "code_analyst")
        builder.add_edge("supervisor", "memory_analyst")

        builder.add_edge("log_analyst", "join_evidence")
        builder.add_edge("metrics_analyst", "join_evidence")
        builder.add_edge("code_analyst", "join_evidence")
        builder.add_edge("memory_analyst", "join_evidence")

        builder.add_edge("join_evidence", "rca")
        builder.add_edge("rca", "critic")

        # Conditional loop from critic
        builder.add_conditional_edges(
            "critic",
            self.route_critic_decision,
            {
                "supervisor": "supervisor",
                "complete": END,
            },
        )

        return builder.compile()


# Helper to instantiate standard compiled graph
def create_incident_workflow() -> Any:
    return IncidentWorkflow().build_graph()

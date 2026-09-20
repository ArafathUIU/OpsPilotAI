"""LangGraph state machine for multi-agent incident response and root cause analysis."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.code_analyst import CodeAnalystAgent
from src.agents.critic import CriticAgent
from src.agents.log_analyst import LogAnalystAgent
from src.agents.memory_analyst import IncidentMemoryAgent
from src.agents.metrics_analyst import MetricsAnalystAgent
from src.agents.rca import RCAAgent
from src.agents.remediation_agent import RemediationAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.verifier import VerificationAgent
from src.domain.state import (
    ActionExecutionResult,
    IncidentState,
    InvestigationTask,
    TimelineEvent,
)
from src.observability.logging import get_logger
from src.safety.execution_runner import ExecutionRunner

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
        remediation_agent: RemediationAgent | None = None,
        verifier: VerificationAgent | None = None,
        execution_runner: ExecutionRunner | None = None,
    ) -> None:
        self.supervisor = supervisor or SupervisorAgent()
        self.log_analyst = log_analyst or LogAnalystAgent()
        self.metrics_analyst = metrics_analyst or MetricsAnalystAgent()
        self.code_analyst = code_analyst or CodeAnalystAgent()
        self.memory_analyst = memory_analyst or IncidentMemoryAgent()
        self.rca = rca or RCAAgent()
        self.critic = critic or CriticAgent()
        self.remediation_agent = remediation_agent or RemediationAgent()
        self.verifier = verifier or VerificationAgent()
        self.execution_runner = execution_runner or ExecutionRunner()

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

    async def remediation_planning_node(self, state: IncidentState) -> dict[str, Any]:
        """Formulate risk-assessed remediation plan for the confirmed hypothesis."""
        if not state.selected_hypothesis:
            logger.warning("LangGraph: No selected hypothesis to remediate.")
            return {"current_stage": "FAILED"}

        logger.info(f"LangGraph: Planning remediation for [{state.selected_hypothesis.id}]")
        plan = await self.remediation_agent.plan_remediation(
            incident_id=state.incident_id,
            hypothesis=state.selected_hypothesis,
            target_services=state.affected_services,
        )

        event = TimelineEvent(
            stage="REMEDIATION_PLANNING",
            actor="RemediationAgent",
            message=f"Formulated remediation plan with {len(plan.actions)} actions. Summary: {plan.summary}",
            metadata={"actions": [a.model_dump(mode="json") for a in plan.actions]},
        )
        return {
            "current_stage": "REMEDIATION_PLANNING",
            "remediation_plan": plan,
            "pending_approvals": [a for a in plan.actions if a.requires_approval],
            "timeline": [event],
        }

    async def execution_node(self, state: IncidentState) -> dict[str, Any]:
        """Execute permitted remediation actions with idempotency tracking."""
        if not state.remediation_plan or not state.remediation_plan.actions:
            logger.warning("LangGraph: No remediation plan to execute.")
            return {"current_stage": "FAILED"}

        logger.info(f"LangGraph: Executing remediation plan for [{state.incident_id}]")
        results: list[ActionExecutionResult] = []
        events: list[TimelineEvent] = []

        for action in state.remediation_plan.actions:
            res = await self.execution_runner.execute_action(action, caller_role="OPERATOR")
            results.append(res)
            event = TimelineEvent(
                stage="EXECUTING",
                actor="ExecutionRunner",
                message=f"Action [{action.action_id}] status: {res.status}. Output: {res.output}",
                metadata={"action_id": action.action_id, "duration_ms": res.duration_ms},
            )
            events.append(event)

        return {
            "current_stage": "EXECUTING",
            "execution_results": results,
            "timeline": events,
        }

    async def verification_node(self, state: IncidentState) -> dict[str, Any]:
        """Empirically verify telemetry recovery and trigger rollback if degraded."""
        target_service = (
            state.affected_services[0] if state.affected_services else "payment-service"
        )
        executed_action_id = (
            state.execution_results[-1].action_id if state.execution_results else "ACT-UNKNOWN"
        )

        logger.info(
            f"LangGraph: Verifying recovery for [{target_service}] after [{executed_action_id}]"
        )
        assessment = await self.verifier.verify_recovery(target_service, executed_action_id)

        events: list[TimelineEvent] = []
        event = TimelineEvent(
            stage="VERIFYING",
            actor="VerificationAgent",
            message=f"Verification status: {assessment.status}. {assessment.explanation}",
            metadata={
                "status": assessment.status,
                "rollback_recommended": assessment.rollback_recommended,
            },
        )
        events.append(event)

        # Automated compensation rollback if degradation detected
        if (
            assessment.rollback_recommended
            and state.remediation_plan
            and state.remediation_plan.actions
        ):
            last_action = state.remediation_plan.actions[-1]
            rb_res = await self.execution_runner.execute_rollback(last_action)
            rb_event = TimelineEvent(
                stage="FAILED",
                actor="ExecutionRunner",
                message=f"Executed automatic rollback for [{last_action.action_id}]: {rb_res.output}",
            )
            events.append(rb_event)
            return {
                "current_stage": "FAILED",
                "verification": assessment,
                "timeline": events,
            }

        next_stage = "RESOLVED" if assessment.status == "RECOVERED" else "INVESTIGATING"
        return {
            "current_stage": next_stage,
            "verification": assessment,
            "timeline": events,
        }

    def route_critic_decision(self, state: IncidentState) -> str:
        """Determines whether to loop back for more evidence, advance to remediation, or complete."""
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
        elif critique and critique.decision == "APPROVE":
            return "remediation"
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
        builder.add_node("remediation_planning", self.remediation_planning_node)
        builder.add_node("execution", self.execution_node)
        builder.add_node("verification", self.verification_node)

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
                "remediation": "remediation_planning",
                "complete": END,
            },
        )

        # Remediation lifecycle edges
        builder.add_edge("remediation_planning", "execution")
        builder.add_edge("execution", "verification")
        builder.add_edge("verification", END)

        return builder.compile()


# Helper to instantiate standard compiled graph
def create_incident_workflow() -> Any:
    return IncidentWorkflow().build_graph()

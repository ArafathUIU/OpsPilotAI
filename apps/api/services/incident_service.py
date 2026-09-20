"""Central application service coordinating incident lifecycle, agent workflows, and SSE broadcasts."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.schemas.approval import ApprovalDecisionRequest, ApprovalRequestResponse
from apps.api.schemas.incident import (
    EvidenceResponse,
    HypothesisResponse,
    IncidentResponse,
    TimelineEventResponse,
)
from apps.api.schemas.report import PostmortemReportResponse
from apps.api.services.event_stream import EventBroker, default_event_broker
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
    ApprovalDecision,
    IncidentState,
    TimelineEvent,
)
from src.llm.adapters.mock_provider import MockLLMProvider
from src.llm.router import ModelRouter
from src.memory.episodic import EpisodicMemoryManager
from src.observability.logging import get_logger
from src.orchestration.graph import IncidentWorkflow
from src.reporting.postmortem import PostmortemGenerator
from src.safety.execution_runner import ExecutionRunner
from src.safety.policy import RiskPolicyEngine

logger = get_logger(__name__)


class IncidentService:
    """Manages active incidents, executes LangGraph workflows, and synchronizes real-time state."""

    def __init__(
        self,
        event_broker: EventBroker | None = None,
        memory_manager: EpisodicMemoryManager | None = None,
    ) -> None:
        self.event_broker = event_broker or default_event_broker
        self.memory_manager = memory_manager or EpisodicMemoryManager()
        self.policy_engine = RiskPolicyEngine()
        self.report_generator = PostmortemGenerator(memory_manager=self.memory_manager)
        self._incidents: dict[str, IncidentState] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def _build_workflow(self) -> Any:
        router = ModelRouter([MockLLMProvider()])
        workflow = IncidentWorkflow(
            supervisor=SupervisorAgent(router=router),
            log_analyst=LogAnalystAgent(router=router),
            metrics_analyst=MetricsAnalystAgent(router=router),
            code_analyst=CodeAnalystAgent(router=router),
            memory_analyst=IncidentMemoryAgent(router=router),
            rca=RCAAgent(router=router),
            critic=CriticAgent(router=router),
            remediation_agent=RemediationAgent(router=router),
            verifier=VerificationAgent(router=router),
            execution_runner=ExecutionRunner(),
        )
        return workflow.build_graph()

    def create_incident(
        self,
        title: str,
        severity: str,
        affected_services: list[str],
        symptoms: str = "",
        auto_remediate: bool = False,
    ) -> IncidentResponse:
        """Provisions a new incident and launches background LangGraph investigation."""
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        initial_event = TimelineEvent(
            stage="CREATED",
            actor="System",
            message=f"Incident alert received: {title}",
            metadata={"symptoms": symptoms, "auto_remediate": auto_remediate},
        )

        state = IncidentState(
            incident_id=incident_id,
            title=title,
            severity=severity,  # type: ignore[arg-type]
            affected_services=affected_services,
            timeline=[initial_event],
        )

        self._incidents[incident_id] = state

        # Launch background investigation pipeline if an event loop is running
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_investigation(incident_id))
            self._tasks[incident_id] = task
        except RuntimeError:
            # Synchronous context or unit test without running loop
            pass

        logger.info(f"Incident [{incident_id}] initialized. Background investigation launched.")
        return self._to_incident_response(state)

    async def _run_investigation(self, incident_id: str) -> None:
        """Background coroutine streaming LangGraph agent execution and updating incident state."""
        state = self._incidents.get(incident_id)
        if not state:
            return

        graph = self._build_workflow()

        try:
            await self.event_broker.publish(
                incident_id=incident_id,
                event_type="stage_change",
                payload={"stage": "PLANNING", "message": "Supervisor initiating triage"},
            )

            # Stream LangGraph state node execution
            async for step_output in graph.astream(state):
                for node_name, node_state in step_output.items():
                    logger.info(f"LangGraph node completed: [{node_name}] for [{incident_id}]")

                    # Merge node state into active incident state
                    if isinstance(node_state, dict):
                        for k, v in node_state.items():
                            if k == "evidence" and isinstance(v, list):
                                state.evidence.extend(v)
                                for item in v:
                                    await self.event_broker.publish(
                                        incident_id=incident_id,
                                        event_type="evidence_found",
                                        payload=item.model_dump(mode="json"),
                                    )
                            elif k == "timeline" and isinstance(v, list):
                                state.timeline.extend(v)
                                for t_event in v:
                                    await self.event_broker.publish(
                                        incident_id=incident_id,
                                        event_type="agent_thought",
                                        payload=t_event.model_dump(mode="json"),
                                    )
                            elif hasattr(state, k):
                                setattr(state, k, v)

                    # Broadcast stage change
                    await self.event_broker.publish(
                        incident_id=incident_id,
                        event_type="stage_change",
                        payload={"stage": state.current_stage, "node": node_name},
                    )

            # Signal final status
            if state.current_stage == "RESOLVED":
                await self.event_broker.publish(
                    incident_id=incident_id,
                    event_type="resolved",
                    payload={"incident_id": incident_id, "status": "RESOLVED"},
                )
                # Auto-index postmortem to memory
                report = self.report_generator.generate_report(state)
                await self.report_generator.auto_index_to_memory(report)

        except Exception as exc:
            logger.error(f"Investigation failed for [{incident_id}]: {exc}", exc_info=True)
            state.current_stage = "FAILED"
            state.errors.append(str(exc))
            await self.event_broker.publish(
                incident_id=incident_id,
                event_type="failed",
                payload={"error": str(exc)},
            )

    def get_incident(self, incident_id: str) -> IncidentResponse | None:
        state = self._incidents.get(incident_id)
        return self._to_incident_response(state) if state else None

    def list_incidents(
        self,
        severity: str | None = None,
        stage: str | None = None,
        service: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IncidentResponse]:
        results = list(self._incidents.values())
        if severity:
            results = [s for s in results if s.severity.upper() == severity.upper()]
        if stage:
            results = [s for s in results if s.current_stage.upper() == stage.upper()]
        if service:
            results = [
                s for s in results if service.lower() in [svc.lower() for svc in s.affected_services]
            ]
        # Order by created_at descending
        results.sort(key=lambda s: s.created_at, reverse=True)
        paginated = results[offset : offset + limit]
        return [self._to_incident_response(s) for s in paginated]

    def get_evidence(self, incident_id: str) -> list[EvidenceResponse]:
        state = self._incidents.get(incident_id)
        if not state:
            return []
        return [
            EvidenceResponse(
                id=e.id,
                type=e.type,
                source=e.source,
                timestamp=e.timestamp,
                observation=e.observation,
                raw_reference=e.raw_reference,
                relevance_score=e.relevance_score,
                metadata=e.metadata,
            )
            for e in state.evidence
        ]

    def get_hypotheses(self, incident_id: str) -> list[HypothesisResponse]:
        state = self._incidents.get(incident_id)
        if not state:
            return []
        return [
            HypothesisResponse(
                id=h.id,
                title=h.title,
                description=h.description,
                confidence=h.confidence,
                supporting_evidence_ids=h.supporting_evidence_ids,
                contradicting_evidence_ids=h.contradicting_evidence_ids,
                reasoning_summary=h.reasoning_summary,
            )
            for h in state.hypotheses
        ]

    def get_timeline(self, incident_id: str) -> list[TimelineEventResponse]:
        state = self._incidents.get(incident_id)
        if not state:
            return []
        return [
            TimelineEventResponse(
                timestamp=t.timestamp,
                stage=t.stage,
                actor=t.actor,
                message=t.message,
                metadata=t.metadata,
            )
            for t in state.timeline
        ]

    def get_approvals(self, incident_id: str) -> list[ApprovalRequestResponse]:
        state = self._incidents.get(incident_id)
        if not state or not state.remediation_plan:
            return []

        decisions_by_action = {d.action_id: d for d in state.approval_decisions}

        approvals: list[ApprovalRequestResponse] = []
        for a in state.remediation_plan.actions:
            dec = decisions_by_action.get(a.action_id)
            status_val = dec.decision if dec else ("PENDING" if a.requires_approval else "AUTO_APPROVED")
            approvals.append(
                ApprovalRequestResponse(
                    id=f"appr-{a.action_id}",
                    incident_id=incident_id,
                    action_id=a.action_id,
                    action_type=a.action_type,
                    target_service=a.target_service,
                    risk_level=a.risk_tier,
                    status=status_val,
                    description=a.description,
                    rollback_plan=a.rollback_plan,
                    parameters=a.parameters,
                    created_at=state.created_at,
                    responded_at=dec.decided_at if dec else None,
                    approver_id=dec.decided_by if dec else None,
                    comment=dec.reason if dec else None,
                )
            )
        return approvals

    def submit_approval(
        self,
        incident_id: str,
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> ApprovalRequestResponse:
        state = self._incidents.get(incident_id)
        if not state or not state.remediation_plan:
            raise ValueError(f"No remediation plan found for incident {incident_id}")

        target_action = None
        for a in state.remediation_plan.actions:
            if f"appr-{a.action_id}" == approval_id or a.action_id == approval_id:
                target_action = a
                break

        if not target_action:
            raise ValueError(f"Approval {approval_id} not found in incident {incident_id}")

        # Guard against duplicate or conflicting approval submissions
        existing_decision = next(
            (d for d in state.approval_decisions if d.action_id == target_action.action_id),
            None,
        )
        if existing_decision:
            raise ValueError(
                f"Action [{target_action.action_id}] was already {existing_decision.decision} by [{existing_decision.decided_by}]"
            )

        # Enforce RBAC authorization
        authorized, msg = self.policy_engine.authorize_approval(
            target_action, request.approver_role
        )
        if not authorized:
            raise PermissionError(f"Authorization denied: {msg}")

        decision = ApprovalDecision(
            action_id=target_action.action_id,
            decision=request.decision,
            decided_by=request.approver_id,
            reason=request.reason,
            modified_parameters=request.modified_parameters,
            decided_at=datetime.now(UTC),
        )
        state.approval_decisions.append(decision)

        # Notify event stream
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.event_broker.publish(
                    incident_id=incident_id,
                    event_type="approval_decision",
                    payload=decision.model_dump(mode="json"),
                )
            )
        except RuntimeError:
            pass

        return ApprovalRequestResponse(
            id=approval_id,
            incident_id=incident_id,
            action_id=target_action.action_id,
            action_type=target_action.action_type,
            target_service=target_action.target_service,
            risk_level=target_action.risk_tier,
            status=request.decision,
            description=target_action.description,
            rollback_plan=target_action.rollback_plan,
            parameters=target_action.parameters,
            created_at=state.created_at,
            responded_at=decision.decided_at,
            approver_id=request.approver_id,
            comment=request.reason,
        )

    def generate_postmortem_report(self, incident_id: str) -> PostmortemReportResponse:
        state = self._incidents.get(incident_id)
        if not state:
            raise ValueError(f"Incident {incident_id} not found")
        return self.report_generator.generate_report(state)

    def _to_incident_response(self, state: IncidentState) -> IncidentResponse:
        return IncidentResponse(
            id=state.incident_id,
            title=state.title,
            severity=state.severity,
            current_stage=state.current_stage,
            affected_services=state.affected_services,
            created_at=state.created_at,
            resolved_at=datetime.now(UTC) if state.current_stage == "RESOLVED" else None,
            confidence_score=state.selected_hypothesis.confidence
            if state.selected_hypothesis
            else 0.0,
            evidence_count=len(state.evidence),
            hypotheses_count=len(state.hypotheses),
            selected_hypothesis_title=state.selected_hypothesis.title
            if state.selected_hypothesis
            else None,
            verification_status=state.verification.status if state.verification else None,
        )


# Global incident service singleton
default_incident_service = IncidentService()

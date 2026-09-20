"""REST API and SSE streaming routes for incidents, evidence, approvals, and postmortems."""

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from apps.api.schemas.approval import ApprovalDecisionRequest, ApprovalRequestResponse
from apps.api.schemas.incident import (
    EvidenceResponse,
    HypothesisResponse,
    IncidentCreateRequest,
    IncidentResponse,
    TimelineEventResponse,
)
from apps.api.schemas.report import PostmortemReportResponse
from apps.api.services.event_stream import default_event_broker
from apps.api.services.incident_service import default_incident_service
from src.observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or trigger an incident",
)
async def create_incident(request: IncidentCreateRequest) -> IncidentResponse:
    incident = default_incident_service.create_incident(
        title=request.title,
        severity=request.severity,
        affected_services=request.affected_services,
        symptoms=request.symptoms,
        auto_remediate=request.auto_remediate,
    )
    return incident


@router.get(
    "",
    response_model=list[IncidentResponse],
    summary="List all incidents with optional filtering and pagination",
)
async def list_incidents(
    severity: str | None = None,
    stage: str | None = None,
    service: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IncidentResponse]:
    return default_incident_service.list_incidents(
        severity=severity,
        stage=stage,
        service=service,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get incident details",
)
async def get_incident(incident_id: str) -> IncidentResponse:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return incident


@router.get(
    "/{incident_id}/evidence",
    response_model=list[EvidenceResponse],
    summary="Get empirical evidence items for an incident",
)
async def get_incident_evidence(incident_id: str) -> list[EvidenceResponse]:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return default_incident_service.get_evidence(incident_id)


@router.get(
    "/{incident_id}/hypotheses",
    response_model=list[HypothesisResponse],
    summary="Get causal hypotheses generated for an incident",
)
async def get_incident_hypotheses(incident_id: str) -> list[HypothesisResponse]:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return default_incident_service.get_hypotheses(incident_id)


@router.get(
    "/{incident_id}/timeline",
    response_model=list[TimelineEventResponse],
    summary="Get the complete audit timeline of agent events",
)
async def get_incident_timeline(incident_id: str) -> list[TimelineEventResponse]:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return default_incident_service.get_timeline(incident_id)


@router.get(
    "/{incident_id}/stream",
    summary="Subscribe to real-time Server-Sent Events (SSE) stream",
)
async def stream_incident_events(incident_id: str) -> EventSourceResponse:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return EventSourceResponse(default_event_broker.subscribe(incident_id))


@router.get(
    "/{incident_id}/approvals",
    response_model=list[ApprovalRequestResponse],
    summary="List pending and completed approval requests",
)
async def get_incident_approvals(incident_id: str) -> list[ApprovalRequestResponse]:
    incident = default_incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )
    return default_incident_service.get_approvals(incident_id)


@router.post(
    "/{incident_id}/approvals/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Submit human approval decision (APPROVED, REJECTED, MODIFIED)",
)
async def submit_approval_decision(
    incident_id: str,
    approval_id: str,
    decision: ApprovalDecisionRequest,
) -> ApprovalRequestResponse:
    try:
        return default_incident_service.submit_approval(
            incident_id=incident_id,
            approval_id=approval_id,
            request=decision,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe)) from pe
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve)) from ve


@router.get(
    "/{incident_id}/report",
    response_model=PostmortemReportResponse,
    summary="Get postmortem report for an incident",
)
async def get_incident_report(incident_id: str) -> PostmortemReportResponse:
    try:
        return default_incident_service.generate_postmortem_report(incident_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve)) from ve


@router.post(
    "/{incident_id}/report",
    response_model=PostmortemReportResponse,
    summary="Generate and publish postmortem report",
)
async def generate_incident_report(incident_id: str) -> PostmortemReportResponse:
    try:
        report = default_incident_service.generate_postmortem_report(incident_id)
        # Preserve into episodic memory
        await default_incident_service.report_generator.auto_index_to_memory(report)
        return report
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve)) from ve

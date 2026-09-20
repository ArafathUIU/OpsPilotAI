"""Mock code repository and deployment provider interface."""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field


class CommitRecord(BaseModel):
    commit_sha: str
    service: str
    author: str
    message: str
    timestamp: datetime
    changed_files: list[str] = Field(default_factory=list)
    diff: str = ""


class DeploymentEvent(BaseModel):
    deployment_id: str
    service: str
    version: str
    previous_version: str
    timestamp: datetime
    deployed_by: str
    status: str = "SUCCESS"  # SUCCESS, FAILED, ROLLED_BACK
    commit_sha: str
    config_changes: dict = Field(default_factory=dict)


class CodeRepositoryProvider(Protocol):
    """Protocol defining repository query capabilities for Code Analyst Agent."""

    def get_recent_commits(
        self, service: str, limit: int = 5, since: datetime | None = None
    ) -> list[CommitRecord]: ...

    def get_commit_diff(self, commit_sha: str) -> str: ...

    def get_recent_deployments(
        self, service: str | None = None, limit: int = 5, since: datetime | None = None
    ) -> list[DeploymentEvent]: ...


class MockCodeRepository(CodeRepositoryProvider):
    """In-memory implementation of code repository and deployment tracker."""

    def __init__(self) -> None:
        self.commits: list[CommitRecord] = []
        self.deployments: list[DeploymentEvent] = []

    def record_commit(self, commit: CommitRecord) -> None:
        self.commits.append(commit)

    def record_deployment(self, deployment: DeploymentEvent) -> None:
        self.deployments.append(deployment)

    def get_recent_commits(
        self, service: str, limit: int = 5, since: datetime | None = None
    ) -> list[CommitRecord]:
        results = [c for c in self.commits if c.service == service]
        if since:
            results = [c for c in results if c.timestamp >= since]
        results.sort(key=lambda c: c.timestamp, reverse=True)
        return results[:limit]

    def get_commit_diff(self, commit_sha: str) -> str:
        for c in self.commits:
            if c.commit_sha == commit_sha or c.commit_sha.startswith(commit_sha):
                return c.diff
        return ""

    def get_recent_deployments(
        self, service: str | None = None, limit: int = 5, since: datetime | None = None
    ) -> list[DeploymentEvent]:
        results = self.deployments
        if service:
            results = [d for d in results if d.service == service]
        if since:
            results = [d for d in results if d.timestamp >= since]
        results.sort(key=lambda d: d.timestamp, reverse=True)
        return results[:limit]

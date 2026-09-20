"""Code repository and deployment history inspection tools."""

from typing import Any

from simulator.engine import default_simulator
from src.tools.base import BaseTool


class GetRecentDeploymentsTool(BaseTool):
    name = "get_recent_deployments"
    description = "Retrieves recent deployment events, versions, deployed commit SHAs, and configuration diffs."
    required_role = "VIEWER"

    async def _run(self, service: str | None = None, limit: int = 5, **kwargs: Any) -> list[dict]:
        events = default_simulator.repository.get_recent_deployments(service=service, limit=limit)
        return [e.model_dump(mode="json") for e in events]


class GetRecentCommitsTool(BaseTool):
    name = "get_recent_commits"
    description = "Retrieves recent git commits for a service including commit message, author, and timestamp."
    required_role = "VIEWER"

    async def _run(self, service: str, limit: int = 5, **kwargs: Any) -> list[dict]:
        commits = default_simulator.repository.get_recent_commits(service=service, limit=limit)
        return [c.model_dump(mode="json") for c in commits]


class GetCommitDiffTool(BaseTool):
    name = "get_commit_diff"
    description = "Retrieves the unified git code/config diff for a specific commit SHA."
    required_role = "VIEWER"

    async def _run(self, commit_sha: str, **kwargs: Any) -> dict:
        diff = default_simulator.repository.get_commit_diff(commit_sha)
        return {"commit_sha": commit_sha, "diff": diff}

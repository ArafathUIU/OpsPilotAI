"""Unit tests for ToolRegistry and deterministic RBAC authorization."""

import pytest

from src.tools.base import BaseTool
from src.tools.registry import ToolRegistry


class DummyAdminTool(BaseTool):
    name = "dummy_admin_action"
    description = "A privileged action requiring ADMIN role"
    required_role = "ADMIN"

    async def _run(self, **kwargs):
        return {"status": "executed"}


@pytest.mark.asyncio
async def test_tool_registry_rbac_enforcement():
    registry = ToolRegistry()
    registry.register(DummyAdminTool())

    # 1. Caller with VIEWER role should be denied
    denied_res = await registry.invoke(
        "dummy_admin_action",
        {},
        caller_role="VIEWER",
        agent_name="TestAgent",
    )
    assert denied_res.status == "PERMISSION_DENIED"
    assert "Access Denied" in (denied_res.error_message or "")

    # 2. Caller with ADMIN role should succeed
    allowed_res = await registry.invoke(
        "dummy_admin_action",
        {},
        caller_role="ADMIN",
        agent_name="TestAgent",
    )
    assert allowed_res.status == "SUCCESS"
    assert allowed_res.data == {"status": "executed"}


def test_tool_parameter_sanitization():
    registry = ToolRegistry()
    raw_params = {
        "service": "payment-service",
        "api_key": "sk-secret-token-12345",
        "db_password": "super_secret_password",
        "normal_limit": 50,
    }
    sanitized = registry._sanitize_params(raw_params)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["db_password"] == "[REDACTED]"
    assert sanitized["service"] == "payment-service"
    assert sanitized["normal_limit"] == 50

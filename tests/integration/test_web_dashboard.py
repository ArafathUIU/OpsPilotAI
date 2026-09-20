"""Integration tests verifying the delivery of the web dashboard and static assets."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_dashboard_root_html_served(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "OpsPilot" in response.text
    assert "Autonomous Incident Response Platform" in response.text


def test_dashboard_css_assets_served(client: TestClient):
    for css_file in ["css/main.css", "css/components.css", "css/topology.css"]:
        resp = client.get(f"/{css_file}")
        assert resp.status_code == 200, f"Failed loading {css_file}"
        assert "text/css" in resp.headers.get("content-type", "")


def test_dashboard_js_modules_served(client: TestClient):
    for js_file in [
        "js/app.js",
        "js/api.js",
        "js/sse.js",
        "js/topology.js",
        "js/components/incidentList.js",
        "js/components/agentStream.js",
        "js/components/evidenceViewer.js",
        "js/components/rcaCards.js",
        "js/components/approvalModal.js",
        "js/components/postmortemViewer.js",
    ]:
        resp = client.get(f"/{js_file}")
        assert resp.status_code == 200, f"Failed loading {js_file}"


def test_api_routes_not_shadowed_by_static_mount(client: TestClient):
    # Verify /health and /api/v1/... routes take precedence over static mount
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    incidents_resp = client.get("/api/v1/incidents")
    assert incidents_resp.status_code == 200
    assert isinstance(incidents_resp.json(), list)

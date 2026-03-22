from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import INFEASIBLE_PAYLOAD, SAMPLE_CLIENT_A


def test_post_schedule_success() -> None:
    client = TestClient(app)
    response = client.post("/schedule", json=SAMPLE_CLIENT_A)
    assert response.status_code == 200
    data = response.json()
    assert "assignments" in data and "kpis" in data
    assert len(data["assignments"]) > 0
    assert "tardiness_minutes" in data["kpis"]


def test_post_schedule_infeasible() -> None:
    client = TestClient(app)
    response = client.post("/schedule", json=INFEASIBLE_PAYLOAD)
    assert response.status_code == 422
    body = response.json()
    assert body.get("error") == "infeasible"
    assert isinstance(body.get("why"), list)
    assert len(body["why"]) >= 1

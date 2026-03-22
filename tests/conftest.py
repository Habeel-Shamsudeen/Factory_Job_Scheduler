from __future__ import annotations

import pytest

from adapter.client_a import client_a_to_model
from api.schemas import ScheduleRequest
from core.models import Model

SAMPLE_CLIENT_A: dict = {
    "horizon": {
        "start": "2025-11-03T08:00:00",
        "end": "2025-11-03T16:00:00",
    },
    "resources": [
        {
            "id": "Fill-1",
            "capabilities": ["fill"],
            "calendar": [
                ["2025-11-03T08:00:00", "2025-11-03T12:00:00"],
                ["2025-11-03T12:30:00", "2025-11-03T16:00:00"],
            ],
        },
        {
            "id": "Fill-2",
            "capabilities": ["fill"],
            "calendar": [["2025-11-03T08:00:00", "2025-11-03T16:00:00"]],
        },
        {
            "id": "Label-1",
            "capabilities": ["label"],
            "calendar": [["2025-11-03T08:00:00", "2025-11-03T16:00:00"]],
        },
        {
            "id": "Pack-1",
            "capabilities": ["pack"],
            "calendar": [["2025-11-03T08:00:00", "2025-11-03T16:00:00"]],
        },
    ],
    "changeover_matrix_minutes": {
        "values": {
            "standard->standard": 0,
            "standard->premium": 20,
            "premium->standard": 20,
            "premium->premium": 0,
        }
    },
    "products": [
        {
            "id": "P-100",
            "family": "standard",
            "due": "2025-11-03T12:30:00",
            "route": [
                {"capability": "fill", "duration_minutes": 30},
                {"capability": "label", "duration_minutes": 20},
                {"capability": "pack", "duration_minutes": 15},
            ],
        },
        {
            "id": "P-101",
            "family": "premium",
            "due": "2025-11-03T15:00:00",
            "route": [
                {"capability": "fill", "duration_minutes": 35},
                {"capability": "label", "duration_minutes": 25},
                {"capability": "pack", "duration_minutes": 15},
            ],
        },
        {
            "id": "P-102",
            "family": "standard",
            "due": "2025-11-03T13:30:00",
            "route": [
                {"capability": "fill", "duration_minutes": 25},
                {"capability": "label", "duration_minutes": 20},
            ],
        },
        {
            "id": "P-103",
            "family": "premium",
            "due": "2025-11-03T14:00:00",
            "route": [
                {"capability": "fill", "duration_minutes": 30},
                {"capability": "label", "duration_minutes": 20},
                {"capability": "pack", "duration_minutes": 15},
            ],
        },
    ],
    "settings": {"time_limit_seconds": 30, "objective_mode": "min_tardiness"},
}


@pytest.fixture
def client_a_request() -> ScheduleRequest:
    return ScheduleRequest.model_validate(SAMPLE_CLIENT_A)


@pytest.fixture
def client_a_model(client_a_request: ScheduleRequest) -> Model:
    return client_a_to_model(client_a_request)


INFEASIBLE_PAYLOAD: dict = {
    "horizon": {
        "start": "2025-11-03T08:00:00",
        "end": "2025-11-03T09:00:00",
    },
    "resources": [
        {
            "id": "OnlyFill",
            "capabilities": ["fill"],
            "calendar": [["2025-11-03T08:00:00", "2025-11-03T09:00:00"]],
        },
    ],
    "changeover_matrix_minutes": {
        "values": {
            "standard->standard": 0,
            "standard->premium": 0,
            "premium->standard": 0,
            "premium->premium": 0,
        }
    },
    "products": [
        {
            "id": "TooBig",
            "family": "standard",
            "due": "2025-11-03T08:30:00",
            "route": [{"capability": "fill", "duration_minutes": 500}],
        },
    ],
    "settings": {"time_limit_seconds": 30, "objective_mode": "min_tardiness"},
}


@pytest.fixture
def infeasible_request() -> ScheduleRequest:
    return ScheduleRequest.model_validate(INFEASIBLE_PAYLOAD)


@pytest.fixture
def infeasible_model(infeasible_request: ScheduleRequest) -> Model:
    return client_a_to_model(infeasible_request)

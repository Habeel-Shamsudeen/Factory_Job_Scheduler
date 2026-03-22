from __future__ import annotations

import pytest

from core.errors import InfeasibleError
from core.models import Model
from kpi.calculate import calculate_kpis
from scheduler.heuristic import heuristic_schedule
from tests.support import verify_schedule


def test_schedule_invariants_client_a(client_a_model: Model) -> None:
    assignments = heuristic_schedule(client_a_model)
    assert len(assignments) == sum(len(j.steps) for j in client_a_model.jobs)
    verify_schedule(assignments, client_a_model)


def test_kpis_match_recomputed_from_assignments(client_a_model: Model) -> None:
    assignments = heuristic_schedule(client_a_model)
    kpis = calculate_kpis(assignments, client_a_model)

    earliest = min(a.start for a in assignments)
    latest = max(a.end for a in assignments)
    assert kpis.makespan_minutes == latest - earliest

    due = {j.id: j.due for j in client_a_model.jobs}
    completion: dict[str, int] = {}
    for a in assignments:
        completion[a.product] = max(completion.get(a.product, 0), a.end)
    tardy = sum(
        max(0, completion.get(jid, 0) - due[jid]) for jid in due
    )
    assert kpis.tardiness_minutes == tardy
    assert abs(kpis.tardiness_minutes - tardy) <= 1


def test_infeasible_raises_infeasible_error(infeasible_model: Model) -> None:
    with pytest.raises(InfeasibleError) as exc:
        heuristic_schedule(infeasible_model)
    assert exc.value.reasons
    assert any(len(s) > 0 for s in exc.value.reasons)


def test_determinism_same_input_twice(client_a_model: Model) -> None:
    a1 = heuristic_schedule(client_a_model)
    a2 = heuristic_schedule(client_a_model)
    key = lambda x: (x.resource, x.product, x.step_index, x.start, x.end)
    assert sorted(a1, key=key) == sorted(a2, key=key)
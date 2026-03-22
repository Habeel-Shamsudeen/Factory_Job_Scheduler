from __future__ import annotations

from collections import defaultdict
from typing import List

from core.models import Assignment, Model, Resource


def assert_no_resource_overlap(assignments: List[Assignment]) -> None:
    by_resource: dict[str, list[Assignment]] = defaultdict(list)
    for a in assignments:
        by_resource[a.resource].append(a)
    for rid, tasks in by_resource.items():
        tasks.sort(key=lambda x: (x.start, x.product, x.step_index))
        for i in range(1, len(tasks)):
            prev, cur = tasks[i - 1], tasks[i]
            assert prev.end <= cur.start, (
                f"Overlap on {rid}: {prev.product} ends {prev.end}, "
                f"{cur.product} starts {cur.start}"
            )


def assert_route_precedence(assignments: List[Assignment]) -> None:
    by_product: dict[str, list[Assignment]] = defaultdict(list)
    for a in assignments:
        by_product[a.product].append(a)
    for pid, steps in by_product.items():
        steps.sort(key=lambda x: x.step_index)
        for i in range(1, len(steps)):
            prev, cur = steps[i - 1], steps[i]
            assert prev.end <= cur.start, (
                f"Precedence violation {pid}: step {cur.step_index} starts "
                f"before step {prev.step_index} ends"
            )


def _resource_by_id(model: Model) -> dict[str, Resource]:
    return {r.id: r for r in model.resources}


def assert_assignments_in_single_windows(
    assignments: List[Assignment], model: Model
) -> None:
    rmap = _resource_by_id(model)
    for a in assignments:
        res = rmap[a.resource]
        ok = any(ws <= a.start and a.end <= we for ws, we in res.windows)
        assert ok, (
            f"Assignment {a.product} step {a.step_index} on {a.resource} "
            f"[{a.start},{a.end}) not contained in any calendar window"
        )


def assert_within_horizon(assignments: List[Assignment], model: Model) -> None:
    span = model.horizon_end - model.horizon_start
    for a in assignments:
        assert 0 <= a.start < a.end <= span, (
            f"Assignment {a.product} [{a.start},{a.end}) outside horizon [0,{span}]"
        )


def assert_changeover_gaps(assignments: List[Assignment], model: Model) -> None:
    fam = {j.id: j.family for j in model.jobs}
    by_resource: dict[str, list[Assignment]] = defaultdict(list)
    for a in assignments:
        by_resource[a.resource].append(a)
    for rid, tasks in by_resource.items():
        tasks.sort(key=lambda x: (x.start, x.product, x.step_index))
        prev_fam: str | None = None
        prev_end = 0
        for t in tasks:
            f = fam[t.product]
            if prev_fam is not None and f != prev_fam:
                need = model.changeover[prev_fam][f]
                
                assert t.start >= prev_end + need, (
                    f"Changeover gap on {rid}: need {need} min between "
                    f"{prev_fam}->{f}, got start {t.start} prev_end {prev_end}"
                )
            prev_fam = f
            prev_end = t.end


def verify_schedule(assignments: List[Assignment], model: Model) -> None:
    """Raise AssertionError if any hard constraint is violated."""
    assert_no_resource_overlap(assignments)
    assert_route_precedence(assignments)
    assert_assignments_in_single_windows(assignments, model)
    assert_within_horizon(assignments, model)
    assert_changeover_gaps(assignments, model)

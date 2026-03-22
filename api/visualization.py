from __future__ import annotations

from datetime import datetime, timedelta

from core.models import Assignment, Model


def _fmt_time(horizon_start: datetime, minutes: int) -> str:
    return (horizon_start + timedelta(minutes=minutes)).strftime("%H:%M")


def build_text_visualization(
    assignments: list[Assignment], model: Model, horizon_start: datetime
) -> str:
    by_resource: dict[str, list[Assignment]] = {r.id: [] for r in model.resources}
    for assignment in assignments:
        by_resource.setdefault(assignment.resource, []).append(assignment)

    lines: list[str] = ["=== Schedule Visualization (text) ==="]
    for resource_id, ops in by_resource.items():
        ops.sort(key=lambda x: (x.start, x.product, x.step_index))
        if not ops:
            lines.append(f"{resource_id:10} | (no assignments)")
            continue

        segments: list[str] = []
        for op in ops:
            start = _fmt_time(horizon_start, op.start)
            end = _fmt_time(horizon_start, op.end)
            label = f"{op.product}#{op.step_index}/{op.capability}"
            segments.append(f"[{start}-{end}] {label}")
        lines.append(f"{resource_id:10} | " + "  ->  ".join(segments))
    return "\n".join(lines)

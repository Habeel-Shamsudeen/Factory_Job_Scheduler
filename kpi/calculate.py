from typing import Dict, List, Tuple

from core.models import Assignment, KPIResult, Model


def _calculate_tardiness_minutes(assignments: List[Assignment], model: Model) -> int:
    """
    Calculate the tardiness minutes for the assignments.
    sum of max(0, completion - due) across products
    """
    tardiness_minutes = 0

    for job in model.jobs:
        job_assignments = [a for a in assignments if a.product == job.id]
        if not job_assignments:
            continue
        completion_time = max(a.end for a in job_assignments)
        tardiness_minutes += max(0, completion_time - job.due)

    return tardiness_minutes


def _calculate_changeover_stats(
    assignments: List[Assignment], model: Model
) -> Tuple[int, int]:
    """
    Calculate the changeover count and changeover minutes for the assignments.
    changeover count: number of family transitions on each resource sequence
    changeover minutes: summed matrix setup minutes for those transitions
    """
    changeover_count = 0
    changeover_minutes = 0
    family_mapping = {job.id: job.family for job in model.jobs}
    for resource in model.resources:
        resource_assignments = [a for a in assignments if a.resource == resource.id]
        if not resource_assignments:
            continue
        resource_assignments.sort(key=lambda x: (x.start, x.step_index, x.product))
        previous_family = family_mapping[resource_assignments[0].product]
        for resource_assignment in resource_assignments:
            fam = family_mapping[resource_assignment.product]
            if fam != previous_family:
                changeover_count += 1
                changeover_minutes += model.changeover[previous_family][fam]
            previous_family = fam
    return changeover_count, changeover_minutes


def _calculate_makespan_minutes(assignments: List[Assignment], model: Model) -> int:
    """
    Calculate the makespan minutes for the assignments.
    makespan minutes: max(end) - min(start) across assignments
    """
    if not assignments:
        return 0
    earliest_start = min(a.start for a in assignments)
    latest_end = max(a.end for a in assignments)
    return latest_end - earliest_start


def _calculate_utilization_pct(
    assignments: List[Assignment], model: Model
) -> Dict[str, int]:
    """
    Calculate the utilization percentage for the assignments.
    utilization percentage: processing minutes / total calendar minutes * 100
    exclude changeover minutes
    """
    utilization_pct: Dict[str, int] = {}

    for resource in model.resources:
        resource_assignments = [a for a in assignments if a.resource == resource.id]

        calendar_minutes = sum(window[1] - window[0] for window in resource.windows)

        if calendar_minutes == 0:
            utilization_pct[resource.id] = 0
            continue

        processing_minutes = sum(a.end - a.start for a in resource_assignments)

        pct = (processing_minutes / calendar_minutes) * 100
        utilization_pct[resource.id] = int(round(pct))

    return utilization_pct


def calculate_kpis(assignments: List[Assignment], model: Model) -> KPIResult:
    """
    Calculate the KPIs for the assignments.
    """
    # 1. Calculate the tardiness minutes
    tardiness_minutes = _calculate_tardiness_minutes(assignments, model)

    # 2. Calculate the changeover count and changeover minutes
    changeover_count, changeover_minutes = _calculate_changeover_stats(
        assignments, model
    )

    # 3. Calculate the makespan minutes
    makespan_minutes = _calculate_makespan_minutes(assignments, model)

    # 4. Calculate the utilization percentage
    utilization_pct = _calculate_utilization_pct(assignments, model)

    # 5. Return the KPIs scores
    return KPIResult(
        tardiness_minutes=tardiness_minutes,
        changeover_count=changeover_count,
        changeover_minutes=changeover_minutes,
        makespan_minutes=makespan_minutes,
        utilization_pct=utilization_pct,
    )

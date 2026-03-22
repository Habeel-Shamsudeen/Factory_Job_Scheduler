from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.models import Assignment, Model, Step


def _get_next_available_machine(
    machine_tracker: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """
    The next available machine is the machine with the smallest next available time.
    """
    min_next: Optional[int] = None
    next_machine: Optional[str] = None
    for resource_id, data in machine_tracker.items():
        time = data["next_available"]
        if min_next is None or time < min_next:
            min_next = time
            next_machine = resource_id
    return next_machine


def _earliest_in_windows(
    windows: List[tuple[int, int]],
    earliest: int,
    duration: int,
) -> Optional[int]:
    for ws, we in sorted(windows, key=lambda w: w[0]):
        start = max(earliest, ws)
        if start + duration <= we:
            return start
    return None


def _get_next_ready_job_for_machine(
    job_tracker: Dict[str, Dict[str, Any]],
    machine_id: str,
    machine_tracker: Dict[str, Dict[str, Any]],
    model: Model,
) -> tuple[Optional[str], Optional[int]]:
    """
    The next ready job for the machine is the job with the smallest due date that is ready for the machine at the current time.
    If there is no job ready for the machine at the current time, we will return None.
    If there are multiple jobs ready for the machine at the current time, we will return the job with the smallest due date.
    """
    caps = machine_tracker[machine_id]["capabilities"]
    candidates: List[str] = []
    for job_id, jt in job_tracker.items():
        index: int = jt["current_step_index"]
        steps: List[Step] = jt["steps"]
        if index >= len(steps):
            continue
        step = steps[index]
        if step.capability in caps:
            candidates.append(job_id)
    if not candidates:
        return None, None

    # if there are multiple candidates, then we check due date, potential panalty for changeover, nextavailable things like that
    best_job = None
    best_score = float('inf')
    machine = machine_tracker[machine_id]
    prev_fam = machine["current_family"]
    start_time = 0
    for job_id in candidates:
        job = job_tracker[job_id]
        fam = job["family"]

        # Calculating the change over cost and earliest possible start time
        setup_cost = 0
        if prev_fam is not None and prev_fam != fam:
            setup_cost = model.changeover[prev_fam][fam]
        earliest_start_time = max(machine["next_available"] + setup_cost, job["next_available"])
        earliest_in_windows = _earliest_in_windows(
            machine["intervals"],
            earliest_start_time,
            job["steps"][job["current_step_index"]].duration,
        )
        if earliest_in_windows is None:
            continue
        # Calculating the remaining time for the job to complete
        current_index = job["current_step_index"]
        remaining_steps = job["steps"][current_index:]
        remaining_time = sum(s.duration for s in remaining_steps)
        worst_case_setup = max(max(v.values()) for v in model.changeover.values())
        future_padding = max(0, len(remaining_steps) - 1) * worst_case_setup

        estimated_completion = earliest_in_windows + remaining_time + future_padding


        if model.settings.objective_mode == "min_tardiness":
            score = job["due"] - estimated_completion
        else:
            # Fallback
            score = job["due"]
    
        if score < best_score:
            best_score = score
            best_job = job_id
            start_time = earliest_in_windows
        elif score == best_score and best_job is not None:
            if job["due"] < job_tracker[best_job]["due"]:
                best_job = job_id
                start_time = earliest_in_windows

    if best_job is None:
        return None, None
    return best_job, start_time


def heuristic_schedule(model: Model) -> List[Assignment]:
    horizon_end = model.horizon_end - model.horizon_start

    machine_tracker: Dict[str, Dict[str, Any]] = {
        resource.id: {
            "current_family": None,
            "next_available": 0,
            "capabilities": resource.capabilities,
            "intervals": list(resource.windows),
        }
        for resource in model.resources
    }

    job_tracker: Dict[str, Dict[str, Any]] = {
        job.id: {
            "current_step_index": 0,
            "next_available": 0,
            "family": job.family,
            "due": job.due,
            "steps": list(job.steps),
        }
        for job in model.jobs
    }

    assignments: List[Assignment] = []
    total_steps = sum(len(job.steps) for job in model.jobs)

    while len(assignments) < total_steps:
        machine_id = _get_next_available_machine(machine_tracker)
        if machine_id is None:
            remaining_steps = []
            for job_id, job in job_tracker.items():
                remaining_steps.extend(job["steps"][job["current_step_index"]:])
            raise ValueError(
                "Infeasible: No machines are available to schedule the jobs. remaining steps: " + str(total_steps - len(assignments))
                + " remaining steps: " + str(remaining_steps)
            )
        job_id, start_time = _get_next_ready_job_for_machine(
            job_tracker, machine_id, machine_tracker, model
        )
        if job_id is None or start_time is None:
            # if there is no job ready for the machine at the current time, we will increment the next available time of the machine and check again.
            # this will also act as a tie breaker so that next iteration we will get another machine (since this machine do not have any jobs at the time)
            machine_tracker[machine_id]["next_available"] += 1
            if machine_tracker[machine_id]["next_available"] > horizon_end:
                del machine_tracker[machine_id]
            continue
        job = job_tracker[job_id]
        machine = machine_tracker[machine_id]
        index: int = job["current_step_index"]
        step = job["steps"][index]

        end = start_time + step.duration

        assignments.append(
            Assignment(
                product=job_id,
                step_index=index + 1,
                capability=step.capability,
                resource=machine_id,
                start=start_time,
                end=end,
            )
        )

        machine["next_available"] = end
        machine["current_family"] = job["family"]
        job["next_available"] = end
        job["current_step_index"] = index + 1
        if job["current_step_index"] == len(job["steps"]):
            del job_tracker[job_id]

    if len(assignments) < total_steps:
        raise ValueError(
            "Infeasible: The horizon ended before all required jobs could be scheduled due to tight due dates and calendar fragmentation."
        )
    return assignments

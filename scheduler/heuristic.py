from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from core.errors import InfeasibleError
from core.models import Assignment, Model, Step


def _get_next_available_machine(
    machine_tracker: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    """Pick the resource with the smallest next_available time."""
    min_next: Optional[int] = None
    candidates: List[str] = []
    for resource_id, data in machine_tracker.items():
        time = data["next_available"]
        if min_next is None or time < min_next:
            min_next = time
            candidates = [resource_id]
        elif time == min_next:
            candidates.append(resource_id)
    if not candidates:
        return None
    return min(candidates)


def _changeover_minutes(model: Model, prev_fam: Optional[str], fam: str) -> int:
    """Helper function to get the changeover time between two families."""
    if prev_fam is None:
        return 0
    cost = (model.changeover.get(prev_fam) or {}).get(fam)
    if cost is None:
        raise InfeasibleError([f"Unknown changeover {prev_fam!r} -> {fam!r}."])
    return cost


def _earliest_op_start_in_windows(
    windows: List[tuple[int, int]],
    machine_free: int,
    job_ready: int,
    setup: int,
    duration: int,
) -> Optional[int]:
    """
    Helper function to get the earliest operation start time such that the operation can be scheduled on the machine.
    The idea behind this is that the machine can undergo changeover (if it need to) as soon as it is free. So that we save time instead of waiting for the job to be ready and starting the changeover.
    """
    earliest_ready = max(machine_free + setup, job_ready)
    for ws, we in sorted(windows, key=lambda w: w[0]):
        t_low = max(earliest_ready, ws + setup)
        t_high = we - duration
        if t_low <= t_high:
            return t_low
    return None


def _machine_can_serve_remaining(
    caps: Set[str], job_tracker: Dict[str, Dict[str, Any]],
) -> bool:
    """
    True if this resource can run at least one step (current or later) of some job.
    """
    for jt in job_tracker.values():
        index: int = jt["current_step_index"]
        steps: List[Step] = jt["steps"]
        for i in range(index, len(steps)):
            if steps[i].capability in caps:
                return True
    return False


def _machine_has_current_candidates(
    machine_id: str,
    machine_tracker: Dict[str, Dict[str, Any]],
    job_tracker: Dict[str, Dict[str, Any]],
) -> bool:
    """
    True if this machine can run at least one step (current or later) of some job.
    """
    caps = machine_tracker[machine_id]["capabilities"]
    for jt in job_tracker.values():
        index = jt["current_step_index"]
        steps: List[Step] = jt["steps"]
        if index < len(steps) and steps[index].capability in caps:
            return True
    return False


def _advance_machine_when_idle(
    machine_id: str,
    machine_tracker: Dict[str, Dict[str, Any]],
    job_tracker: Dict[str, Dict[str, Any]],
    horizon_end: int,
    had_candidates: bool,
) -> int:
    """
    Jump next_available forward to the next meaningful time. Like if the machine is idle, we need to jump to the next time when the machine is available.
    """
    time = machine_tracker[machine_id]["next_available"]
    caps = frozenset(machine_tracker[machine_id]["capabilities"])
    intervals = sorted(machine_tracker[machine_id]["intervals"], key=lambda w: w[0])

    # Here we are checking if the machine has the capabilities to serve any of the remaining jobs.
    if job_tracker and not _machine_can_serve_remaining(set(caps), job_tracker):
        # It serves no purpose in the future so we can del it (will be deleted upstream)
        return horizon_end + 1

    # Finding possible time jumps
    events: List[int] = []
    # Possible jump to start of next window or end of the current window
    for ws, we in intervals:
        if ws > time:
            events.append(ws)
        elif had_candidates and ws <= time < we:
            events.append(we)
    # Jobs whose current step this machine can run may become ready later than `time`.
    if had_candidates:
        for jt in job_tracker.values():
            index = jt["current_step_index"]
            if index >= len(jt["steps"]):
                continue
            if jt["steps"][index].capability in caps:
                na = jt["next_available"]
                if na > time:
                    events.append(na)
    
    # If there was no candidates to run on the machine, we need to jump to the next time when any other machine is available.
    if not had_candidates:
        other_times = [
            machine_tracker[mid]["next_available"]
            for mid in machine_tracker
            if mid != machine_id
        ]
        for ot in other_times:
            if ot > time:
                events.append(ot)

    if not events:
        return time + 1
    return min(events)


def _worst_case_changeover(model: Model) -> int:
    """
    Helper function to get the worst case changeover time. Basically the max changeover time between any two families.
    TODO: I guess we should also pass the job and return max changeover to that job's family.
     """
    if not model.changeover:
        return 0
    return max(max(v.values()) for v in model.changeover.values())


def _get_next_ready_job_for_machine(
    job_tracker: Dict[str, Dict[str, Any]],
    machine_id: str,
    machine_tracker: Dict[str, Dict[str, Any]],
    model: Model,
) -> tuple[Optional[str], Optional[int]]:
    caps = machine_tracker[machine_id]["capabilities"]
    candidates: List[str] = []
    # We get the job id of the jobs whose current step capability is in the machine's capabilities.
    for job_id, jt in job_tracker.items():
        index: int = jt["current_step_index"]
        steps: List[Step] = jt["steps"]
        if index >= len(steps):
            continue
        step = steps[index]
        if step.capability in caps:
            candidates.append(job_id)

    # No candidate means that no job can be scheduled on this machine.
    if not candidates:
        return None, None

    # We now have a list of candidate jobs. We need to find the best one. And we will also find the start time of the best job factoring in the changeover time.
    best_job: Optional[str] = None
    best_score = float("inf")
    machine = machine_tracker[machine_id]
    prev_fam: Optional[str] = machine["current_family"]
    start_time = 0
    worst_setup = _worst_case_changeover(model)

    for job_id in sorted(candidates):
        job = job_tracker[job_id]
        fam = job["family"]
        setup = _changeover_minutes(model, prev_fam, fam)
        machine_free: int = machine["next_available"]
        job_ready: int = job["next_available"]
        duration = job["steps"][job["current_step_index"]].duration

        earliest_in_windows = _earliest_op_start_in_windows(
            machine["intervals"],
            machine_free,
            job_ready,
            setup,
            duration,
        )
        if earliest_in_windows is None:
            continue

        current_index = job["current_step_index"]
        remaining_steps = job["steps"][current_index:]
        remaining_time = sum(s.duration for s in remaining_steps)
        # We add the worst case changeover time for each remaining step. Assuming that the machine will need to changeover for each remaining step which is like a worst case scenario.
        future_padding = max(0, len(remaining_steps) - 1) * worst_setup
        estimated_completion = earliest_in_windows + remaining_time + future_padding

        if model.settings.objective_mode == "min_tardiness":
            score = job["due"] - estimated_completion
        else:
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
    horizon_span = model.horizon_end - model.horizon_start

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
            raise InfeasibleError(
                [
                    "No resources remain available within the horizon while jobs still need scheduling.",
                    "Check calendars, capabilities, and horizon length.",
                ]
            )

        job_id, start_time = _get_next_ready_job_for_machine(
            job_tracker, machine_id, machine_tracker, model
        )
        if job_id is None or start_time is None:
            had_candidates = _machine_has_current_candidates(
                machine_id, machine_tracker, job_tracker
            )
            new_t = _advance_machine_when_idle(
                machine_id,
                machine_tracker,
                job_tracker,
                horizon_span,
                had_candidates=had_candidates,
            )
            machine_tracker[machine_id]["next_available"] = new_t
            if new_t >= horizon_span:
                del machine_tracker[machine_id]
            continue

        job = job_tracker[job_id]
        machine = machine_tracker[machine_id]
        index: int = job["current_step_index"]
        step = job["steps"][index]
        end = start_time + step.duration

        if end > horizon_span:
            raise InfeasibleError(
                [
                    f"Operation for product {job_id} step {index + 1} would end after the horizon end time.",
                ]
            )

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

        # cleanup completed jobs
        if job["current_step_index"] == len(job["steps"]):
            del job_tracker[job_id]

    return assignments

from core.models import Model, Assignment
from api.schemas import KPIResponseSchema
from typing import List, Tuple, Dict

def _calculate_tardiness_minutes(assignments: List[Assignment], model: Model) -> int:
    tardiness_minutes = 0
    
    for job in model.jobs:
        job_assignments = [a for a in assignments if a.product == job.id]
        if not job_assignments:
            continue  
        completion_time = max(a.end for a in job_assignments)
        tardiness_minutes += max(0, completion_time - job.due)
        
    return tardiness_minutes

def _calculate_changeover_stats(assignments: List[Assignment], model: Model) -> Tuple[int, int]:
    changeover_count = 0
    changeover_minutes = 0
    family_mapping = {
        job.id: job.family for job in model.jobs
    }
    for resource in model.resources:
        resource_assignments = [a for a in assignments if a.resource == resource.id]
        if not resource_assignments:
            continue
        resource_assignments.sort(key=lambda x: x.start)
        previous_family = family_mapping[resource_assignments[0].product]
        for resource_assignment in resource_assignments:
            if family_mapping[resource_assignment.product] != previous_family:
                changeover_count += 1
                changeover_minutes += model.changeover[previous_family][family_mapping[resource_assignment.product]]
            previous_family = family_mapping[resource_assignment.product]
    return changeover_count, changeover_minutes

def _calculate_makespan_minutes(assignments: List[Assignment], model: Model) -> int:
    earliest_start = min(a.start for a in assignments)
    latest_end = max(a.end for a in assignments)
    return latest_end - earliest_start

def _calculate_utilization_pct(assignments: List[Assignment], model: Model) -> Dict[str, int]:
    utilization_pct = {}
    
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

def calculate_kpis(assignments: List[Assignment], model: Model) -> KPIResponseSchema:
    tardiness_minutes = _calculate_tardiness_minutes(assignments, model)
    changeover_count, changeover_minutes = _calculate_changeover_stats(assignments, model)
    makespan_minutes = _calculate_makespan_minutes(assignments, model)
    utilization_pct = _calculate_utilization_pct(assignments, model)

    return KPIResponseSchema(
        tardiness_minutes=tardiness_minutes,
        changeover_count=changeover_count,
        changeover_minutes=changeover_minutes,
        makespan_minutes=makespan_minutes,
        utilization_pct=utilization_pct,
    )
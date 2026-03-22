from api.schemas import ScheduleRequest
from core.models import Model, Job, Resource, Settings, Step
from datetime import datetime

def _to_minutes(start_dt: datetime, dt: datetime) -> int:
    return int((dt - start_dt).total_seconds() / 60)

def client_a_to_model(request: ScheduleRequest) -> Model:
    """
    Convert the request from Client A to the canonical internal model. Transforms Client A request to the canonical internal model.
    """
    # 1. Mapping: Horizon -> horizon_start and horizon_end (convert horizon to minutes)
    start_dt = request.horizon.start
    horizon_start = 0
    horizon_end = _to_minutes(start_dt, request.horizon.end)
    
    # 2. Mapping: Resources -> Internal Resources 
    resources = []
    for resource in request.resources:
        windows = [
            (
                _to_minutes(start_dt, interval[0]),
                _to_minutes(start_dt, interval[1]),
            )
            for interval in resource.calendar
        ]
        resources.append(Resource(
            id=resource.id,
            capabilities=resource.capabilities,
            windows=windows,
        ))
    
    # 3. Mapping: Changeover Matrix -> Internal changeover
    changeover = {}
    for key, cost in request.changeover_matrix_minutes.values.items():
        family1, family2 = key.split("->")
        changeover.setdefault(family1, {})[family2] = cost
    
    # 4. Mapping: Products -> Internal Jobs
    jobs = []
    for product in request.products:
        steps = [
            Step(
                capability=step.capability,
                duration=step.duration_minutes,
            )
            for step in product.route
        ]
        jobs.append(Job(
            id=product.id,
            family=product.family,
            due=_to_minutes(start_dt, product.due),
            steps=steps,
        ))
    
    # 5. Mapping: Settings -> Internal Settings
    settings = Settings(
        time_limit_seconds=request.settings.time_limit_seconds,
        objective_mode=request.settings.objective_mode,
    )
    
    # 6. Return Model (return internal model)
    return Model(
        jobs=jobs,
        resources=resources,
        changeover=changeover,
        horizon_start=horizon_start,
        horizon_end=horizon_end,
        settings=settings,
    )
from datetime import timedelta

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from adapter.client_a import client_a_to_model
from core.errors import InfeasibleError
from kpi.calculate import calculate_kpis

from .schemas import (
    AssignmentSchema,
    KPIResponseSchema,
    ScheduleInfeasibleResponse,
    ScheduleRequest,
    ScheduleSuccessResponse,
)
from .validation_errors import request_validation_exception_handler
from scheduler.heuristic import heuristic_schedule

app = FastAPI(
    title="Harmony Job Scheduler API",
)

app.add_exception_handler(
    RequestValidationError, request_validation_exception_handler
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/schedule",
    response_model=ScheduleSuccessResponse,
    responses={
        422: {
            "model": ScheduleInfeasibleResponse,
            "description": "No feasible schedule",
        },
    },
)
def create_schedule(request: ScheduleRequest) -> ScheduleSuccessResponse | JSONResponse:
    model = client_a_to_model(request)
    try:
        assignments = heuristic_schedule(model)
    except InfeasibleError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "infeasible", "why": exc.reasons},
        )

    kpis = calculate_kpis(assignments, model)
    horizon_start = request.horizon.start
    transformed_assignments = [
        AssignmentSchema(
            product=assignment.product,
            step_index=assignment.step_index,
            capability=assignment.capability,
            resource=assignment.resource,
            start=horizon_start + timedelta(minutes=assignment.start),
            end=horizon_start + timedelta(minutes=assignment.end),
        )
        for assignment in assignments
    ]
    return ScheduleSuccessResponse(
        assignments=transformed_assignments,
        kpis=KPIResponseSchema(
            tardiness_minutes=kpis.tardiness_minutes,
            changeover_count=kpis.changeover_count,
            changeover_minutes=kpis.changeover_minutes,
            makespan_minutes=kpis.makespan_minutes,
            utilization_pct=kpis.utilization_pct,
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

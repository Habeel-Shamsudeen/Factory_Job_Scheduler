from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from .schemas import (
    ScheduleResponse,
    ScheduleRequest,
    ScheduleSuccessResponse,
)
from .validation_errors import request_validation_exception_handler
from adapter.client_a import client_a_to_model
from kpi.calculate import calculate_kpis
from scheduler.mock import schedule_mock

app = FastAPI(
    title="Harmony Job Scheduler API",
)

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/schedule", response_model=ScheduleResponse)
def create_schedule(request: ScheduleRequest) -> ScheduleResponse:
    try:
        # Step 0: Validate the request payload [Already handled by pydantic]
        # step 1: Transform the request payload into a format that can be used by the scheduler
        model = client_a_to_model(request)
        # step 2: Call the scheduler
        assignments = schedule_mock(model)
        # Step 3: Calculate the KPIs
        kpis = calculate_kpis(assignments, model)
        # Step 4: return the response

        return ScheduleSuccessResponse(
            assignments=[],
            kpis=kpis,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
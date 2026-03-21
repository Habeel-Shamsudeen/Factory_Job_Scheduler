from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from .schemas import (
    KPIResponseSchema,
    SchedulePostResponse,
    ScheduleRequest,
    ScheduleSuccessResponse,
)
from .validation_errors import request_validation_exception_handler


app = FastAPI(
    title="Harmony Job Scheduler API",
)

app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

@app.get("/health")
def health_check():
    return {"message": "ok"}


@app.post("/schedule", response_model=SchedulePostResponse)
def create_schedule(request_payload: ScheduleRequest) -> SchedulePostResponse:
    try:
        # Step 0: Validate the request payload [Already handled by pydantic]
        # step 1: Transform the request payload into a format that can be used by the scheduler
        # step 2: Call the scheduler
        # Step 3: Calculate the KPIs
        # Step 4: return the response
        return ScheduleSuccessResponse(
            assignments=[],
            kpis=KPIResponseSchema(
                tardiness_minutes=0,
                changeover_count=0,
                changeover_minutes=0,
                makespan_minutes=0,
                utilization_pct={},
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
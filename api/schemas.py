from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class HorizonSchema(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_horizon(self) -> Self:
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class ResourceSchema(BaseModel):
    id: str
    capabilities: list[str]
    calendar: list[list[datetime]]

    @field_validator("calendar")
    @classmethod
    def validate_calendar(cls, calendar: list[list[datetime]]) -> list[list[datetime]]:
        if len(calendar) == 0:
            raise ValueError("calendar must be non-empty")
        for interval in calendar:
            if len(interval) != 2:
                raise ValueError("interval must be a list of two datetime objects")
            if interval[0] >= interval[1]:
                raise ValueError("interval start must be before end")
        return calendar


class ChangeoverMatrixMinutesSchema(BaseModel):
    """
    family1->family2: minutes to changeover
    """
    values: dict[str, int]


class RouteSchema(BaseModel):
    capability: str
    duration_minutes: int

    @field_validator("duration_minutes")
    @classmethod
    def duration_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("duration_minutes must be > 0")
        return value


class ProductSchema(BaseModel):
    id: str
    family: str
    due: datetime
    route: list[RouteSchema] = Field(min_length=1)


class SettingsSchema(BaseModel):
    time_limit_seconds: int
    objective_mode: str

    @field_validator("time_limit_seconds")
    @classmethod
    def time_limit_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("time_limit_seconds must be > 0")
        return value


class AssignmentSchema(BaseModel):
    product: str
    step_index: int
    capability: str
    resource: str
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_assignment(self) -> Self:
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class KPIResponseSchema(BaseModel):
    tardiness_minutes: int
    changeover_count: int
    changeover_minutes: int
    makespan_minutes: int
    utilization_pct: dict[str, int]

class ScheduleRequest(BaseModel):
    horizon: HorizonSchema
    resources: list[ResourceSchema]
    changeover_matrix_minutes: ChangeoverMatrixMinutesSchema
    products: list[ProductSchema]
    settings: SettingsSchema


class ScheduleSuccessResponse(BaseModel):
    assignments: list[AssignmentSchema]
    kpis: KPIResponseSchema


class ScheduleInfeasibleResponse(BaseModel):
    error: Literal["infeasible"]
    why: list[str] = Field(min_length=1)


SchedulePostResponse = ScheduleSuccessResponse | ScheduleInfeasibleResponse

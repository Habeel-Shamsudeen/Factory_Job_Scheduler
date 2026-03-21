from datetime import datetime
from typing import Literal, Union, Tuple, List, Dict

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
    capabilities: List[str]
    calendar: List[Tuple[datetime, datetime]]

    @field_validator("calendar")
    @classmethod
    def validate_calendar(cls, calendar: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
        if len(calendar) == 0:
            raise ValueError("calendar must be non-empty")
        for start, end in calendar:
            if start >= end:
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
    route: List[RouteSchema] = Field(min_length=1)


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
    utilization_pct: Dict[str, int]

class ScheduleRequest(BaseModel):
    horizon: HorizonSchema
    resources: list[ResourceSchema]
    changeover_matrix_minutes: ChangeoverMatrixMinutesSchema
    products: list[ProductSchema]
    settings: SettingsSchema

    @model_validator(mode="after")
    def validate_schedule_request(self) -> Self:
        # calendar should be in the range of the horizon
        for resource in self.resources:
            for start, end in resource.calendar:
                if start < self.horizon.start or end > self.horizon.end:
                    raise ValueError("calendar must be in the range of the horizon")
        # products should be in the range of the horizon
        for product in self.products:
            if product.due < self.horizon.start or product.due > self.horizon.end:
                raise ValueError("due date must be in the range of the horizon")

        return self


class ScheduleSuccessResponse(BaseModel):
    assignments: list[AssignmentSchema]
    kpis: KPIResponseSchema


class ScheduleInfeasibleResponse(BaseModel):
    error: Literal["infeasible"]
    why: List[str] = Field(min_length=1)


ScheduleResponse = Union[ScheduleSuccessResponse, ScheduleInfeasibleResponse]

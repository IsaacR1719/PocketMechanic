from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def schedule_shape_error(
    interval_miles: int | None,
    interval_days: int | None,
    due_mileage: int | None,
    due_date: date | None,
) -> str | None:
    has_miles = interval_miles is not None
    has_days = interval_days is not None

    if has_miles == has_days:
        return "Set either a mileage interval or a time interval"

    if has_miles and due_mileage is None:
        return "A mileage schedule needs a due mileage"

    if has_miles and due_date is not None:
        return "A mileage schedule cannot include a due date"

    if has_days and due_date is None:
        return "A time schedule needs a due date"

    if has_days and due_mileage is not None:
        return "A time schedule cannot include a due mileage"

    return None


class ScheduleCreate(BaseModel):
    service_type: str = Field(min_length=1, max_length=100)
    interval_miles: int | None = None
    interval_days: int | None = None
    due_mileage: int | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("service_type")
    @classmethod
    def clean_service_type(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Service type cannot be blank")
        return value

    @field_validator("interval_miles", "interval_days")
    @classmethod
    def check_interval(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Interval must be at least 1")
        return value

    @field_validator("due_mileage")
    @classmethod
    def check_due_mileage(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Due mileage cannot be negative")
        return value

    @model_validator(mode="after")
    def check_shape(self) -> "ScheduleCreate":
        message = schedule_shape_error(
            self.interval_miles,
            self.interval_days,
            self.due_mileage,
            self.due_date,
        )
        if message:
            raise ValueError(message)
        return self


class ScheduleUpdate(BaseModel):
    service_type: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    interval_miles: int | None = None
    interval_days: int | None = None
    due_mileage: int | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("service_type", mode="before")
    @classmethod
    def reject_null_service_type(cls, value: object) -> object:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("service_type")
    @classmethod
    def clean_service_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Service type cannot be blank")
        return value

    @field_validator("interval_miles", "interval_days")
    @classmethod
    def check_interval(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Interval must be at least 1")
        return value

    @field_validator("due_mileage")
    @classmethod
    def check_due_mileage(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Due mileage cannot be negative")
        return value


class ScheduleResponse(ScheduleCreate):
    id: int
    vehicle_id: int
    created_at: datetime
    status: Literal["overdue", "approaching", "upcoming"]
    miles_remaining: int | None
    days_remaining: int | None

    model_config = ConfigDict(from_attributes=True)

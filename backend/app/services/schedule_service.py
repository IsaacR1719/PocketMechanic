from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance_schedule import MaintenanceSchedule
from app.models.vehicle import Vehicle
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    schedule_shape_error,
)
from app.services.vehicle_service import get_vehicle


# Due soon: within this many miles, or this many days, of the due point.
APPROACHING_MILES = 500
APPROACHING_DAYS = 14

STATUS_ORDER = {
    "overdue": 0,
    "approaching": 1,
    "upcoming": 2,
}


def check_schedule_shape(
    interval_miles: int | None,
    interval_days: int | None,
    due_mileage: int | None,
    due_date: date | None,
) -> None:
    message = schedule_shape_error(
        interval_miles, interval_days, due_mileage, due_date
    )
    if message:
        raise HTTPException(status_code=422, detail=message)


def reminder_state(
    schedule: MaintenanceSchedule,
    vehicle: Vehicle,
    today: date | None = None,
) -> dict:
    # Overdue once the due mileage or date has passed.
    # Approaching within APPROACHING_MILES or APPROACHING_DAYS.
    today = today or date.today()

    if schedule.interval_miles is not None:
        miles_remaining = schedule.due_mileage - vehicle.mileage
        if miles_remaining < 0:
            status = "overdue"
        elif miles_remaining <= APPROACHING_MILES:
            status = "approaching"
        else:
            status = "upcoming"
        return {
            "status": status,
            "miles_remaining": miles_remaining,
            "days_remaining": None,
        }

    days_remaining = (schedule.due_date - today).days
    if days_remaining < 0:
        status = "overdue"
    elif days_remaining <= APPROACHING_DAYS:
        status = "approaching"
    else:
        status = "upcoming"

    return {
        "status": status,
        "miles_remaining": None,
        "days_remaining": days_remaining,
    }


def to_response(
    schedule: MaintenanceSchedule,
    vehicle: Vehicle,
    today: date | None = None,
) -> dict:
    state = reminder_state(schedule, vehicle, today)
    return {
        "id": schedule.id,
        "vehicle_id": schedule.vehicle_id,
        "service_type": schedule.service_type,
        "interval_miles": schedule.interval_miles,
        "interval_days": schedule.interval_days,
        "due_mileage": schedule.due_mileage,
        "due_date": schedule.due_date,
        "notes": schedule.notes,
        "created_at": schedule.created_at,
        "status": state["status"],
        "miles_remaining": state["miles_remaining"],
        "days_remaining": state["days_remaining"],
    }


def reminder_sort_key(item: dict) -> tuple:
    remaining = item["miles_remaining"]
    if remaining is None:
        remaining = item["days_remaining"]
    return (STATUS_ORDER[item["status"]], remaining, item["id"])


def add_schedule(
    db: Session,
    user_id: int,
    vehicle_id: int,
    data: ScheduleCreate,
):
    get_vehicle(db, user_id, vehicle_id)
    check_schedule_shape(
        data.interval_miles,
        data.interval_days,
        data.due_mileage,
        data.due_date,
    )

    schedule = MaintenanceSchedule(
        vehicle_id=vehicle_id,
        **data.model_dump()
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedules(db: Session, user_id: int, vehicle_id: int):
    vehicle = get_vehicle(db, user_id, vehicle_id)
    schedules = db.scalars(
        select(MaintenanceSchedule)
        .where(MaintenanceSchedule.vehicle_id == vehicle_id)
    ).all()
    return sorted(
        schedules,
        key=lambda schedule: reminder_sort_key(
            to_response(schedule, vehicle)
        ),
    )


def get_schedule(db: Session, user_id: int, schedule_id: int):
    schedule = db.scalar(
        select(MaintenanceSchedule)
        .join(Vehicle, MaintenanceSchedule.vehicle_id == Vehicle.id)
        .where(
            MaintenanceSchedule.id == schedule_id,
            Vehicle.user_id == user_id,
        )
    )

    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail="Schedule not found"
        )

    return schedule


def update_schedule(
    db: Session,
    user_id: int,
    schedule_id: int,
    data: ScheduleUpdate,
):
    schedule = get_schedule(db, user_id, schedule_id)
    changes = data.model_dump(exclude_unset=True)

    merged = {
        "interval_miles": schedule.interval_miles,
        "interval_days": schedule.interval_days,
        "due_mileage": schedule.due_mileage,
        "due_date": schedule.due_date,
    }
    for field in merged:
        if field in changes:
            merged[field] = changes[field]

    check_schedule_shape(
        merged["interval_miles"],
        merged["interval_days"],
        merged["due_mileage"],
        merged["due_date"],
    )

    for field, value in changes.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, user_id: int, schedule_id: int):
    schedule = get_schedule(db, user_id, schedule_id)
    db.delete(schedule)
    db.commit()


def list_reminders(
    db: Session,
    user_id: int,
    today: date | None = None,
):
    rows = db.execute(
        select(MaintenanceSchedule, Vehicle)
        .join(Vehicle, MaintenanceSchedule.vehicle_id == Vehicle.id)
        .where(Vehicle.user_id == user_id)
    ).all()

    reminders = [
        to_response(schedule, vehicle, today)
        for schedule, vehicle in rows
    ]
    reminders.sort(key=reminder_sort_key)
    return reminders


def respond(db: Session, user_id: int, schedule: MaintenanceSchedule):
    vehicle = get_vehicle(db, user_id, schedule.vehicle_id)
    return to_response(schedule, vehicle)

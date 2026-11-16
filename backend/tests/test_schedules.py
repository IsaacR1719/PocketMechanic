import os
import unittest
from datetime import date, timedelta

os.environ.setdefault(
    "DATABASE_URL", "sqlite+pysqlite:///:memory:"
)

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.maintenance_schedule import MaintenanceSchedule

from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.schedule_service import (
    add_schedule,
    get_schedule,
    list_schedules,
    list_reminders,
    update_schedule,
    delete_schedule,
    reminder_state,
)


class ScheduleServiceTests(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:"
        )
        Base.metadata.create_all(self.engine)

        self.db = Session(self.engine)
        self.today = date(2026, 11, 16)

        self.db.add_all([
            User(
                name="Alex",
                email="alex@example.com",
                password_hash="test"
            ),
            User(
                name="Sam",
                email="sam@example.com",
                password_hash="test"
            )
        ])
        self.db.commit()

        self.db.add_all([
            Vehicle(
                user_id=1,
                make="Toyota",
                model="Corolla",
                year=2020,
                mileage=10000
            ),
            Vehicle(
                user_id=2,
                make="Honda",
                model="Civic",
                year=2021,
                mileage=20000
            )
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_mileage_schedule_crud(self):
        created = ScheduleCreate(
            service_type="  Oil Change  ",
            interval_miles=5000,
            due_mileage=15000,
            notes="Synthetic oil"
        )
        self.assertEqual(created.service_type, "Oil Change")

        schedule = add_schedule(self.db, 1, 1, created)

        self.assertEqual(schedule.interval_miles, 5000)
        self.assertEqual(schedule.due_mileage, 15000)
        self.assertIsNone(schedule.interval_days)
        self.assertIsNone(schedule.due_date)
        self.assertEqual(schedule.notes, "Synthetic oil")

        records = list_schedules(self.db, 1, 1)
        self.assertEqual(len(records), 1)

        found = get_schedule(self.db, 1, schedule.id)
        self.assertEqual(found.service_type, "Oil Change")

        update_schedule(
            self.db, 1, schedule.id,
            ScheduleUpdate(due_mileage=16000, notes="Full synthetic")
        )

        updated = get_schedule(self.db, 1, schedule.id)
        self.assertEqual(updated.due_mileage, 16000)
        self.assertEqual(updated.notes, "Full synthetic")

        delete_schedule(self.db, 1, schedule.id)

        self.assertEqual(
            list_schedules(self.db, 1, 1), []
        )

    def test_time_schedule_crud(self):
        due = self.today + timedelta(days=180)
        schedule = add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Inspection",
                interval_days=180,
                due_date=due
            )
        )

        self.assertEqual(schedule.interval_days, 180)
        self.assertEqual(schedule.due_date, due)
        self.assertIsNone(schedule.interval_miles)

        update_schedule(
            self.db, 1, schedule.id,
            ScheduleUpdate(
                interval_miles=None,
                due_mileage=None,
                interval_days=365,
                due_date=self.today + timedelta(days=30)
            )
        )

        updated = get_schedule(self.db, 1, schedule.id)
        self.assertEqual(updated.interval_days, 365)
        self.assertEqual(
            updated.due_date, self.today + timedelta(days=30)
        )

    def test_switch_schedule_basis(self):
        schedule = add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Tire rotation",
                interval_miles=7500,
                due_mileage=17500
            )
        )

        update_schedule(
            self.db, 1, schedule.id,
            ScheduleUpdate(
                interval_miles=None,
                due_mileage=None,
                interval_days=180,
                due_date=self.today + timedelta(days=20)
            )
        )

        updated = get_schedule(self.db, 1, schedule.id)
        self.assertIsNone(updated.interval_miles)
        self.assertIsNone(updated.due_mileage)
        self.assertEqual(updated.interval_days, 180)
        self.assertEqual(
            updated.due_date, self.today + timedelta(days=20)
        )

    def test_vehicle_ownership(self):
        schedule = add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Brake fluid",
                interval_miles=30000,
                due_mileage=40000
            )
        )

        with self.assertRaises(HTTPException) as result:
            get_schedule(self.db, 2, schedule.id)

        self.assertEqual(result.exception.status_code, 404)

        with self.assertRaises(HTTPException):
            update_schedule(
                self.db, 2, schedule.id,
                ScheduleUpdate(service_type="Stolen")
            )

        with self.assertRaises(HTTPException):
            delete_schedule(self.db, 2, schedule.id)

        with self.assertRaises(HTTPException):
            list_schedules(self.db, 2, 1)

        with self.assertRaises(HTTPException):
            add_schedule(
                self.db, 2, 1,
                ScheduleCreate(
                    service_type="Oil Change",
                    interval_miles=5000,
                    due_mileage=15000
                )
            )

        self.assertEqual(
            get_schedule(self.db, 1, schedule.id).service_type,
            "Brake fluid"
        )
        self.assertEqual(list_reminders(self.db, 2), [])

    def test_invalid_schedules(self):
        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="   ",
                interval_miles=5000,
                due_mileage=15000
            )

        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="Oil Change",
                interval_miles=5000,
                due_mileage=15000,
                due_date="2026-12-01"
            )

        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="Oil Change",
                interval_miles=5000
            )

        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="Inspection",
                interval_days=180
            )

        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="Oil Change",
                interval_miles=0,
                due_mileage=15000
            )

        with self.assertRaises(ValidationError):
            ScheduleCreate(
                service_type="Oil Change",
                due_mileage=15000
            )

        with self.assertRaises(ValidationError):
            ScheduleUpdate(service_type=None)

        schedule = add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Oil Change",
                interval_miles=5000,
                due_mileage=15000
            )
        )

        with self.assertRaises(HTTPException) as result:
            update_schedule(
                self.db, 1, schedule.id,
                ScheduleUpdate(due_mileage=None)
            )

        self.assertEqual(result.exception.status_code, 422)
        self.assertEqual(
            get_schedule(self.db, 1, schedule.id).due_mileage,
            15000
        )

        with self.assertRaises(HTTPException) as result:
            update_schedule(
                self.db, 1, schedule.id,
                ScheduleUpdate(
                    interval_days=30,
                    due_date=self.today
                )
            )

        self.assertEqual(result.exception.status_code, 422)
        self.assertEqual(
            get_schedule(self.db, 1, schedule.id).interval_miles,
            5000
        )

    def test_reminder_status(self):
        vehicle = self.db.get(Vehicle, 1)

        def mileage_state(due_mileage):
            schedule = MaintenanceSchedule(
                vehicle_id=vehicle.id,
                service_type="Oil Change",
                interval_miles=5000,
                due_mileage=due_mileage
            )
            return reminder_state(schedule, vehicle, self.today)

        overdue = mileage_state(9000)
        self.assertEqual(overdue["status"], "overdue")
        self.assertEqual(overdue["miles_remaining"], -1000)
        self.assertIsNone(overdue["days_remaining"])

        due_now = mileage_state(10000)
        self.assertEqual(due_now["status"], "approaching")
        self.assertEqual(due_now["miles_remaining"], 0)

        approaching = mileage_state(10500)
        self.assertEqual(approaching["status"], "approaching")
        self.assertEqual(approaching["miles_remaining"], 500)

        upcoming = mileage_state(10501)
        self.assertEqual(upcoming["status"], "upcoming")
        self.assertEqual(upcoming["miles_remaining"], 501)

        def time_state(days):
            schedule = MaintenanceSchedule(
                vehicle_id=vehicle.id,
                service_type="Inspection",
                interval_days=180,
                due_date=self.today + timedelta(days=days)
            )
            return reminder_state(schedule, vehicle, self.today)

        late = time_state(-1)
        self.assertEqual(late["status"], "overdue")
        self.assertEqual(late["days_remaining"], -1)
        self.assertIsNone(late["miles_remaining"])

        today = time_state(0)
        self.assertEqual(today["status"], "approaching")
        self.assertEqual(today["days_remaining"], 0)

        soon = time_state(14)
        self.assertEqual(soon["status"], "approaching")

        later = time_state(15)
        self.assertEqual(later["status"], "upcoming")
        self.assertEqual(later["days_remaining"], 15)

    def test_reminders_are_sorted_for_the_owner(self):
        add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Later service",
                interval_miles=5000,
                due_mileage=20000
            )
        )
        add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Soon service",
                interval_days=180,
                due_date=self.today + timedelta(days=7)
            )
        )
        add_schedule(
            self.db, 1, 1,
            ScheduleCreate(
                service_type="Late service",
                interval_miles=5000,
                due_mileage=9000
            )
        )
        add_schedule(
            self.db, 2, 2,
            ScheduleCreate(
                service_type="Other owner",
                interval_miles=5000,
                due_mileage=21000
            )
        )

        reminders = list_reminders(self.db, 1, self.today)

        self.assertEqual(
            [item["service_type"] for item in reminders],
            ["Late service", "Soon service", "Later service"]
        )
        self.assertEqual(reminders[0]["status"], "overdue")
        self.assertEqual(reminders[1]["status"], "approaching")
        self.assertEqual(reminders[2]["status"], "upcoming")
        self.assertEqual(reminders[0]["miles_remaining"], -1000)
        self.assertEqual(reminders[1]["days_remaining"], 7)
        self.assertTrue(reminders[0]["created_at"])


if __name__ == "__main__":
    unittest.main()

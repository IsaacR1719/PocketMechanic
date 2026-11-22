# PocketMechanic test plan — reminders

Reminder cases below follow the same case-id style as the cases already in the project test plan: AUTH-01–04, VEH-01–05, MAIN-01–05, EXP-01–05, and SYS-01. Those earlier cases are unchanged. The Word test plan is not in this repository, so the reminder cases live here.

Scheduling (Contracts 19–23) and cost analysis are already covered by `backend/tests/test_schedules.py`, `backend/tests/test_dashboard.py`, and `backend/tests/test_cost_analysis.py`. This file does not retest schedule editing.

Reminders are not stored. `get_reminders` asks `calculate_next_due` for each of the signed-in user's schedules. A reminder is OVERDUE when the vehicle's mileage or today's date is at or past due. It is UPCOMING when it is within 500 miles or 30 days and not overdue. Anything outside both windows is left out.

Each reminder dict, and `GET /reminders`, uses these keys: `schedule_id`, `vehicle_id`, `vehicle_name`, `service_type`, `status`, `due_mileage`, `due_date`.

Automated cases run with the other backend tests:

```bash
cd backend
python -m unittest discover -s tests -v
```

## REM-01 Mileage at or past due

- **Objective:** A mileage schedule is OVERDUE when the odometer is at or past the due mileage from `calculate_next_due`.
- **Preconditions:** Signed in. Vehicle at 15,000 miles. Oil Change schedule whose baseline plus interval is 15,000 miles. No time interval.
- **Steps:** Call `get_reminders` for that user. Raise the odometer to 15,001 and call it again.
- **Expected:** One reminder. `status` is `OVERDUE`, `due_mileage` is 15000, `due_date` is null. Still OVERDUE at 15,001.
- **Automated:** `test_mileage_at_or_past_due_is_overdue`

## REM-02 Mileage coming due

- **Objective:** 500 miles remaining is UPCOMING. 501 miles remaining is not a reminder.
- **Preconditions:** Vehicle at 10,000 miles. One schedule due at 10,500. Another due at 10,501. No time intervals.
- **Steps:** Call `get_reminders`.
- **Expected:** Only the 10,500 schedule is returned, with `status` `UPCOMING` and `due_mileage` equal to `calculate_next_due`.
- **Automated:** `test_mileage_window_is_500`

## REM-03 Date at or past due

- **Objective:** A time schedule is OVERDUE when today is the due date or later.
- **Preconditions:** Two time-only schedules. One is due today. One was due yesterday.
- **Steps:** Call `get_reminders`.
- **Expected:** Both are `OVERDUE`. `due_date` matches the target date. `due_mileage` is null.
- **Automated:** `test_date_at_or_past_due_is_overdue`

## REM-04 Date coming due

- **Objective:** 30 days out is UPCOMING. 31 days out is not a reminder.
- **Preconditions:** Two time-only schedules, due in 30 days and 31 days.
- **Steps:** Call `get_reminders`.
- **Expected:** Only the 30-day schedule is returned, `status` `UPCOMING`, `due_date` equal to `calculate_next_due`.
- **Automated:** `test_date_window_is_30_days`

## REM-05 Either condition, overdue wins

- **Objective:** Mileage or date can qualify. If either one is at or past due, the status is OVERDUE even when the other is only upcoming.
- **Preconditions:** One vehicle and five schedules: mileage overdue with a far date, mileage within 500 with a far date, mileage far with a date inside 30 days, mileage overdue with a date inside 30 days, and one outside both windows.
- **Steps:** Call `get_reminders`.
- **Expected:** The two mileage-overdue schedules are `OVERDUE`. The mileage-soon and date-soon schedules are `UPCOMING`. The schedule outside both windows is absent.
- **Automated:** `test_either_window_qualifies_and_overdue_wins`

## REM-06 Maintenance record moves the due point

- **Objective:** The due point is the one from `calculate_next_due`, so a matching service record replaces the schedule start.
- **Preconditions:** Oil Change schedule, interval 500 miles, start mileage 0. A maintenance record "oil change" at 19,800 miles today. Vehicle odometer 20,000.
- **Steps:** Call `get_reminders` and `calculate_next_due`.
- **Expected:** Baseline comes from the record. `due_mileage` is 20300. Status is `UPCOMING` (300 miles left), not overdue from the start mileage of 0.
- **Automated:** `test_matching_record_moves_the_due_point`

## REM-07 Another user's schedules stay hidden

- **Objective:** Reminders are limited to the signed-in user's vehicles.
- **Preconditions:** Two users, each with an overdue schedule.
- **Steps:** Call `get_reminders` for each user.
- **Expected:** Each list contains only that user's schedule. `vehicle_name` is the year, make, and model.
- **Automated:** `test_other_users_schedules_are_hidden`

## REM-08 Payload keys

- **Objective:** The dict keys stay the ones the dashboard already reads.
- **Steps:** Call `get_reminders` for a schedule inside the 500-mile window.
- **Expected:** Keys are exactly `schedule_id`, `vehicle_id`, `vehicle_name`, `service_type`, `status`, `due_mileage`, `due_date`. The dict validates as `DashboardReminder`.
- **Automated:** `test_payload_keys_match_the_dashboard`

## REM-09 GET /reminders

- **Objective:** The API exposes the list to the signed-in user.
- **Preconditions:** Backend running. User signed in (session cookie).
- **Steps:**
  1. `GET /reminders` with the session cookie.
  2. Repeat without a session.
  3. Confirm the route is registered on the app.
- **Expected:** Step 1 returns the same list as `get_reminders`. Step 2 returns 401. The app route is `GET /reminders`.
- **Automated:** `test_get_reminders_route` checks that `GET /reminders` is registered. The 401 check is the same session rule as the other routes (`get_current_user`).

## REM-10 Dashboard uses the same list

- **Objective:** The dashboard facade shows these reminders once the service is available.
- **Steps:** Create one upcoming schedule and call `get_dashboard_summary`.
- **Expected:** `reminders_available` is true. `reminders` equals `get_reminders` for that user. The Upcoming Services stat counts that list, and Needs Attention links to `/reminders`.
- **Automated:** `test_dashboard_includes_the_same_reminders`

## REM-11 Reminders page

- **Objective:** `/reminders` lists overdue and due-soon services, and the sidebar item is the one already in the layout.
- **Preconditions:** Signed in at `http://localhost:5173`.
- **Steps:**
  1. Open Reminders with no vehicles.
  2. Add a vehicle and a schedule that is not inside 500 miles or 30 days.
  3. Add or edit a schedule so a service is overdue, and another so a service is due soon.
  4. Use the All, Overdue, and Due soon filters.
  5. Open a reminder. It goes to that vehicle.
- **Expected:** Step 1 says to add a vehicle first. Step 2 says nothing is due soon. Step 3 lists both, with Overdue and Due soon counts. Filters limit the list. The sidebar Reminders item is highlighted.

## REM-12 Reminder popup

- **Objective:** A popup surfaces the same reminders without leaving the current page.
- **Preconditions:** Signed in, with at least one overdue or due-soon schedule. Popup not dismissed this browser session.
- **Steps:**
  1. Open the dashboard.
  2. Dismiss the popup.
  3. Open it again from the bell in the top bar.
  4. Choose View reminders.
- **Expected:** The popup lists the service, vehicle, status, and due mileage or date. Dismiss closes it and it stays closed for the rest of the session. The bell opens it again. View reminders lands on `/reminders`.

## REM-13 Nothing due

- **Objective:** A schedule outside both windows produces an empty reminder list.
- **Preconditions:** Vehicle at 10,000 miles. Mileage interval 5,000 and no time interval, so the next due mileage is 15,000.
- **Steps:** Call `get_reminders`.
- **Expected:** An empty list, including for a user who has a vehicle and no schedules.
- **Automated:** `test_nothing_due_is_an_empty_list`

## REM-14 Order

- **Objective:** Overdue reminders are listed before upcoming ones.
- **Steps:** Create an upcoming schedule first, then an overdue one, and call `get_reminders`.
- **Expected:** The overdue schedule is first even though it was created second.
- **Automated:** `test_overdue_is_listed_before_upcoming`

## Execution

`python -m unittest discover -s tests` from `backend/` passed, including REM-01 through REM-10, REM-13, and REM-14.

REM-11 and REM-12 were also walked through in the browser. A signed-in user with no vehicle sees "Add a vehicle first." A schedule 500 miles out is Due soon. A schedule 800 miles out, and a schedule 6 months out, stay off the list. Raising the odometer to the due mileage makes that service Overdue and brings the 800-mile schedule into Due soon. The All, Overdue, and Due soon filters match those rows. The dashboard Upcoming Services count and Needs Attention list use the same reminders. The popup opens on the dashboard, Dismiss keeps it closed for the session, and the bell opens it again. A second account does not see the first account's reminders. At 700px the page stacks and the sidebar stays usable.

# MediBook: Hospital Appointment Booking System

Patients book appointments with doctors, doctors manage their day, and admins track hospital activity. The main focus is **double-booking prevention**: two patients can never book the same slot, even when they click at the same moment.

## Features
- **Patient:** register, log in, find doctors (filter by hospital, department, name), view live slots, book and cancel appointments
- **Doctor:** daily schedule, mark appointments as completed or no-show
- **Admin:** dashboard with totals, cancellation and no-show rates, top doctors; manage hospitals, doctors, schedules and leaves

## Tech stack
Python, Django, Django REST Framework, MySQL, JWT authentication, HTML/CSS/JavaScript

## Screenshots

| Find a doctor | Book a slot |
|---|---|
| ![Find a doctor](appointment-booking/screenshots/index.png) | ![Book a slot](appointment-booking/screenshots/booking.png) |

| Doctor dashboard | Admin dashboard |
|---|---|
| ![Doctor dashboard](appointment-booking/screenshots/doctor_booking.png) | ![Admin dashboard](appointment-booking/screenshots/admin_dashboard.png) |

## How double booking is prevented
1. **Transaction:** the booking succeeds or fails as one unit.
2. **Row lock (`select_for_update`):** bookings for the same doctor run one at a time.
3. **Unique database constraint:** the last line of defence. A cancelled slot becomes free again.

A multithreaded test fires 5 simultaneous bookings for one slot and checks that exactly one succeeds.

## Run locally
```bash
git clone https://github.com/<your-username>/appointment-booking.git
cd appointment-booking
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
1. Create a MySQL database named `appointment_db`.
2. Copy `.env.example` to `.env` and fill in your database details.
3. Run:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
4. Open `frontend/login.html` with VS Code Live Server (port 5500).

Run the concurrency test: `python manage.py test appointments.tests.test_concurrency`

## API overview
Base URL `/api`. Protected endpoints need `Authorization: Bearer <token>`.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| Browse | `GET /hospitals`, `GET /doctors`, `GET /doctors/{id}/slots?date=` |
| Patient | `POST /appointments`, `GET /appointments`, `DELETE /appointments/{id}` |
| Doctor | `GET /doctor/appointments`, `PATCH /doctor/appointments/{id}/status` |
| Admin | `GET /admin/stats`, CRUD on `/admin/hospitals`, `/admin/departments`, `/admin/doctors` |

## Author
Kalpesh Dharmraj Bhure
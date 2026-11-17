import threading
from datetime import time, timedelta

from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from appointments.models import (Appointment, Department, Doctor,
                                 DoctorSchedule, Hospital, Patient)
from appointments.services import BookingError, book_appointment, cancel_appointment


def next_monday():
    """Aaj ke baad ka agla Monday (schedule Monday ka bana rahe, test kabhi bhi chale)."""
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7 or 7  # weekday 0 = Monday
    return today + timedelta(days=days_ahead)


class ConcurrentBookingTests(TransactionTestCase):
    """
    TestCase ki jagah TransactionTestCase kyun:
    TestCase har test ko ek bade transaction me chalata (end me rollback).
    Threads ke apne alag DB connection hote, unko wo uncommitted data dikhta hi nahi.
    TransactionTestCase data asli me commit karta, isliye threads data dekh paate.
    """

    def setUp(self):
        self.day = next_monday()

        hospital = Hospital.objects.create(name="Test Hospital", city="Nagpur", address="x")
        dept = Department.objects.create(hospital=hospital, name="Cardiology")
        doc_user = User.objects.create_user("dr_test", password="Test@12345")
        self.doctor = Doctor.objects.create(
            user=doc_user, department=dept, qualification="MD",
            consultation_fee=500, slot_minutes=15,
        )
        # Monday 10:00 se 11:00 = 4 slots
        DoctorSchedule.objects.create(
            doctor=self.doctor, day_of_week=0,
            start_time=time(10, 0), end_time=time(11, 0),
        )

        # 5 alag patients
        self.patients = []
        for i in range(5):
            u = User.objects.create_user(f"patient{i}", password="Test@12345")
            self.patients.append(Patient.objects.create(user=u))

    def run_parallel(self, jobs):
        """
        jobs ki list ek saath chalata, results wapas deta.
        Barrier: sab threads yahan ruk ke ek saath chhoote, asli race banti.
        """
        barrier = threading.Barrier(len(jobs))
        results = []

        def worker(job):
            try:
                barrier.wait()  # sab ready hone tak ruko
                job()
                results.append(("ok", None))
            except BookingError as e:
                results.append(("fail", e.code))
            except Exception as e:  # koi anjaan error = bug, test fail hoga
                results.append(("error", repr(e)))
            finally:
                # Thread ka DB connection band karna zaruri, warna test DB drop me atakta
                connection.close()

        threads = [threading.Thread(target=worker, args=(j,)) for j in jobs]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results

    def test_same_slot_only_one_wins(self):
        """5 patient, same slot, ek saath. Sirf 1 booking honi chahiye."""
        jobs = [
            (lambda p=p: book_appointment(p, self.doctor, self.day, time(10, 0)))
            for p in self.patients
        ]
        results = self.run_parallel(jobs)

        ok = [r for r in results if r[0] == "ok"]
        fail = [r for r in results if r[0] == "fail"]
        errors = [r for r in results if r[0] == "error"]

        self.assertEqual(errors, [], f"Anjaan error aaya: {errors}")
        self.assertEqual(len(ok), 1, f"Ek hi jeetna chahiye, results: {results}")
        self.assertEqual(len(fail), 4)
        # Haarne walon ko sahi reason mila
        for _, code in fail:
            self.assertIn(code, {"slot_unavailable", "slot_taken"})

        # Asli proof: DB me exactly 1 booked row
        booked = Appointment.objects.filter(
            doctor=self.doctor, date=self.day, start_time=time(10, 0), status="booked"
        ).count()
        self.assertEqual(booked, 1)

    def test_different_slots_all_succeed(self):
        """Alag-alag slot ek saath book hon to sab succeed (lock se galat reject nahi)."""
        slots = [time(10, 0), time(10, 15), time(10, 30), time(10, 45)]
        jobs = [
            (lambda p=p, s=s: book_appointment(p, self.doctor, self.day, s))
            for p, s in zip(self.patients, slots)
        ]
        results = self.run_parallel(jobs)

        self.assertEqual([r for r in results if r[0] != "ok"], [])
        self.assertEqual(
            Appointment.objects.filter(doctor=self.doctor, status="booked").count(), 4
        )

    def test_cancelled_slot_can_be_rebooked(self):
        """Cancel hone ke baad slot free hota (active_slot NULL wali trick)."""
        p1, p2 = self.patients[0], self.patients[1]

        appt = book_appointment(p1, self.doctor, self.day, time(10, 0))

        # Slot bhara hai, p2 nahi le sakta
        with self.assertRaises(BookingError):
            book_appointment(p2, self.doctor, self.day, time(10, 0))

        cancel_appointment(appt.id, p1)

        # Ab p2 le sakta
        new_appt = book_appointment(p2, self.doctor, self.day, time(10, 0))
        self.assertEqual(new_appt.status, "booked")
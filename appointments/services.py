from datetime import datetime, timedelta
from django.utils import timezone
from .models import Appointment, DoctorLeave, DoctorSchedule, Doctor

# imports replace
from datetime import datetime, timedelta
from django.db import IntegrityError, transaction


MAX_ADVANCE_DAYS = 30  # kitne din aage tak booking

def generate_slots(doctor, day):
    """
    Us din ke saare POSSIBLE slots (start times) banata.
    Slots DB me store nahi hote, schedule se on-the-fly bante.
    Fayda: schedule badla to purana data fix nahi karna padta.
    """
    # Doctor ki chutti ho to koi slot nahi
    if DoctorLeave.objects.filter(doctor=doctor, date=day).exists():
        return []

    step = timedelta(minutes=doctor.slot_minutes)
    slots = []

    # day.weekday(): Mon=0 ... Sun=6 (model ke day_of_week se match)
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor, day_of_week=day.weekday()
    )

    # Ek din me kai shift ho sakti (subah 10-1, shaam 5-8), isliye loop
    for sch in schedules:
        # time + timedelta direct nahi hota, isliye datetime me convert
        cur = datetime.combine(day, sch.start_time)
        end = datetime.combine(day, sch.end_time)

        # cur + step <= end: aakhri slot shift ke end se bahar na jaye
        while cur + step <= end:
            slots.append(cur.time())
            cur += step

    return sorted(slots)


def get_available_slots(doctor, day):
    """Possible slots me se booked aur nikle hue (past) slots hata do."""
    # Sirf status="booked". Cancelled slot wapas available.
    # set: "in" check O(1), list me O(n) hota
    booked = set(
        Appointment.objects.filter(doctor=doctor, date=day, status="booked")
        .values_list("start_time", flat=True)
    )

    now = timezone.localtime()  # USE_TZ=True, IST time
    available = []

    for s in generate_slots(doctor, day):
        if s in booked:
            continue
        # Aaj ki date pe nikla hua time book nahi hona chahiye
        if day == now.date() and s <= now.time():
            continue
        available.append(s)

    return available

class BookingError(Exception):
    """Booking rule tootne par. API isse HTTP error me badalti."""

    def __init__(self, message, status_code=400, code="booking_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code  # 400 = galat request, 409 = conflict
        self.code = code


def book_appointment(patient, doctor, day, start, reason=""):
    """
    Race-condition safe booking. 3 layer ki suraksha:
    1. transaction.atomic: sab kuch ek unit (ya pura ya kuch nahi)
    2. select_for_update: doctor row lock, ek doctor ki booking ek-ek karke
    3. active_slot unique constraint: DB level akhri deewar
    """
    today = timezone.localdate()

    # --- Basic rules (lock se pehle, sasta check) ---
    if not doctor.is_active:
        raise BookingError("Ye doctor abhi available nahi hai.")
    if day < today:
        raise BookingError("Past date me booking nahi ho sakti.")
    if day > today + timedelta(days=MAX_ADVANCE_DAYS):
        raise BookingError(f"Sirf agle {MAX_ADVANCE_DAYS} din tak booking hoti hai.")

    with transaction.atomic():
        # Doctor ki row LOCK. Dusra request yahin ruk jaata jab tak
        # ye transaction commit/rollback na ho. Lock pehle, slot check baad me,
        # isliye check hamesha latest committed data dekhta.
        Doctor.objects.select_for_update().get(pk=doctor.pk)

        # Slot ab bhi available hai? (lock ke andar check, safe)
        if start not in get_available_slots(doctor, day):
            raise BookingError(
                "Ye slot available nahi hai (book ho chuka ya schedule me nahi).",
                status_code=409,
                code="slot_unavailable",
            )

        # Patient ka usi time pe kisi aur doctor ke saath booking na ho
        if Appointment.objects.filter(
            patient=patient, date=day, start_time=start, status="booked"
        ).exists():
            raise BookingError(
                "Is time pe aapki pehle se ek booking hai.",
                status_code=409,
                code="patient_clash",
            )

        # end_time = start + slot length
        end = (datetime.combine(day, start) + timedelta(minutes=doctor.slot_minutes)).time()

        try:
            # Nested atomic = savepoint. IntegrityError pe sirf ye hissa rollback,
            # outer transaction toot ke 500 nahi deta.
            with transaction.atomic():
                return Appointment.objects.create(
                    patient=patient,
                    doctor=doctor,
                    date=day,
                    start_time=start,
                    end_time=end,
                    reason=reason,
                )
        except IntegrityError:
            # Kisi tarah do request nikal gayi to DB unique (active_slot) rok deta
            raise BookingError(
                "Slot abhi kisi aur ne book kar liya.",
                status_code=409,
                code="slot_taken",
            )
from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment, DoctorLeave, DoctorSchedule


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
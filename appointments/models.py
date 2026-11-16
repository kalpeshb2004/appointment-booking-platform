from django.contrib.auth.models import User
from django.db import models


class Hospital(models.Model):
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.name}, {self.city}"


class Department(models.Model):
    # Ek hospital ke kai department (Cardiology, ENT...)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE,
                                 related_name="departments")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("hospital", "name")  # same hospital me duplicate naam nahi

    def __str__(self):
        return f"{self.name} ({self.hospital.name})"


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # login account
    department = models.ForeignKey(Department, on_delete=models.PROTECT,
                                   related_name="doctors")
    qualification = models.CharField(max_length=150)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2)
    slot_minutes = models.PositiveIntegerField(default=15)  # ek slot kitne min ka
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class DoctorSchedule(models.Model):
    # Doctor ka weekly timetable (kis din kab se kab tak)
    DAYS = [(0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu"),
            (4, "Fri"), (5, "Sat"), (6, "Sun")]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE,
                               related_name="schedules")
    day_of_week = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ("doctor", "day_of_week", "start_time")


class DoctorLeave(models.Model):
    # Doctor ki chutti: us din slots nahi milenge
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE,
                               related_name="leaves")
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("doctor", "date")


class Patient(models.Model):
    GENDER = [("M", "Male"), ("F", "Female"), ("O", "Other")]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER, blank=True)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username


class Appointment(models.Model):
    STATUS = [("booked", "Booked"), ("cancelled", "Cancelled"),
              ("completed", "Completed"), ("no_show", "No show")]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,
                                related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE,
                               related_name="appointments")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="booked")

    # Double-booking ki DB-level suraksha:
    # booked hone par unique string, cancel hone par NULL.
    # MySQL me kai NULL allowed, isliye cancelled slot dobara book ho sakta.
    active_slot = models.CharField(max_length=60, null=True, blank=True,
                                   unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["doctor", "date"])]  # slot query fast

    def save(self, *args, **kwargs):
        if self.status == "booked":
            self.active_slot = f"{self.doctor_id}-{self.date}-{self.start_time}"
        else:
            self.active_slot = None
        super().save(*args, **kwargs)
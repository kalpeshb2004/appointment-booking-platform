from datetime import datetime

from django.db.models import Count, Q, ProtectedError
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import (Appointment, Department, Doctor, DoctorLeave,DoctorSchedule, Hospital, Patient)

from appointments.permissions import IsAdmin
from django.db import transaction
from rest_framework import generics, viewsets
from rest_framework.decorators import action

from .serializers import (AdminDepartmentSerializer, AdminDoctorCreateSerializer,AdminDoctorSerializer, AdminHospitalSerializer,LeaveInputSerializer, ScheduleInputSerializer)




def parse_date(value, field):
    """?from= / ?to= ko date me badalta. Galat format par 400."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({field: "Format galat. YYYY-MM-DD use kar."})


def pct(part, total):
    """Percentage. total 0 ho to 0 (ZeroDivisionError se bachav)."""
    return round(part * 100 / total, 1) if total else 0


# Status-wise count ke liye reusable aggregates.
# Count(filter=Q(...)) = SQL ka COUNT(CASE WHEN ...), ek hi query me sab counts.
STATUS_COUNTS = {
    "booked": Count("id", filter=Q(status="booked")),
    "completed": Count("id", filter=Q(status="completed")),
    "cancelled": Count("id", filter=Q(status="cancelled")),
    "no_show": Count("id", filter=Q(status="no_show")),
}


class AdminStatsView(APIView):
    """
    GET /api/admin/stats
    Optional: ?from=YYYY-MM-DD  ?to=YYYY-MM-DD  (appointment date ke hisaab se)
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        qs = Appointment.objects.all()

        # --- optional date range ---
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        if date_from:
            date_from = parse_date(date_from, "from")
            qs = qs.filter(date__gte=date_from)
        if date_to:
            date_to = parse_date(date_to, "to")
            qs = qs.filter(date__lte=date_to)
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"from": "'from' date 'to' se pehle honi chahiye."})

        # --- 1) Overall: ek query me total + status-wise ---
        overall = qs.aggregate(total=Count("id"), **STATUS_COUNTS)
        total = overall["total"]

        # --- 2) Doctor-wise: GROUP BY doctor, ek query ---
        by_doctor = (
            qs.values(
                "doctor_id",
                "doctor__user__first_name",
                "doctor__user__last_name",
                "doctor__user__username",
                "doctor__department__name",
            )
            .annotate(total=Count("id"), **STATUS_COUNTS)
            .order_by("-total")[:10]  # top 10 doctors
        )
        doctors = []
        for row in by_doctor:
            name = f"{row['doctor__user__first_name']} {row['doctor__user__last_name']}".strip()
            doctors.append({
                "doctor_id": row["doctor_id"],
                "name": name or row["doctor__user__username"],
                "department": row["doctor__department__name"],
                "total": row["total"],
                "completed": row["completed"],
                "cancelled": row["cancelled"],
                "no_show": row["no_show"],
                "no_show_rate": pct(row["no_show"], row["total"]),
            })

        # --- 3) Department-wise: GROUP BY department ---
        by_dept = (
            qs.values("doctor__department__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        departments = [
            {"department": r["doctor__department__name"], "total": r["total"]}
            for r in by_dept
        ]

        # --- 4) Aane wali bookings (date range se alag, hamesha aaj se aage) ---
        upcoming = Appointment.objects.filter(
            status="booked", date__gte=timezone.localdate()
        ).count()

        return Response({
            "range": {"from": date_from or None, "to": date_to or None},
            "totals": {
                "appointments": total,
                "booked": overall["booked"],
                "completed": overall["completed"],
                "cancelled": overall["cancelled"],
                "no_show": overall["no_show"],
                "upcoming_booked": upcoming,
            },
            "rates": {
                "cancelled_percent": pct(overall["cancelled"], total),
                "no_show_percent": pct(overall["no_show"], total),
                "completed_percent": pct(overall["completed"], total),
            },
            "counts": {
                "patients": Patient.objects.count(),
                "active_doctors": Doctor.objects.filter(is_active=True).count(),
            },
            "by_doctor": doctors,
            "by_department": departments,
        })

class ProtectedDeleteMixin:
    """
    Doctor wale department ko delete karo to Django ProtectedError deta
    (model me on_delete=PROTECT). Bina handle kiye 500 crash.
    Yahan pakad ke 409 Conflict + saaf message dete.
    """

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Ye delete nahi ho sakta, iske under doctors/data juda hai. "
                           "Pehle unhe hatao ya doosre department me daalo.",
                 "code": "in_use"},
                status=409,
            )


class AdminHospitalViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    ModelViewSet = list, retrieve, create, update, partial_update, destroy
    ek class me. Router URLs khud banata.
    """

    queryset = Hospital.objects.order_by("name")
    serializer_class = AdminHospitalSerializer
    permission_classes = [IsAdmin]  # sirf admin (is_staff)


class AdminDepartmentViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = AdminDepartmentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        # select_related: hospital_name ke liye alag query nahi (N+1 se bachav)
        qs = Department.objects.select_related("hospital").order_by("hospital__name", "name")
        hospital = self.request.query_params.get("hospital")  # ?hospital=<id>
        if hospital and hospital.isdigit():
            qs = qs.filter(hospital_id=hospital)
        return qs

class AdminDoctorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = Doctor.objects.select_related(
            "user", "department__hospital"
        ).order_by("user__first_name")

        # Admin ko inactive doctors bhi dikhte (public API me nahi dikhte)
        p = self.request.query_params
        if p.get("hospital", "").isdigit():
            qs = qs.filter(department__hospital_id=p["hospital"])
        if p.get("department", "").isdigit():
            qs = qs.filter(department_id=p["department"])
        if p.get("is_active") in ("true", "false"):
            qs = qs.filter(is_active=p["is_active"] == "true")
        return qs

    def get_serializer_class(self):
        # create ke liye alag serializer (username/password chahiye), baaki ke liye read/update wala
        if self.action == "create":
            return AdminDoctorCreateSerializer
        return AdminDoctorSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminDoctorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        # Response me read serializer: password wapas nahi jaata, id/naam sab milta
        return Response(AdminDoctorSerializer(doctor).data, status=201)

    def destroy(self, request, *args, **kwargs):
        """Hard delete nahi, deactivate. Appointment history bachti."""
        doctor = self.get_object()

        # Aane wali booked appointments hain to pehle unka intezaam karo
        upcoming = Appointment.objects.filter(
            doctor=doctor, status="booked", date__gte=timezone.localdate()
        ).count()
        if upcoming:
            return Response(
                {"detail": f"Is doctor ki {upcoming} aane wali booked appointments hain. "
                           "Pehle unhe complete/cancel karo.",
                 "code": "has_upcoming"},
                status=409,
            )

        with transaction.atomic():
            doctor.is_active = False
            doctor.save()
            doctor.user.is_active = False  # login bhi band
            doctor.user.save()
        return Response({"message": "Doctor deactivate ho gaya."})

    @action(detail=True, methods=["post"], url_path="schedule")
    def set_schedule(self, request, pk=None):
        """POST /api/admin/doctors/<id>/schedule : poora weekly schedule REPLACE"""
        doctor = self.get_object()
        serializer = ScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Replace semantics: purana hatao, naya daalo, ek transaction me.
        # Beech me error aaye to purana schedule safe rehta.
        with transaction.atomic():
            DoctorSchedule.objects.filter(doctor=doctor).delete()
            DoctorSchedule.objects.bulk_create([
                DoctorSchedule(doctor=doctor, **item)
                for item in serializer.validated_data["schedule"]
            ])

        rows = doctor.schedules.order_by("day_of_week", "start_time")
        return Response({
            "message": "Schedule set ho gaya.",
            "schedule": [
                {"day": r.get_day_of_week_display(),
                 "start_time": r.start_time.strftime("%H:%M"),
                 "end_time": r.end_time.strftime("%H:%M")}
                for r in rows
            ],
        })

    @action(detail=True, methods=["post"], url_path="leaves")
    def add_leave(self, request, pk=None):
        """POST /api/admin/doctors/<id>/leaves : us din ki chutti"""
        doctor = self.get_object()
        serializer = LeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = serializer.validated_data["date"]

        if day < timezone.localdate():
            raise ValidationError({"date": "Past date ki leave nahi lag sakti."})

        # Us din booked appointments hain to leave nahi, pehle unhe hatao
        booked = Appointment.objects.filter(
            doctor=doctor, date=day, status="booked"
        ).count()
        if booked:
            return Response(
                {"detail": f"Us din {booked} booked appointments hain. Pehle unhe cancel karo.",
                 "code": "has_bookings"},
                status=409,
            )

        # get_or_create: dobara same date daali to naya row nahi
        leave, created = DoctorLeave.objects.get_or_create(
            doctor=doctor, date=day,
            defaults={"reason": serializer.validated_data["reason"]},
        )
        if not created:
            return Response({"detail": "Is date ki leave pehle se hai.", "code": "exists"},
                            status=409)
        return Response(
            {"id": leave.id, "date": leave.date, "reason": leave.reason}, status=201
        )


class AdminLeaveDeleteView(generics.DestroyAPIView):
    """DELETE /api/admin/leaves/<id> : leave hatana (slots wapas khul jaate)"""

    permission_classes = [IsAdmin]
    queryset = DoctorLeave.objects.all()
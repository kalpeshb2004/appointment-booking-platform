
# imports replace
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny,IsAuthenticated
from appointments.models import Doctor, Hospital
from .serializers import (DepartmentSerializer, DoctorDetailSerializer,DoctorSerializer, HospitalSerializer)
# imports me ye add kar (purane same rehne de)
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from appointments.services import get_available_slots

MAX_ADVANCE_DAYS = 30  # kitne din aage tak booking allow

class HospitalListView(ListAPIView):
    """
    GET /api/hospitals
    Optional filters: ?city=Nagpur  ?search=care
    """

    serializer_class = HospitalSerializer
    permission_classes = [AllowAny]  # public API, login nahi chahiye
    authentication_classes = []      # token bheja bhi to ignore (expired token se fail nahi)

    def get_queryset(self):
        # ListAPIView is queryset ko serializer se list me convert karke bhejta
        qs = Hospital.objects.all().order_by("name")

        # query_params = URL ke ?key=value
        city = self.request.query_params.get("city")
        search = self.request.query_params.get("search")

        if city:
            qs = qs.filter(city__iexact=city)      # iexact: exact match, case ignore
        if search:
            qs = qs.filter(name__icontains=search) # icontains: naam me kahin bhi match
        return qs


class HospitalDepartmentListView(ListAPIView):
    """GET /api/hospitals/<id>/departments : ek hospital ke departments"""

    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        # Hospital nahi mila to 404 (khaali list nahi), client ko clear signal
        hospital = get_object_or_404(Hospital, pk=self.kwargs["pk"])
        # related_name="departments" se reverse relation
        return hospital.departments.order_by("name")

def active_doctors():
    # Sirf active doctor. select_related: user/department/hospital ek hi JOIN
    # query me aa jaate, warna har doctor ke liye alag query chalti (N+1 problem).
    return Doctor.objects.filter(is_active=True).select_related(
        "user", "department__hospital"
    )


class DoctorListView(ListAPIView):
    """
    GET /api/doctors
    Filters: ?hospital=<id>  ?department=<id>  ?search=<naam>
    """

    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        qs = active_doctors().order_by("user__first_name")
        params = self.request.query_params

        hospital = params.get("hospital")
        department = params.get("department")
        search = params.get("search")

        # id number hona chahiye, warna 400 (500 crash nahi)
        for key, value in (("hospital", hospital), ("department", department)):
            if value and not value.isdigit():
                raise ValidationError({key: "Number (id) dena zaruri hai."})

        if hospital:
            qs = qs.filter(department__hospital_id=hospital)
        if department:
            qs = qs.filter(department_id=department)
        if search:
            # Q objects: OR condition. Naam ya username me kahin bhi match
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
            )
        return qs


class DoctorDetailView(RetrieveAPIView):
    """GET /api/doctors/<id> : ek doctor + uska weekly schedule"""

    serializer_class = DoctorDetailSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        # prefetch_related: schedules alag ek query me aate (reverse relation)
        return active_doctors().prefetch_related("schedules")

class DoctorSlotsView(APIView):
    """
    GET /api/doctors/<id>/slots?date=2026-11-23
    Us din ke available slots. Login zaruri (default IsAuthenticated).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Inactive/galat doctor → 404
        doctor = get_object_or_404(Doctor, pk=pk, is_active=True)

        # --- date validate ---
        date_str = request.query_params.get("date")
        if not date_str:
            raise ValidationError({"date": "date zaruri hai (format: YYYY-MM-DD)."})
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"date": "Format galat. YYYY-MM-DD use kar."})

        today = timezone.localdate()
        if day < today:
            raise ValidationError({"date": "Past date ke slots nahi milte."})
        if day > today + timedelta(days=MAX_ADVANCE_DAYS):
            raise ValidationError(
                {"date": f"Sirf agle {MAX_ADVANCE_DAYS} din tak booking hoti hai."}
            )

        slots = get_available_slots(doctor, day)

        return Response({
            "doctor_id": doctor.id,
            "date": day,
            "slot_minutes": doctor.slot_minutes,
            "total": len(slots),
            "slots": [s.strftime("%H:%M") for s in slots],  # "10:00" format
        })
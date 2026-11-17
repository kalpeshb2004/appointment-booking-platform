
# imports replace
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from appointments.models import Doctor, Hospital

from .serializers import (DepartmentSerializer, DoctorDetailSerializer,DoctorSerializer, HospitalSerializer)

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
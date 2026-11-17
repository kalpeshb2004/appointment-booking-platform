from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment, Doctor
from appointments.permissions import IsPatient
from appointments.services import BookingError, book_appointment,cancel_appointment

from .serializers import AppointmentSerializer, BookingSerializer

# Model ke STATUS choices se match. Filter me galat value pakadne ke liye.
VALID_STATUS = {"booked", "cancelled", "completed", "no_show"}


class AppointmentListCreateView(APIView):
    """
    GET  /api/appointments : meri bookings (filter ke saath)
    POST /api/appointments : slot book karna
    """

    permission_classes = [IsPatient]  # login + patient role zaruri

    def get(self, request):
        # SECURITY: filter(patient=request.user.patient)
        # Patient sirf apni bookings dekhe, kisi aur ki nahi.
        # (Ye check chhoot gaya to data leak, bahut bada bug.)
        qs = (
            Appointment.objects.filter(patient=request.user.patient)
            # N+1 se bachne ke liye: doctor, user, department, hospital ek JOIN me
            .select_related("doctor__user", "doctor__department__hospital")
            .order_by("-date", "-start_time")  # naya pehle
        )

        params = request.query_params
        status_param = params.get("status")
        date_str = params.get("date")

        # --- ?status=booked ---
        if status_param:
            if status_param not in VALID_STATUS:
                raise ValidationError(
                    {"status": f"Valid values: {', '.join(sorted(VALID_STATUS))}"}
                )
            qs = qs.filter(status=status_param)

        # --- ?date=2026-11-23 ---
        if date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({"date": "Format galat. YYYY-MM-DD use kar."})
            qs = qs.filter(date=day)

        # --- ?upcoming=true : aane wali booked appointments, sabse nazdeek pehle ---
        if params.get("upcoming") == "true":
            qs = qs.filter(
                status="booked", date__gte=timezone.localdate()
            ).order_by("date", "start_time")

        # many=True: queryset (kai objects) ko list me convert
        return Response(AppointmentSerializer(qs, many=True).data)

    def post(self, request):
        # 1) Input format validate (400 auto)
        serializer = BookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2) Doctor exist + active (nahi to 404)
        doctor = get_object_or_404(Doctor, pk=data["doctor_id"], is_active=True)

        # 3) Asli booking, saari business logic service me.
        # View patla: request lena, service bulana, response dena.
        try:
            appointment = book_appointment(
                patient=request.user.patient,
                doctor=doctor,
                day=data["date"],
                start=data["start_time"],
                reason=data["reason"],
            )
        except BookingError as e:
            return Response(
                {"detail": e.message, "code": e.code},
                status=e.status_code,
            )

        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )

class AppointmentDetailView(APIView):
    """
    GET    /api/appointments/<id> : ek booking ki detail
    DELETE /api/appointments/<id> : booking cancel
    """

    permission_classes = [IsPatient]

    def get(self, request, pk):
        # patient=... filter: dusre ki booking par 404
        appointment = get_object_or_404(
            Appointment.objects.select_related(
                "doctor__user", "doctor__department__hospital"
            ),
            pk=pk,
            patient=request.user.patient,
        )
        return Response(AppointmentSerializer(appointment).data)

    def delete(self, request, pk):
        try:
            appointment = cancel_appointment(pk, request.user.patient)
        except BookingError as e:
            return Response(
                {"detail": e.message, "code": e.code}, status=e.status_code
            )
        # 204 (no body) ki jagah 200 + data: frontend ko updated status mil jaata
        return Response(
            {"message": "Appointment cancel ho gayi.",
             "appointment": AppointmentSerializer(appointment).data}
        )
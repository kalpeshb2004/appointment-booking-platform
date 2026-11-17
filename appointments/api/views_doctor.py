from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from appointments.permissions import IsDoctor
from appointments.services import BookingError, update_appointment_status

from .serializers import DoctorAppointmentSerializer, StatusUpdateSerializer

# Model ke STATUS choices se hi nikala (ek jagah truth)
VALID_STATUS = {value for value, _ in Appointment.STATUS}


class DoctorAppointmentListView(APIView):
    """
    GET /api/doctor/appointments
    Filters: ?today=true  ?date=2026-11-23  ?status=booked
    """

    permission_classes = [IsDoctor]

    def get(self, request):
        # SECURITY: sirf is doctor ki bookings
        qs = (
            Appointment.objects.filter(doctor=request.user.doctor)
            .select_related("patient__user")
            .order_by("date", "start_time")
        )

        params = request.query_params
        status_param = params.get("status")
        date_str = params.get("date")

        if status_param:
            if status_param not in VALID_STATUS:
                raise ValidationError(
                    {"status": f"Valid values: {', '.join(sorted(VALID_STATUS))}"}
                )
            qs = qs.filter(status=status_param)

        if params.get("today") == "true":
            qs = qs.filter(date=timezone.localdate())
        elif date_str:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({"date": "Invalid format. Use YYYY-MM-DD."})
            qs = qs.filter(date=day)

        data = DoctorAppointmentSerializer(qs, many=True).data
        return Response({"count": len(data), "appointments": data})


class DoctorAppointmentStatusView(APIView):
    """
    PATCH /api/doctor/appointments/<id>/status
    Body: {"status": "completed"}  ya  {"status": "no_show"}
    """

    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        # 1) Input validate: sirf completed / no_show allowed (baaki 400)
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2) Business rules service me, view patla
        try:
            appointment = update_appointment_status(
                pk, request.user.doctor, serializer.validated_data["status"]
            )
        except BookingError as e:
            return Response(
                {"detail": e.message, "code": e.code}, status=e.status_code
            )

        return Response(
            {
                "message": f"Status updated to '{appointment.status}'.",
                "appointment": DoctorAppointmentSerializer(appointment).data,
            }
        )
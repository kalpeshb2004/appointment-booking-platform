from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from appointments.models import Hospital

from .serializers import DepartmentSerializer, HospitalSerializer


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
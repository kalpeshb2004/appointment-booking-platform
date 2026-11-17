from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views_auth import LoginView, MeView, RegisterView
from .views_patient import AppointmentDetailView,AppointmentListCreateView
from .views_public import (DoctorDetailView, DoctorListView, DoctorSlotsView,
                           HospitalDepartmentListView, HospitalListView)

urlpatterns = [
    # Auth
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me", MeView.as_view(), name="auth-me"),

    # Public
    path("hospitals", HospitalListView.as_view(), name="hospital-list"),
    path("hospitals/<int:pk>/departments", HospitalDepartmentListView.as_view(),
         name="hospital-departments"),
    path("doctors", DoctorListView.as_view(), name="doctor-list"),
    path("doctors/<int:pk>", DoctorDetailView.as_view(), name="doctor-detail"),
    path("doctors/<int:pk>/slots", DoctorSlotsView.as_view(), name="doctor-slots"),

    # Appointments (patient)
    path("appointments", AppointmentListCreateView.as_view(),
         name="appointment-list-create"),
    # urlpatterns me add
    path("appointments/<int:pk>", AppointmentDetailView.as_view(),
         name="appointment-detail"),
]
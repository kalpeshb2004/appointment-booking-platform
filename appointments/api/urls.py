from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views_admin import (AdminDepartmentViewSet, AdminDoctorViewSet,
                          AdminHospitalViewSet, AdminLeaveDeleteView,
                          AdminStatsView)
from .views_auth import LoginView, MeView, RegisterView
from .views_doctor import DoctorAppointmentListView, DoctorAppointmentStatusView
from .views_patient import AppointmentDetailView, AppointmentListCreateView
from .views_public import (DoctorDetailView, DoctorListView, DoctorSlotsView,
                           HospitalDepartmentListView, HospitalListView)

# Router builds the list/detail URLs for the admin CRUD viewsets.
# trailing_slash=False keeps these URLs consistent with the rest (no "/" at the end).
router = SimpleRouter(trailing_slash=False)
router.register("admin/hospitals", AdminHospitalViewSet, basename="admin-hospital")
router.register("admin/departments", AdminDepartmentViewSet, basename="admin-department")
router.register("admin/doctors", AdminDoctorViewSet, basename="admin-doctor")

urlpatterns = [
    # Auth
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me", MeView.as_view(), name="auth-me"),

    # Public browsing
    path("hospitals", HospitalListView.as_view(), name="hospital-list"),
    path("hospitals/<int:pk>/departments", HospitalDepartmentListView.as_view(),
         name="hospital-departments"),
    path("doctors", DoctorListView.as_view(), name="doctor-list"),
    path("doctors/<int:pk>", DoctorDetailView.as_view(), name="doctor-detail"),
    path("doctors/<int:pk>/slots", DoctorSlotsView.as_view(), name="doctor-slots"),

    # Patient
    path("appointments", AppointmentListCreateView.as_view(),
         name="appointment-list-create"),
    path("appointments/<int:pk>", AppointmentDetailView.as_view(),
         name="appointment-detail"),

    # Doctor
    path("doctor/appointments", DoctorAppointmentListView.as_view(),
         name="doctor-appointments"),
    path("doctor/appointments/<int:pk>/status", DoctorAppointmentStatusView.as_view(),
         name="doctor-appointment-status"),

    # Admin
    path("admin/stats", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/leaves/<int:pk>", AdminLeaveDeleteView.as_view(), name="admin-leave-delete"),
]

# The router's URLs are added at the end
urlpatterns += router.urls
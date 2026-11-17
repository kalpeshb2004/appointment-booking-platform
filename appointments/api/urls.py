from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views_auth import LoginView, RegisterView,MeView
from .views_public import (DoctorDetailView, DoctorListView,HospitalDepartmentListView, HospitalListView)

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/me", MeView.as_view(), name="auth-me"),

    path("hospitals", HospitalListView.as_view(), name="hospital-list"),
    path("hospitals/<int:pk>/departments", HospitalDepartmentListView.as_view(),
         name="hospital-departments"),
         # ... auth + hospitals wale purane path same ...
    path("doctors", DoctorListView.as_view(), name="doctor-list"),
    path("doctors/<int:pk>", DoctorDetailView.as_view(), name="doctor-detail"),
]

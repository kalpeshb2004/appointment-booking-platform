from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    """Sirf patient role wala user. Doctor/admin ko 403."""

    message = "Only patients can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "patient")
        )


class IsDoctor(BasePermission):
    """Sirf active doctor role wala user. Patient/admin ko 403."""

    message = "Only doctors can perform this action."

    def has_permission(self, request, view):
        # hasattr: reverse OneToOne, doctor row na ho to False
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "doctor")
            and request.user.doctor.is_active  # deactivated doctor ko access nahi
        )

class IsAdmin(BasePermission):
    """Sirf admin (is_staff). Patient/doctor ko 403."""

    message = "Only admins can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
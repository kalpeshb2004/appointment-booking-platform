from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    """Sirf patient role wala user. Doctor/admin ko 403."""

    message = "Sirf patient ye kaam kar sakta hai."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "patient")
        )


class IsDoctor(BasePermission):
    """Sirf active doctor role wala user. Patient/admin ko 403."""

    message = "Sirf doctor ye kaam kar sakta hai."

    def has_permission(self, request, view):
        # hasattr: reverse OneToOne, doctor row na ho to False
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "doctor")
            and request.user.doctor.is_active  # deactivated doctor ko access nahi
        )
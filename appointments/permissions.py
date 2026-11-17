from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    """Sirf patient role wala user. Doctor/admin ko 403."""

    message = "Sirf patient ye kaam kar sakta hai."

    def has_permission(self, request, view):
        # Token valid + user ke paas patient profile
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "patient")
        )
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsDoctor(BasePermission):
    message = "Access restricted to doctors."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_doctor()
        )


class IsDoctorOwner(BasePermission):
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if not (
            request.user
            and request.user.is_authenticated
            and request.user.is_doctor()
        ):
            return False

        doctor = request.user.doctor_profile

        if hasattr(obj, "doctor"):
            return obj.doctor == doctor

        if hasattr(obj, "assigned_doctor"):
            return obj.assigned_doctor == doctor

        if hasattr(obj, "patient"):
            return obj.patient.doctor == doctor

        return False
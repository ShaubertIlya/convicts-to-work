from rest_framework import permissions

from apps.accounts.models import User


class NonClinicalAuthenticated(permissions.BasePermission):
    """Allow authenticated platform users except medical and psychological reviewers."""

    message = "Раздел недоступен для вашей роли."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role not in {
            User.Role.MEDIC,
            User.Role.PSYCHOLOGIST,
        }

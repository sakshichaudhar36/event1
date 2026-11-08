from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):

    message = "Only superusers can access this API."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )
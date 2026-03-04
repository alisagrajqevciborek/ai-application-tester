"""
Common permissions for the API.
"""
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Allow access only to authenticated admin users with an active status.
    Use this permission class for admin-only endpoints.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
            and request.user.status == 'active'
        )


class IsActiveUser(permissions.BasePermission):
    """
    Allow access only to authenticated users whose account is active (status == 'active').
    Rejects anonymous users and any account that has been disabled.
    """

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.status == 'active'
        )
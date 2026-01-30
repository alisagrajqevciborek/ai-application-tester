"""
Common permissions for the API.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        return obj.owner == request.user


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'admin' and
            request.user.status == 'active'
        )


class IsActiveUser(permissions.BasePermission):
    """
    Permission to check if user is active (not disabled).
    """
    
    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.status == 'active'
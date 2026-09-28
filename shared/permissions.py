from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

def has_permission(provider_user, user):
    if provider_user != user and not user.is_superuser:
        raise PermissionDenied()

class IsSuper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser

class IsVerified(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_verified or request.user.is_superuser

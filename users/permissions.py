from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsAdmin(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.ADMIN
        )


class IsTechnician(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea técnico.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.TECH
        )


class IsClient(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea cliente.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.CLIENT
        )


class IsAdminOrTechnician(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador o técnico.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.TECH]
        )


class IsAdminOrOwner(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador o el propietario del recurso.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == User.Role.ADMIN or 
             request.user.document == view.kwargs.get('pk'))
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea el propietario del recurso o administrador.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == User.Role.ADMIN or 
             obj == request.user)
        )


class IsAuthenticated(permissions.IsAuthenticated):
    """
    Permiso básico de autenticación.
    """
    pass

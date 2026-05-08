from rest_framework import permissions
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission, IsAuthenticated

User = get_user_model()


class IsAdmin(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador.
    Garantiza respuesta 403 si el rol no coincide.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.ADMIN
        )

class IsTechnician(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea técnico.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.TECH
        )

class IsClient(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea cliente.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.CLIENT
        )

class IsAdminOrTechnician(permissions.BasePermission):
    """
    Permiso para administradores o técnicos.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.TECH]
        )

class IsAdminOrClient(permissions.BasePermission):
    """
    Permiso para administradores o clientes.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.CLIENT]
        )

class IsAdminOrTechnicianOrClient(permissions.BasePermission):
    """
    Permiso para cualquier rol autenticado (Admin, Tech o Client).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.TECH, User.Role.CLIENT]
        )

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Verifica que el usuario sea el propietario del recurso o administrador.
    Utilizado usualmente en has_object_permission.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role == User.Role.ADMIN or obj == request.user

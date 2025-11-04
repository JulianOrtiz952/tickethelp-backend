from rest_framework import permissions
from django.contrib.auth import get_user_model
from .models import Ticket

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


class IsAdminOrClient(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador o cliente.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.CLIENT]
        )


class IsTicketOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea el propietario del ticket o administrador.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Administradores pueden acceder a todos los tickets
        if request.user.role == User.Role.ADMIN:
            return True
        
        # El técnico asignado puede acceder al ticket
        if hasattr(obj, 'tecnico') and obj.tecnico == request.user:
            return True
        
        # El cliente propietario puede acceder al ticket
        if hasattr(obj, 'cliente') and obj.cliente == request.user:
            return True
        
        # El administrador que creó el ticket puede acceder
        if hasattr(obj, 'administrador') and obj.administrador == request.user:
            return True
        
        return False


class IsAssignedTechnicianOrAdmin(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea el técnico asignado o administrador.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Administradores pueden acceder
        if request.user.role == User.Role.ADMIN:
            return True
        
        # El técnico asignado puede acceder
        if hasattr(obj, 'tecnico') and obj.tecnico == request.user:
            return True
        
        return False


class IsAuthenticated(permissions.IsAuthenticated):
    """
    Permiso básico de autenticación.
    """
    pass

class IsAdminOrTechnicianOrClient(permissions.BasePermission):
    """
    Permiso personalizado para verificar que el usuario sea administrador, técnico o cliente.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.TECH, User.Role.CLIENT]
        )
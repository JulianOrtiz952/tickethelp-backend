from rest_framework import permissions
from django.contrib.auth import get_user_model
from users.permissions import (
    IsAdmin, IsTechnician, IsClient, 
    IsAdminOrTechnician, IsAdminOrClient, 
    IsAdminOrTechnicianOrClient, IsAuthenticated
)
from .models import Ticket

User = get_user_model()


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


class IsAssignedTechnician(permissions.BasePermission):
    """
    Solo el técnico asignado al ticket.
    """
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.tecnico == request.user)


class IsClientOwner(permissions.BasePermission):
    """
    Solo el cliente propietario del ticket.
    """
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.cliente == request.user)

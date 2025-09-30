# users/views.py
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import (
    UserReadSerializer,
    UserCreateSerializer,
    UserDeleteSerializer,  
    )
User = get_user_model()

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (getattr(user, 'role', None) == 'ADMIN' or user.is_superuser))

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny] # Para probar los endpoints sin autenticación, quitar y colocar IsAdmin en producción

    def get_serializer_class(self):
        return UserCreateSerializer if self.action in ('create', 'update', 'partial_update') else UserReadSerializer

    # Para crear usuarios
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Usuario creado exitosamente"
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    # Para eliminar usuarios
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_active_tickets():
            data = UserDeleteSerializer(instance).data
            return Response({
                "detail": "No se puede eliminar porque tiene tickets activos. Puede desactivarlo.",
                "code": "usuario_con_tickets_activos"
            },
            status=status.HTTP_409_CONFLICT)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if not user.is_active:
            return Response({"detail": "El usuario ya estaba desactivado."}, status=status.HTTP_200_OK)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({"detail": "Usuario desactivado."}, status=status.HTTP_200_OK)
class BaseRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    def get_serializer_class(self):
        return UserCreateSerializer if self.action in ('create', 'update', 'partial_update') else UserReadSerializer
    def get_queryset(self):
        return User.objects.filter(role=self.ROLE)
    def perform_create(self, serializer):
        serializer.save(role=self.ROLE)
    def perform_update(self, serializer):
        serializer.save(role=self.ROLE)
class AdminViewSet(BaseRoleViewSet):
    ROLE = 'ADMIN'
class TechnicianViewSet(BaseRoleViewSet):
    ROLE = 'TECH'
class ClientViewSet(BaseRoleViewSet):
    ROLE = 'CLIENT'
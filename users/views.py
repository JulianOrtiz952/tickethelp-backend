# users/views.py
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import generics
from django.shortcuts import get_object_or_404

from .serializers import (
    UserReadSerializer,
    UserCreateSerializer,
    UserDeleteSerializer,  
    UserUpdateSerializer,
    ChangePasswordSerializer,
    ChangePasswordByIdSerializer
)
User = get_user_model()

# Verifica si quien va hacer la acción es un administrador
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (getattr(user, 'role', None) == 'ADMIN' or user.is_superuser))

# Maneja las vistas para los usuarios
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny] # Para probar los endpoints sin autenticación, quitar y colocar IsAdmin en producción

    def get_serializer_class(self):
        return UserCreateSerializer if self.action in ('create', 'update', 'partial_update') else UserReadSerializer

    # Sirve para crear usuarios
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

    # Sirve para eliminar usuarios
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

    # Sirve para desactivar usuarios en lugar de eliminarlos
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if not user.is_active:
            return Response({"detail": "El usuario ya estaba desactivado."}, status=status.HTTP_200_OK)
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({"detail": "Usuario desactivado."}, status=status.HTTP_200_OK)

# Maneja las vistas para los roles específicos
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

# Vistas para cada rol
class AdminViewSet(BaseRoleViewSet):
    ROLE = 'ADMIN'
class TechnicianViewSet(BaseRoleViewSet):
    ROLE = 'TECH'
class ClientViewSet(BaseRoleViewSet):
    ROLE = 'CLIENT'

class UserUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserUpdateSerializer

    def get_object(self):
        return self.request.user
    
    def patch(self, request, *args, **kwargs):
        resp = super().patch(request, *args, **kwargs)
        if resp.status_code in (200, 202):
            data = dict(resp.data) if isinstance(resp.data, dict) else {}
            data["message"] = "Datos actualizados correctamente."
            return Response(data, status=status.HTTP_200_OK)
        return resp

class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"message": "Contraseña actualizada correctamente, vuelve a iniciar sesión."}, status=status.HTTP_200_OK)
    
class UserUpdateByIdView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.AllowAny]  # <- Habilitado solo para pruebas
    serializer_class = UserUpdateSerializer
    lookup_url_kwarg = 'pk'

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs.get(self.lookup_url_kwarg))

    def patch(self, request, *args, **kwargs):
        resp = super().patch(request, *args, **kwargs)
        if resp.status_code in (200, 202):
            data = dict(resp.data) if isinstance(resp.data, dict) else {}
            data["message"] = "Datos actualizados correctamente."
            return Response(data, status=status.HTTP_200_OK)
        return resp
    
class ChangePasswordByIdView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]  # <- Habilitado solo para pruebas
    serializer_class = ChangePasswordByIdSerializer
    def post(self, request, pk, *args, **kwargs):
        user_obj = get_object_or_404(User, pk=pk)
        ser = self.get_serializer(data=request.data, context={'user': user_obj})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"message": "Contraseña actualizada. Vuelve a iniciar sesión."}, status=status.HTTP_200_OK)
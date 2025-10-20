# users/views.py
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from .serializers import (
    UserReadSerializer,
    UserCreateSerializer,
    UserDeleteSerializer,  
    UserUpdateSerializer,
    UserDeactivateSerializer,
    AdminUpdateUserSerializer,
    UserUpdateProfilePictureSerializer,
    ChangePasswordSerializer,
    ChangePasswordByIdSerializer,
    EmailTokenObtainPairSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
User = get_user_model()

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (getattr(user, 'role', None) == 'ADMIN' or user.is_superuser))

# Maneja las vistas para los usuarios
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'update':
            return UserUpdateSerializer
        elif self.action == 'deactivate':
            return UserDeactivateSerializer
        return UserReadSerializer

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
        
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Usuario actualizado exitosamente"
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_data = UserReadSerializer(instance).data
        if instance.has_active_tickets():
            data = UserDeleteSerializer(instance).data
            return Response({
                "detail": "No se puede eliminar porque tiene tickets activos. Puede desactivarlo.",
                "code": "usuario_con_tickets_activos",
                "User data:": user_data
            },
            status=status.HTTP_409_CONFLICT)
        self.perform_destroy(instance)
        return Response({
            "Message": "Usuario eliminado correctamente"
                },status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        try:
            # Busca al usuario por su documento
            user = self.get_object()  # Obtiene el usuario con pk
            
            if not user.is_active:
                return Response({"detail": "El usuario ya estaba desactivado."}, status=status.HTTP_200_OK)

            # Desactiva al usuario
            user.is_active = False
            user.save(update_fields=['is_active'])

            return Response({
                "detail": "Usuario desactivado.",
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        if user.is_active:
            return Response({"detail": "El usuario ya estaba activado."}, status=status.HTTP_200_OK)
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({"detail": "Usuario activado."}, status=status.HTTP_200_OK)

# Maneja las vistas para los roles específicos
class BaseRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.AllowAny] # Solo para pruebas, luego cambiar a IsAdmin
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

class UserUpdateProfilePictureView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.AllowAny] # <- Habilitado solo para pruebas, luego cambiar a IsAuthenticated
    serializer_class = UserUpdateProfilePictureSerializer

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs.get('pk'))
    
    def patch(self, request, *args, **kwargs):
        resp = super().patch(request, *args, **kwargs)
    
        if resp.status_code in (200, 202):
            data = dict(resp.data) if isinstance(resp.data, dict) else {}
            data["message"] = "Foto de perfil actualizada correctamente."
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
    
# Función para consultar cliente por documento con manejo de error personalizado
@api_view(['GET'])
@permission_classes([permissions.AllowAny])  # Cambiar por IsAdmin en producción
def get_client_by_document(request, document):
    """
    Consulta un cliente por su número de documento.
    Si no existe, retorna un mensaje específico indicando que debe ser creado.
    """
    try:
        # Intentar buscar el cliente por documento
        client = User.objects.get(document=document, role=User.Role.CLIENT)
        
        serializer = UserReadSerializer(client)
        return Response({
            "success": True,
            "message": "Cliente encontrado exitosamente",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            "success": False,
            "message": f"El cliente con documento {document} no existe en el sistema",
            "suggestion": "Debe crear el cliente antes de continuar",
            "code": "CLIENT_NOT_FOUND",
            "data": None
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        # Manejo de otros errores inesperados
        return Response({
            "success": False,
            "message": "Error interno del servidor",
            "error": str(e),
            "code": "INTERNAL_ERROR"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ================ Admin ================
class AdminUpdateUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.AllowAny] # <- Habilitado solo para pruebas, luego cambiar a IsAdmin
    serializer_class = AdminUpdateUserSerializer

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs.get('pk'))
    
    def patch(self, request, *args, **kwargs):
        resp = super().patch(request, *args, **kwargs)
        if resp.status_code in (200, 202):
            data = dict(resp.data) if isinstance(resp.data, dict) else {}
            data["message"] = "Datos actualizados correctamente."
            return Response(data, status=status.HTTP_200_OK)
        return resp


# =============================================================================
# HU14A - Login: Vista personalizada para autenticación JWT
# =============================================================================
# Esta vista extiende TokenObtainPairView para manejar la autenticación
# con email como username y implementar validaciones específicas de la HU14A
# =============================================================================

class EmailTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para autenticación JWT con email como username.
    
    Implementa los escenarios de la HU14A - Login:
    - Escenario 1: Inicio de sesión exitoso ✅
    - Escenario 2: Autenticación por rol ✅  
    - Escenario 5: Credenciales incorrectas ✖️
    - Escenario 6: Usuario no registrado ✖️
    - Escenario 7: Usuario inactivo ✖️
    - Escenario 12: Contraseña por defecto ✖️
    
    Endpoint: POST /api/auth/login/
    Body: {"email": "usuario@ejemplo.com", "password": "contraseña"}
    
    Respuestas:
    - 200: Login exitoso con token JWT y datos del usuario
    - 401: Credenciales inválidas, usuario inactivo o debe cambiar contraseña
    - 400: Datos de entrada inválidos
    """
    serializer_class = EmailTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """
        Maneja las solicitudes de login con validaciones de la HU14A.
        
        Args:
            request: Request con email y password
            
        Returns:
            Response: Token JWT con datos del usuario o error específico
            
        Escenarios implementados:
        - Escenario 1: Retorna token y datos del usuario para redirección
        - Escenario 2: Incluye rol en la respuesta para redirección automática
        - Escenario 5/6: Retorna 401 con mensaje "Credenciales inválidas"
        - Escenario 7: Retorna 401 con mensaje "Cuenta inactiva"
        - Escenario 12: Retorna 401 con mensaje "Por favor, cambie la contraseña"
        """
        return super().post(request, *args, **kwargs)

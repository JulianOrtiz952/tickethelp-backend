from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AdminViewSet, TechnicianViewSet, ClientViewSet, UserUpdateView, ChangePasswordView, ChangePasswordByIdView, UserUpdateByIdView, get_client_by_document, AdminUpdateUserView, UserUpdateProfilePictureView, EmailTokenObtainPairView, TokenValidationView, TokenUserDataView
from django.urls import path, include
urlpatterns = [
    # Listar usuarios
    path('users/', UserViewSet.as_view({'get': 'list'}), name='user-list'),
    # Crear usuarios
    path('users/create/', UserViewSet.as_view({'post': 'create'}), name='user-create'),
    # Obtener información del usuario
    path('users/<str:pk>/', UserViewSet.as_view({'get': 'retrieve'}), name='user-detail'),
    # Actualizar información del usuario siendo administrador
    path('users/update-user/<str:pk>/', AdminUpdateUserView.as_view(), name='admin-update-user'),
    # Eliminar el usuario por el admin
    path('users/delete/<str:pk>', UserViewSet.as_view({'delete': 'destroy'}), name='user-delete'),
    # Desactivar usuario en caso de que no se pueda eliminar
    path('users/deactivate/<str:pk>', UserViewSet.as_view({'post': 'deactivate'}), name='user-deactivate'),
    # Activar usuario de nuevo
    path('users/activate/<str:pk>/', UserViewSet.as_view({'post': 'activate'}), name='user-activate'),
    # Actualizar foto de perfil del usuario
    path('users/update-profile-picture/<str:pk>/', UserUpdateProfilePictureView.as_view(), name='user-update-profile-picture'),
    
    # Listar admins
    path('admins/', AdminViewSet.as_view({'get': 'list'}), name='admin-list'),
    # Obtener información de un administrador
    path('admins/<str:pk>/', AdminViewSet.as_view({'get': 'retrieve'}), name='admin-detail'),
    
    # Listar technicians
    path('technicians/', TechnicianViewSet.as_view({'get': 'list'}), name='technician-list'),
    # Obtener información de un técnico
    path('technicians/<str:pk>/', TechnicianViewSet.as_view({'get': 'retrieve'}), name='technician-detail'),
    
    # Listar clients
    path('clients/', ClientViewSet.as_view({'get': 'list'}), name='client-list'),
    # Obtener cliente por documento
    path('clients/<str:document>/', get_client_by_document, name='get-client-by-document'),

    #HU03B - actualizar perfil de usuario
    path('me/', UserUpdateView.as_view(), name='users-me'), # Endpoint para que el usuario autenticado actualice su perfil
    path('me/change-password/', ChangePasswordView.as_view(), name='users-change-password'),
    
    #Endpoint para las pruebas
    path('me/<int:pk>/', UserUpdateByIdView.as_view(), name='users-me-by-id'),
    path('me/change-password/<int:pk>/', ChangePasswordByIdView.as_view(), name='users-change-password-by-id'),
    
    # =============================================================================
    # HU14A - Login: Endpoint de autenticación JWT personalizado
    # =============================================================================
    # Endpoint para autenticación con email como username
    # Implementa los escenarios de la HU14A - Login
    # =============================================================================
    path('users/auth/login/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair_email'), # HU14A - Login con email
    
    # =============================================================================
    # HU14A - Login: Endpoint para cambio de contraseña con validaciones
    # =============================================================================
    # Endpoint para cambio de contraseña con validaciones específicas
    # Implementa los escenarios 4 y 13-18 de la HU14A - Login
    # =============================================================================
    path('users/auth/change-password/', ChangePasswordView.as_view(), name='change_password'), # HU14A - Cambio de contraseña
    
    # =============================================================================
    # HU14A - Login: Métodos adicionales para manejo de tokens
    # =============================================================================
    # Endpoints adicionales requeridos para la HU14A - Login:
    # - Método 1: Obtener datos del usuario desde el token
    # - Método 2: Validar si el token está activo
    # =============================================================================
    path('users/auth/validate-token/', TokenValidationView.as_view(), name='token_validation'), # HU14A - Validar token activo
    path('users/auth/user-data/', TokenUserDataView.as_view(), name='token_user_data'), # HU14A - Obtener datos del usuario desde token
]
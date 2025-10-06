from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AdminViewSet, TechnicianViewSet, ClientViewSet, UserUpdateView, ChangePasswordView, ChangePasswordByIdView, UserUpdateByIdView, AdminUpdateUserView
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
    path('admin/delete/<str:pk>', UserViewSet.as_view({'delete': 'destroy'}), name='user-delete'),
    # Desactivar usuario en caso de que no se pueda eliminar
    path('users/<str:pk>/deactivate/', UserViewSet.as_view({'post': 'deactivate'}), name='user-deactivate'),
    # Activar usuario de nuevo
    path('users/<str:pk>/activate/', UserViewSet.as_view({'post': 'activate'}), name='user-activate'),
    
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
    # Obtener información de un cliente
    path('clients/<str:pk>/', ClientViewSet.as_view({'get': 'retrieve'}), name='client-detail'),

    #HU03B - actualizar perfil de usuario
    path('me/', UserUpdateView.as_view(), name='users-me'), # Endpoint para que el usuario autenticado actualice su perfil
    path('me/change-password/', ChangePasswordView.as_view(), name='users-change-password'),
     
     #Endpoint para las pruebas
    path('me/<int:pk>/', UserUpdateByIdView.as_view(), name='users-me-by-id'),
    path('me/change-password/<int:pk>/', ChangePasswordByIdView.as_view(), name='users-change-password-by-id'),
]
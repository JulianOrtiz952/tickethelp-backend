from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AdminViewSet, TechnicianViewSet, ClientViewSet, UserUpdateView, ChangePasswordView, ChangePasswordByIdView, UserUpdateByIdView
from django.urls import path, include

router = DefaultRouter()
# Mapeo de rutas generales
router.register('/users', UserViewSet, basename='user')
router.register('/admins', AdminViewSet, basename='admin')
router.register('/technicians', TechnicianViewSet, basename='technician')
router.register('/clients', ClientViewSet, basename='client')

urlpatterns = [
    path('', include(router.urls)),

    #HU03B - actualizar perfil de usuario
    path('me/', UserUpdateView.as_view(), name='users-me'), # Endpoint para que el usuario autenticado actualice su perfil
    path('me/change-password/', ChangePasswordView.as_view(), name='users-change-password'),
     
     #Endpoint para las pruebas
    path('me/<int:pk>/', UserUpdateByIdView.as_view(), name='users-me-by-id'),
    path('me/change-password/<int:pk>/', ChangePasswordByIdView.as_view(), name='users-change-password-by-id'),

]
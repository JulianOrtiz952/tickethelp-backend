from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Lista de notificaciones del usuario autenticado
    path('', views.notification_list, name='notification-list'),
    
    # Detalle de notificación específica
    path('<int:notification_id>/', views.notification_detail, name='notification-detail'),
    
    # Estadísticas del usuario autenticado
    path('stats/', views.notification_stats, name='notification-stats'),
    
    # Tipos de notificaciones disponibles
    path('types/', views.notification_types, name='notification-types'),
    
    # Historial de notificaciones de usuario
    path('user-notifications/', views.UserNotificationsAV.as_view(), name='user-notifications'),
    
    # Marcar notificación como leída
    path('<int:notification_id>/mark-read/', views.NotificationMarkAsReadAV.as_view(), name='notification-mark-read'),
    
    # Notificaciones específicas para clientes
    path('client/', views.ClientNotificationsAV.as_view(), name='client-notifications'),
]
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Lista de notificaciones
    path('', views.notification_list, name='notification-list'),
    
    # Detalle de notificación
    path('<int:notification_id>/', views.notification_detail, name='notification-detail'),
    
    # Marcar notificaciones como leídas
    path('mark-as-read/', views.mark_notifications_as_read, name='mark-as-read'),
    path('mark-all-as-read/', views.mark_all_as_read, name='mark-all-as-read'),
    
    # Estadísticas
    path('stats/', views.notification_stats, name='notification-stats'),
    
    # Tipos de notificaciones
    path('types/', views.notification_types, name='notification-types'),
    
    # Eliminar notificación
    path('<int:notification_id>/delete/', views.delete_notification, name='delete-notification'),
]


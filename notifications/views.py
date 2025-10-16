from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from .models import Notification, NotificationType
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationStatsSerializer, NotificationTypeSerializer
)

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """
    Lista las notificaciones del usuario autenticado.
    Cumple con criterio 8: Usuario autenticado accede a su historial.
    """
    user = request.user
    
    # Filtros básicos
    queryset = Notification.objects.filter(usuario=user).select_related(
        'tipo', 'ticket'
    ).order_by('-fecha_creacion')
    
    # Filtros opcionales
    estado = request.query_params.get('estado')
    if estado:
        queryset = queryset.filter(estado=estado)
    
    tipo = request.query_params.get('tipo')
    if tipo:
        queryset = queryset.filter(tipo__codigo=tipo)
    
    leidas = request.query_params.get('leidas')
    if leidas is not None:
        if leidas.lower() == 'true':
            queryset = queryset.filter(estado=Notification.Estado.LEIDA)
        elif leidas.lower() == 'false':
            queryset = queryset.exclude(estado=Notification.Estado.LEIDA)
    
    # Paginación
    limit = min(int(request.query_params.get('limit', 20)), 100)
    offset = int(request.query_params.get('offset', 0))
    
    total_count = queryset.count()
    notifications = queryset[offset:offset + limit]
    
    serializer = NotificationListSerializer(notifications, many=True)
    
    return Response({
        'notifications': serializer.data,
        'total': total_count,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total_count
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):
    """
    Obtiene los detalles de una notificación específica.
    Automáticamente marca la notificación como leída si no lo está.
    """
    user = request.user
    
    notification = get_object_or_404(
        Notification.objects.select_related('tipo', 'ticket', 'usuario'),
        id=notification_id,
        usuario=user  # Solo puede ver sus propias notificaciones
    )
    
    # Marcar como leída si no lo está
    if not notification.es_leida:
        notification.marcar_como_leida()
    
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """
    Obtiene estadísticas de las notificaciones del usuario autenticado.
    """
    user = request.user
    
    stats = Notification.objects.filter(usuario=user).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado=Notification.Estado.PENDIENTE)),
        enviadas=Count('id', filter=Q(estado=Notification.Estado.ENVIADA)),
        leidas=Count('id', filter=Q(estado=Notification.Estado.LEIDA)),
        fallidas=Count('id', filter=Q(estado=Notification.Estado.FALLIDA))
    )
    
    stats['no_leidas'] = stats['pendientes'] + stats['enviadas']
    
    serializer = NotificationStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_types(request):
    """Lista los tipos de notificaciones disponibles."""
    types = NotificationType.objects.filter(es_activo=True).order_by('nombre')
    serializer = NotificationTypeSerializer(types, many=True)
    return Response(serializer.data)
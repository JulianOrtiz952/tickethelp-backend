from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone

from .models import Notification, NotificationType
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationMarkAsReadSerializer, NotificationStatsSerializer,
    NotificationTypeSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """
    Lista las notificaciones del usuario autenticado.
    
    Query parameters:
    - estado: Filtrar por estado (PENDIENTE, ENVIADA, LEIDA, FALLIDA)
    - tipo: Filtrar por tipo de notificación
    - leidas: true/false para filtrar por estado de lectura
    - limit: Número de notificaciones a retornar (default: 20)
    - offset: Número de notificaciones a saltar (default: 0)
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
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    # Limitar el límite máximo
    limit = min(limit, 100)
    
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
        usuario=user
    )
    
    # Marcar como leída si no lo está
    if not notification.es_leida:
        notification.marcar_como_leida()
    
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notifications_as_read(request):
    """
    Marca múltiples notificaciones como leídas.
    """
    user = request.user
    serializer = NotificationMarkAsReadSerializer(data=request.data)
    
    if serializer.is_valid():
        notification_ids = serializer.validated_data['notification_ids']
        
        # Verificar que todas las notificaciones pertenezcan al usuario
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            usuario=user
        )
        
        if notifications.count() != len(notification_ids):
            return Response(
                {'error': 'No tienes permiso para acceder a algunas de estas notificaciones.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Marcar como leídas
        updated_count = notifications.filter(
            estado__in=[Notification.Estado.PENDIENTE, Notification.Estado.ENVIADA]
        ).update(
            estado=Notification.Estado.LEIDA,
            fecha_lectura=timezone.now()
        )
        
        return Response({
            'message': f'{updated_count} notificaciones marcadas como leídas.',
            'updated_count': updated_count
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """
    Obtiene estadísticas de las notificaciones del usuario.
    """
    user = request.user
    
    stats = Notification.objects.filter(usuario=user).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado=Notification.Estado.PENDIENTE)),
        enviadas=Count('id', filter=Q(estado=Notification.Estado.ENVIADA)),
        leidas=Count('id', filter=Q(estado=Notification.Estado.LEIDA)),
        fallidas=Count('id', filter=Q(estado=Notification.Estado.FALLIDA))
    )
    
    # Calcular no leídas (pendientes + enviadas)
    stats['no_leidas'] = stats['pendientes'] + stats['enviadas']
    
    serializer = NotificationStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_types(request):
    """
    Lista los tipos de notificaciones disponibles.
    """
    types = NotificationType.objects.filter(es_activo=True).order_by('nombre')
    serializer = NotificationTypeSerializer(types, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """
    Marca todas las notificaciones del usuario como leídas.
    """
    user = request.user
    
    updated_count = Notification.objects.filter(
        usuario=user,
        estado__in=[Notification.Estado.PENDIENTE, Notification.Estado.ENVIADA]
    ).update(
        estado=Notification.Estado.LEIDA,
        fecha_lectura=timezone.now()
    )
    
    return Response({
        'message': f'{updated_count} notificaciones marcadas como leídas.',
        'updated_count': updated_count
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """
    Elimina una notificación específica.
    """
    user = request.user
    
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        usuario=user
    )
    
    notification.delete()
    
    return Response({
        'message': 'Notificación eliminada exitosamente.'
    }, status=status.HTTP_204_NO_CONTENT)
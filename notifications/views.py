from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, UpdateAPIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Notification, NotificationType
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationStatsSerializer, NotificationTypeSerializer, NotificationUpdateSerializer
)

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    user = request.user

    # Solo mostrar notificaciones donde el usuario es el destinatario principal
    queryset = Notification.objects.filter(usuario=user).select_related('tipo', 'ticket', 'enviado_por').order_by('-fecha_creacion')

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

    limit = min(int(request.query_params.get('limit', 20)), 100)
    offset = int(request.query_params.get('offset', 0))

    notifications = queryset[offset:offset + limit]
    serializer = NotificationListSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):
    notification = get_object_or_404(
        Notification.objects.select_related('tipo', 'ticket', 'usuario', 'enviado_por'),
        id=notification_id
    )

    user = request.user
    # Permitir acceso si es el dueño, destinatario o administrador
    allowed = (
        getattr(user, 'role', None) == getattr(User.Role, 'ADMIN', 'ADMIN') or
        notification.usuario == user or
        notification.enviado_por == user or
        notification.destinatarios.filter(pk=user.pk).exists()
    )

    if not allowed:
        return Response({"detail": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)

    try:
        is_recipient = (request.user and request.user.is_authenticated and notification.usuario == request.user)
    except Exception:
        is_recipient = (user is not None and notification.usuario == user)

    if is_recipient and not notification.es_leida:
        notification.marcar_como_leida()

    serializer = NotificationSerializer(notification)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    user = request.user
    # Solo contar notificaciones donde el usuario es el destinatario principal
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
    types = NotificationType.objects.filter(es_activo=True).order_by('nombre')
    serializer = NotificationTypeSerializer(types, many=True)
    return Response(serializer.data)


class UserNotificationsAV(ListAPIView):
    """Endpoint para obtener el historial de notificaciones del usuario autenticado."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(
            Q(usuario=user) | Q(destinatarios=user)
        ).select_related('tipo', 'ticket', 'enviado_por').order_by('-fecha_creacion').distinct()
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Aplicar filtros opcionales
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
        
        notifications = queryset[offset:offset + limit]
        serializer = self.get_serializer(notifications, many=True)
        
        return Response({
            'message': 'Historial de notificaciones',
            'total_notifications': queryset.count(),
            'notifications': serializer.data
        }, status=status.HTTP_200_OK)


class NotificationMarkAsReadAV(UpdateAPIView):
    """Endpoint para marcar notificaciones como leídas."""
    serializer_class = NotificationUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        notification_id = self.kwargs.get('notification_id')
        user = self.request.user
        
        # Buscar notificación que pertenezca al usuario
        return get_object_or_404(
            Notification.objects.filter(usuario=user),
            pk=notification_id
        )
    
    def put(self, request, *args, **kwargs):
        notification = self.get_object()
        serializer = self.get_serializer(notification, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Notificación marcada como leída',
                'notification_id': notification.id,
                'estado': notification.estado
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
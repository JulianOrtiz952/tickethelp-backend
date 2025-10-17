from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Notification, NotificationType
from .serializers import (
    NotificationSerializer, NotificationListSerializer,
    NotificationStatsSerializer, NotificationTypeSerializer
)

User = get_user_model()


@api_view(['GET'])
@permission_classes([AllowAny])
def notification_list(request):
    if request.user and request.user.is_authenticated:
        user = request.user
    else:
        user_document = request.query_params.get('user_document')
        user_id = request.query_params.get('user_id')
        if user_document:
            user = get_object_or_404(User, document=user_document)
        elif user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            return Response({"detail": "No autenticado."}, status=status.HTTP_400_BAD_REQUEST)

    queryset = Notification.objects.filter(
        Q(usuario=user) | Q(destinatarios=user)
    ).select_related('tipo', 'ticket', 'enviado_por').order_by('-fecha_creacion').distinct()

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
@permission_classes([AllowAny])
def notification_detail(request, notification_id):
    notification = get_object_or_404(
        Notification.objects.select_related('tipo', 'ticket', 'usuario', 'enviado_por'),
        id=notification_id
    )

    if request.user and request.user.is_authenticated:
        user = request.user
        allowed = request.user.is_staff or notification.usuario == request.user or notification.enviado_por == request.user
    else:
        user_document = request.query_params.get('user_document')
        user_id = request.query_params.get('user_id')
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
            allowed = (notification.usuario == user)
        elif user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
            allowed = (notification.usuario == user)
        else:
            force = request.query_params.get('force')
            if settings.DEBUG and force and force.lower() == 'true':
                allowed = True
            else:
                return Response({"detail": "No autorizado."}, status=status.HTTP_400_BAD_REQUEST)

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
@permission_classes([AllowAny])
def notification_stats(request):
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
    types = NotificationType.objects.filter(es_activo=True).order_by('nombre')
    serializer = NotificationTypeSerializer(types, many=True)
    return Response(serializer.data)
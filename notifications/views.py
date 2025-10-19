from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
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


class UserNotificationsAV(ListAPIView):
    """Endpoint para obtener el historial de notificaciones de un usuario específico."""
    serializer_class = NotificationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        user_document = self.request.query_params.get('user_document')
        user_id = self.request.query_params.get('user_id')
        
        # Obtener usuario por documento o ID
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Notification.objects.none()
        elif user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Notification.objects.none()
        else:
            if self.request.user and self.request.user.is_authenticated:
                user = self.request.user
            else:
                return Notification.objects.none()
        
        # Filtrar notificaciones del usuario
        return Notification.objects.filter(
            Q(usuario=user) | Q(destinatarios=user)
        ).select_related('tipo', 'ticket', 'enviado_por').order_by('-fecha_creacion').distinct()
    
    def list(self, request, *args, **kwargs):
        # Validar que se proporcione un usuario
        user_document = request.query_params.get('user_document')
        user_id = request.query_params.get('user_id')
        
        if not user_document and not user_id and not (request.user and request.user.is_authenticated):
            return Response({
                'error': 'No tiene acceso',
                'message': 'Debe proporcionar user_document o user_id como parámetro de consulta'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar que el usuario existe
        try:
            if user_document:
                user = User.objects.get(document=user_document)
            elif user_id:
                user = User.objects.get(id=user_id)
            else:
                user = request.user
        except User.DoesNotExist:
            return Response({
                'error': 'No tiene acceso',
                'message': 'El usuario especificado no existe'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user and request.user.is_authenticated:
            if request.user != user and not request.user.is_staff:
                return Response({
                    'error': 'No tienes permiso para acceder',
                    'message': 'Solo puedes ver tus propias notificaciones'
                }, status=status.HTTP_403_FORBIDDEN)
        
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
    permission_classes = [AllowAny]
    
    def get_object(self):
        notification_id = self.kwargs.get('notification_id')
        user_document = self.request.query_params.get('user_document')
        user_id = self.request.query_params.get('user_id')
        
        # Obtener usuario
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return None
        elif user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return None
        else:
            user = getattr(self.request, 'user', None)
            if not user or not user.is_authenticated:
                return None
        
        # Buscar notificación que pertenezca al usuario
        return get_object_or_404(
            Notification.objects.filter(
                Q(usuario=user) | Q(destinatarios=user)
            ),
            pk=notification_id
        )
    
    def put(self, request, *args, **kwargs):
        notification = self.get_object()
        
        if not notification:
            return Response({
                'error': 'No tiene acceso',
                'message': 'Debe proporcionar user_document o user_id como parámetro de consulta'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(notification, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Notificación marcada como leída',
                'notification_id': notification.id,
                'estado': notification.estado
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
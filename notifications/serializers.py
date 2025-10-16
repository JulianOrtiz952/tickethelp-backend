from rest_framework import serializers
from .models import Notification, NotificationType
from users.models import User
from tickets.models import Ticket


class NotificationTypeSerializer(serializers.ModelSerializer):
    """Serializer para tipos de notificaciones."""
    
    class Meta:
        model = NotificationType
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'es_activo',
            'enviar_a_cliente', 'enviar_a_tecnico', 'enviar_a_admin'
        ]
        read_only_fields = ['id', 'codigo']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones."""
    
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    ticket_titulo = serializers.CharField(source='ticket.titulo', read_only=True)
    ticket_id = serializers.IntegerField(source='ticket.id', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'titulo', 'mensaje', 'estado', 'fecha_creacion',
            'fecha_envio', 'fecha_lectura', 'datos_adicionales',
            'tipo_nombre', 'tipo_codigo', 'usuario_email',
            'ticket_titulo', 'ticket_id'
        ]
        read_only_fields = [
            'id', 'fecha_creacion', 'fecha_envio', 'fecha_lectura',
            'tipo_nombre', 'tipo_codigo', 'usuario_email',
            'ticket_titulo', 'ticket_id'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar notificaciones."""
    
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    ticket_titulo = serializers.CharField(source='ticket.titulo', read_only=True)
    es_leida = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'titulo', 'estado', 'fecha_creacion', 'fecha_lectura',
            'tipo_nombre', 'ticket_titulo', 'es_leida'
        ]


class NotificationMarkAsReadSerializer(serializers.Serializer):
    """Serializer para marcar notificaciones como leídas."""
    
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista de IDs de notificaciones a marcar como leídas"
    )
    
    def validate_notification_ids(self, value):
        """Valida que los IDs de notificaciones existan y pertenezcan al usuario."""
        if not value:
            raise serializers.ValidationError("La lista no puede estar vacía.")
        
        # Verificar que todas las notificaciones existan
        existing_ids = Notification.objects.filter(
            id__in=value
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Las notificaciones con IDs {list(missing_ids)} no existen."
            )
        
        return value


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de notificaciones."""
    
    total = serializers.IntegerField()
    pendientes = serializers.IntegerField()
    enviadas = serializers.IntegerField()
    leidas = serializers.IntegerField()
    fallidas = serializers.IntegerField()
    no_leidas = serializers.IntegerField()


from rest_framework import serializers
from .models import Notification, NotificationType


class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'es_activo']


class NotificationSerializer(serializers.ModelSerializer):
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


class NotificationListSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    ticket_titulo = serializers.CharField(source='ticket.titulo', read_only=True)
    es_leida = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'titulo', 'estado', 'fecha_creacion', 'fecha_lectura',
            'tipo_nombre', 'ticket_titulo', 'es_leida'
        ]


class NotificationStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pendientes = serializers.IntegerField()
    enviadas = serializers.IntegerField()
    leidas = serializers.IntegerField()
    fallidas = serializers.IntegerField()
    no_leidas = serializers.IntegerField()


class CreateNotificationSerializer(serializers.ModelSerializer):
    """Serializer para crear notificaciones manualmente."""
    user_document = serializers.CharField(write_only=True, help_text="Documento del usuario destinatario")
    ticket_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID del ticket relacionado")
    tipo_codigo = serializers.CharField(help_text="Código del tipo de notificación")
    
    class Meta:
        model = Notification
        fields = [
            'user_document', 'ticket_id', 'tipo_codigo', 
            'titulo', 'mensaje', 'datos_adicionales'
        ]
    
    def validate_user_document(self, value):
        """Valida que el documento del usuario exista."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            User.objects.get(document=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")
        return value
    
    def validate_tipo_codigo(self, value):
        """Valida que el tipo de notificación exista."""
        try:
            NotificationType.objects.get(codigo=value, es_activo=True)
        except NotificationType.DoesNotExist:
            raise serializers.ValidationError("Tipo de notificación no encontrado o inactivo")
        return value
    
    def validate_ticket_id(self, value):
        """Valida que el ticket exista si se proporciona."""
        if value is not None:
            from tickets.models import Ticket
            try:
                Ticket.objects.get(id=value)
            except Ticket.DoesNotExist:
                raise serializers.ValidationError("Ticket no encontrado")
        return value
    
    def create(self, validated_data):
        """Crea la notificación."""
        from django.contrib.auth import get_user_model
        from tickets.models import Ticket
        from django.utils import timezone
        
        User = get_user_model()
        
        # Obtener usuario
        user = User.objects.get(document=validated_data['user_document'])
        
        # Obtener tipo de notificación
        tipo = NotificationType.objects.get(codigo=validated_data['tipo_codigo'])
        
        # Obtener ticket si se proporciona
        ticket = None
        if validated_data.get('ticket_id'):
            ticket = Ticket.objects.get(id=validated_data['ticket_id'])
        
        # Crear notificación
        notification = Notification.objects.create(
            usuario=user,
            ticket=ticket,
            tipo=tipo,
            titulo=validated_data['titulo'],
            mensaje=validated_data['mensaje'],
            datos_adicionales=validated_data.get('datos_adicionales', {}),
            estado=Notification.Estado.ENVIADA,
            fecha_envio=timezone.now()
        )
        
        return notification
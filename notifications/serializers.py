from rest_framework import serializers
from .models import Notification, NotificationType


class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'es_activo']


class NotificationSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    mensaje = serializers.SerializerMethodField(read_only=True)
    # Nested recipient and sender objects
    usuario = serializers.SerializerMethodField(read_only=True)
    enviado_por = serializers.SerializerMethodField(read_only=True)
    
    destinatarios = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'mensaje', 'estado', 'fecha_creacion',
            'fecha_envio',
            'tipo_nombre', 'tipo_codigo', 'usuario', 'enviado_por', 'destinatarios'
        ]

    def get_usuario(self, obj):
        u = getattr(obj, 'usuario', None)
        if not u:
            return None
        return {
            'email': getattr(u, 'email', None),
            'first_name': getattr(u, 'first_name', ''),
            'last_name': getattr(u, 'last_name', ''),
            'role': getattr(u, 'role', '')
        }

    def get_enviado_por(self, obj):
        s = getattr(obj, 'enviado_por', None)
        if not s:
            return None
        return {
            'email': getattr(s, 'email', None),
            'first_name': getattr(s, 'first_name', ''),
            'last_name': getattr(s, 'last_name', ''),
            'role': getattr(obj, 'enviado_por_role', '') or getattr(s, 'role', '')
        }

    def get_mensaje(self, obj):
        # Usa el mensaje específico de la notificación si existe, sino la descripción del tipo
        if getattr(obj, 'mensaje', None):
            return obj.mensaje
        return getattr(obj.tipo, 'descripcion', '')

    def get_destinatarios(self, obj):
        users = obj.destinatarios.all()
        return [
            {
                'email': getattr(u, 'email', None),
                'first_name': getattr(u, 'first_name', ''),
                'last_name': getattr(u, 'last_name', ''),
                'role': getattr(u, 'role', '')
            }
            for u in users
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    mensaje = serializers.SerializerMethodField(read_only=True)
    enviado_por = serializers.SerializerMethodField(read_only=True)
    usuario = serializers.SerializerMethodField(read_only=True)
    
    destinatarios = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'mensaje', 'estado', 'fecha_creacion',
            'tipo_nombre', 'tipo_codigo', 'enviado_por', 'usuario', 'destinatarios'
        ]

    def get_enviado_por(self, obj):
        s = getattr(obj, 'enviado_por', None)
        if not s:
            return None
        return {
            'email': getattr(s, 'email', None),
            'first_name': getattr(s, 'first_name', ''),
            'last_name': getattr(s, 'last_name', ''),
            'role': getattr(obj, 'enviado_por_role', '') or getattr(s, 'role', '')
        }

    def get_usuario(self, obj):
        u = getattr(obj, 'usuario', None)
        if not u:
            return None
        return {
            'email': getattr(u, 'email', None),
            'first_name': getattr(u, 'first_name', ''),
            'last_name': getattr(u, 'last_name', ''),
            'role': getattr(u, 'role', '')
        }

    def get_mensaje(self, obj):
        if getattr(obj, 'mensaje', None):
            return obj.mensaje
        return getattr(obj.tipo, 'descripcion', '')

    def get_destinatarios(self, obj):
        users = obj.destinatarios.all()
        return [
            {
                'email': getattr(u, 'email', None),
                'first_name': getattr(u, 'first_name', ''),
                'last_name': getattr(u, 'last_name', ''),
                'role': getattr(u, 'role', '')
            }
            for u in users
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
    # Ahora aceptamos una lista de documentos para múltiples destinatarios
    user_documents = serializers.ListField(
        child=serializers.CharField(), write_only=True, help_text="Lista de documentos de los usuarios destinatarios"
    )
    ticket_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID del ticket relacionado")
    tipo_codigo = serializers.CharField(help_text="Código del tipo de notificación")
    
    class Meta:
        model = Notification
        fields = [
            'user_documents', 'ticket_id', 'tipo_codigo', 
            'titulo', 'mensaje', 'descripcion'
        ]
    
    def validate_user_documents(self, value):
        """Valida que los documentos de los destinatarios existan y retorna los usuarios."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = []
        for doc in value:
            try:
                users.append(User.objects.get(document=doc))
            except User.DoesNotExist:
                raise serializers.ValidationError(f"Usuario no encontrado: {doc}")
        return users
    
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
        # Obtener destinatarios (validate_user_documents devuelve lista de User)
        destinatarios = validated_data.pop('user_documents', [])

        # Obtener tipo de notificación
        tipo = NotificationType.objects.get(codigo=validated_data['tipo_codigo'])

        # Obtener ticket si se proporciona
        ticket = None
        if validated_data.get('ticket_id'):
            ticket = Ticket.objects.get(id=validated_data['ticket_id'])

        # Verificar que el emisor viene en el contexto y tiene rol permitido
        request = self.context.get('request')
        enviado_por = None
        enviado_por_role = ''
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            enviado_por = request.user
            enviado_por_role = getattr(request.user, 'role', '')
            if enviado_por_role not in ('TECH', 'ADMIN'):
                raise serializers.ValidationError('Solo técnicos o administradores pueden enviar notificaciones')
        else:
            raise serializers.ValidationError('Se requiere autenticación del emisor')

        # Crear notificación (usuario campo se mantiene por compatibilidad, usamos el primero si existe)
        primary_user = destinatarios[0] if destinatarios else None
        notification = Notification.objects.create(
            usuario=primary_user,
            ticket=ticket,
            tipo=tipo,
            titulo=validated_data.get('titulo', ''),
            mensaje=validated_data.get('mensaje', ''),
            descripcion=validated_data.get('descripcion', ''),
            datos_adicionales={},
            estado=Notification.Estado.ENVIADA,
            fecha_envio=timezone.now(),
            enviado_por=enviado_por,
            enviado_por_role=enviado_por_role
        )

        # Asignar destinatarios M2M
        if destinatarios:
            notification.destinatarios.set(destinatarios)

        return notification
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
import re

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    document = serializers.CharField()

    class Meta:
        model  = User
        fields = ['document', 'email', 'number', 'role', 'first_name', 'last_name']

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['document'])
        user.save()
        return user

    def validate(self, attrs):
        email = attrs.get('email')
        document = attrs.get('document')
        number = attrs.get('number')
        
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': f"El correo '{email}' ya está registrado."
            })
        
        if document and User.objects.filter(document=document).exists():
            raise serializers.ValidationError({
                'document': f"El documento '{document}' ya está registrado."
            })
        
        if number and User.objects.filter(number=number).exists():
            raise serializers.ValidationError({
                'number': f"El número telefónico '{number}' ya está registrado."
            })

        return attrs
    
    def validate_number(self, value):
        if not value:
            return value
            
        if not value.isdigit():
            raise serializers.ValidationError("El número telefónico solo puede contener dígitos.")
        
        if len(value) != 10:
            raise serializers.ValidationError("El número telefónico debe tener exactamente 10 dígitos.")
        
        if not value.startswith('3'):
            raise serializers.ValidationError("El número telefónico debe empezar con 3 (celulares colombianos).")
        
        return value

class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['document','email','number','role','is_active','date_joined','first_name','last_name', 'profile_picture']
        
class UserDeactivateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['document']
        
class UserDeleteSerializer(serializers.ModelSerializer):
    active_tickets = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['document','email','number','role','is_active', 'first_name','last_name','active_tickets']

    def get_active_tickets(self, obj):
        return obj.has_active_tickets()
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'number']
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': False, 'max_length': 150},
            'last_name': {'required': False, 'allow_blank': False, 'max_length': 150},
            'number': {'required': False, 'allow_blank': False, 'max_length': 10},
        }
    
    def validate_number(self, value):
        if not value:
            return value
            
        if not value.isdigit():
            raise serializers.ValidationError("El número telefónico solo puede contener dígitos.")
        
        if len(value) != 10:
            raise serializers.ValidationError("El número telefónico debe tener exactamente 10 dígitos.")
        
        if not value.startswith('3'):
            raise serializers.ValidationError("El número telefónico debe empezar con 3 (celulares colombianos).")
        
        return value

class UserUpdateProfilePictureSerializer(serializers.ModelSerializer):
    profile_picture = serializers.URLField(required=False, allow_blank=True, max_length=500)
    
    class Meta:
        model = User
        fields = ['profile_picture']
    
    def validate_profile_picture(self, value):
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("La URL de la imagen debe comenzar con http:// o https://")
        return value
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True, trim_whitespace=False, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not check_password(attrs['current_password'], user.password):
            raise serializers.ValidationError({"current_password": "La contraseña actual es incorrecta."})
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Las nuevas contraseñas no coinciden."})
        password_validation.validate_password(attrs['new_password'], user=user)
        return attrs
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user

class ChangePasswordByIdSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context['user']
        if not check_password(attrs['current_password'], user.password):
            raise serializers.ValidationError({"current_password": "contraseña actual inválida"})
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "las contraseñas no coinciden"})
        password_validation.validate_password(attrs['new_password'], user=user)
        return attrs

    def save(self, **kwargs):
        user = self.context['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user
class AdminUpdateUserSerializer (serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['document','email','number','role','is_active','first_name','last_name']
        extra_kwargs = {
            'document': {'required': False},  # Opcional: solo si se quiere cambiar
            'email': {'required': True, 'allow_blank': False, 'max_length': 254},
            'role': {'required': True},
            'is_active': {'required': True},
            'first_name': {'required': True, 'allow_blank': False, 'max_length': 150},
            'last_name': {'required': True, 'allow_blank': False, 'max_length': 150},
            'number': {'required': True, 'allow_blank': False, 'max_length': 10},
        }
    
    def validate(self, attrs):
        """
        Valida que email, document y number sean únicos excluyendo al usuario actual.
        Maneja el cambio de document (PK) de manera especial.
        """
        # Obtener la instancia del usuario que se está actualizando
        instance = self.instance
        
        if not instance:
            raise serializers.ValidationError("No se puede actualizar: usuario no encontrado.")
        
        email = attrs.get('email')
        document = attrs.get('document')
        number = attrs.get('number')
        
        # Validar email único (excluyendo el usuario actual)
        if email:
            email_exists = User.objects.filter(email=email).exclude(pk=instance.pk)
            if email_exists.exists():
                raise serializers.ValidationError({
                    'email': f"El correo '{email}' ya está registrado."
                })
        
        # Validar document único (excluyendo el usuario actual) - solo si se quiere cambiar
        if document and document != instance.document:
            document_exists = User.objects.filter(document=document).exclude(pk=instance.pk)
            if document_exists.exists():
                raise serializers.ValidationError({
                    'document': f"El documento '{document}' ya está registrado."
                })
        
        # Validar number único (excluyendo el usuario actual)
        if number:
            number_exists = User.objects.filter(number=number).exclude(pk=instance.pk)
            if number_exists.exists():
                raise serializers.ValidationError({
                    'number': f"El número telefónico '{number}' ya está registrado."
                })
        
        return attrs
    
    def save(self, **kwargs):
        """
        Guarda el usuario actualizando el PK si es necesario.
        Si se cambia el document (PK), se crea un nuevo usuario y se actualizan todas las referencias.
        """
        from django.db import transaction
        
        instance = self.instance
        validated_data = self.validated_data.copy()
        
        # Si se quiere cambiar el document (PK)
        new_document = validated_data.get('document')
        if new_document and new_document != instance.document:
            old_document = instance.document
            
            # Usar transacción para asegurar atomicidad
            with transaction.atomic():
                # Crear nuevo usuario con el nuevo document y todos los datos actualizados
                new_user = User(
                    document=new_document,
                    email=validated_data.get('email', instance.email),
                    number=validated_data.get('number', instance.number),
                    role=validated_data.get('role', instance.role),
                    is_active=validated_data.get('is_active', instance.is_active),
                    first_name=validated_data.get('first_name', instance.first_name),
                    last_name=validated_data.get('last_name', instance.last_name),
                    password=instance.password,  # Mantener la contraseña actual
                    is_staff=instance.is_staff,
                    is_superuser=instance.is_superuser,
                    date_joined=instance.date_joined,  # Mantener fecha original
                    last_login=instance.last_login,
                    must_change_password=instance.must_change_password,
                    profile_picture=instance.profile_picture,
                )
                
                # Guardar el nuevo usuario
                new_user.save()
                
                # Actualizar referencias en Ticket (técnico, cliente, administrador)
                from tickets.models import Ticket
                Ticket.objects.filter(tecnico_id=old_document).update(tecnico=new_user)
                Ticket.objects.filter(cliente_id=old_document).update(cliente=new_user)
                Ticket.objects.filter(administrador_id=old_document).update(administrador=new_user)
                
                # Actualizar referencias en StateChangeRequest
                from tickets.models import StateChangeRequest
                StateChangeRequest.objects.filter(requested_by_id=old_document).update(requested_by=new_user)
                StateChangeRequest.objects.filter(approved_by_id=old_document).update(approved_by=new_user)
                
                # Actualizar referencias en Notification
                from notifications.models import Notification
                Notification.objects.filter(usuario_id=old_document).update(usuario=new_user)
                Notification.objects.filter(enviado_por_id=old_document).update(enviado_por=new_user)
                
                # Actualizar ManyToMany en Notification (destinatarios)
                # Obtener todas las notificaciones que tienen al usuario antiguo como destinatario
                notifications_with_user = Notification.objects.filter(destinatarios=old_document)
                for notification in notifications_with_user:
                    notification.destinatarios.remove(instance)
                    notification.destinatarios.add(new_user)
                
                # Eliminar el usuario antiguo
                instance.delete()
                
                # Actualizar self.instance para que el serializer retorne el nuevo usuario
                self.instance = new_user
                
                # Retornar el nuevo usuario
                return new_user
        else:
            # Si no se cambia el document, actualización normal
            return super().save(**kwargs)
        
    def validate_number(self, value):
        if not value:
            return value
            
        if not value.isdigit():
            raise serializers.ValidationError("El número telefónico solo puede contener dígitos.")
        
        if len(value) != 10:
            raise serializers.ValidationError("El número telefónico debe tener exactamente 10 dígitos.")
        
        if not value.startswith('3'):
            raise serializers.ValidationError("El número telefónico debe empezar con 3 (celulares colombianos).")
        
        return value


# =============================================================================
# HU14A - Login: Serializer personalizado para autenticación JWT
# =============================================================================
# Este serializer extiende TokenObtainPairSerializer para manejar la autenticación
# con email como username y implementar validaciones específicas de la HU14A
# =============================================================================

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para autenticación JWT con email como username.
    
    Implementa los escenarios de la HU14A - Login:
    - Escenario 1: Inicio de sesión exitoso ✅
    - Escenario 2: Autenticación por rol ✅  
    - Escenario 7: Usuario inactivo ✖️
    - Escenario 12: Contraseña por defecto ✖️
    """
    
    @classmethod
    def get_token(cls, user):
        """
        Personaliza el token JWT con claims adicionales del usuario.
        """
        token = super().get_token(user)
        # Claims personalizados:
        token['email'] = user.email
        token['role'] = user.role
        token['is_active'] = user.is_active
        token['document'] = user.document
        return token
    
    def validate(self, attrs):
        """
        Valida las credenciales y aplica las reglas de negocio de la HU14A.

        - Valida credenciales vía `super().validate` (JWT).
        - Verifica explícitamente la contraseña para retornar un mensaje claro.
        - Aplica reglas: usuario activo y contraseña por defecto.
        - Enriquecer respuesta con datos del usuario y su rol.
        """
        # 1) Validación base de SimpleJWT (email/password) -> genera tokens
        data = super().validate(attrs)

        # 2) Verificación explícita de contraseña con mensaje claro
        #    Esto asegura que, si llega hasta aquí pero la contraseña no coincide,
        #    se informe el motivo exacto.
        user = self.user
        if not user.check_password(attrs.get('password', '')):
            raise AuthenticationFailed("Credenciales inválidas")

        # 3) Usuario debe estar activo
        if not user.is_active:
            raise AuthenticationFailed("Cuenta inactiva")

        # 4) Usuario debe cambiar contraseña (por defecto/temporal)
        if getattr(user, 'must_change_password', False):
            raise AuthenticationFailed("Por favor, cambie la contraseña")

        # 5) Enriquecer la respuesta con datos del usuario y su rol
        data['user'] = {
            'document': user.document,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
        }

        return data
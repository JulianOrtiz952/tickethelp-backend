from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
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
            'document': {'required': True, 'allow_blank': False, 'max_length': 20},
            'email': {'required': True, 'allow_blank': False, 'max_length': 254},
            'role': {'required': True},
            'is_active': {'required': True},
            'first_name': {'required': True, 'allow_blank': False, 'max_length': 150},
            'last_name': {'required': True, 'allow_blank': False, 'max_length': 150},
            'number': {'required': True, 'allow_blank': False, 'max_length': 10},
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
        # Si quieres más (evita PII innecesaria):
        # token['first_name'] = user.first_name
        # token['last_name']  = user.last_name
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
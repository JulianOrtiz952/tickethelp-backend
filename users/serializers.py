from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import check_password
import re

User = get_user_model()

# Serializer para crear usuarios
class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    document = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model  = User
        fields = ['document', 'email', 'number', 'role', 'first_name', 'last_name', 'password']

    # Crea el usuario con la contraseña hasheada
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    # Valida que el email y documento sean únicos
    def validate(self, attrs):
        email = attrs.get('email')
        document = attrs.get('document')
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': f"El correo '{email}' ya está registrado."
            })
        
        if document and User.objects.filter(document=document).exists():
            raise serializers.ValidationError({
                'document': f"El documento '{document}' ya está registrado."
            })

        return attrs

# Serializer para leer usuarios
class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['document','email','number','role','is_active','date_joined','first_name','last_name']
        
# Serializer para eliminar usuarios
class UserDeleteSerializer(serializers.ModelSerializer):
    # Se debe verificar si el usuario tiene tickets activos antes de eliminarlo
    active_tickets = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['document','email','number','role','is_active', 'first_name','last_name','active_tickets']

    def get_active_tickets(self, obj):
        return obj.has_active_tickets()
    
    
# Serializer para actualizar usuarios
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'number']
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': False, 'max_length': 150},
            'last_name': {'required': False, 'allow_blank': False, 'max_length': 150},
            'number': {'required': False, 'allow_blank': False, 'max_length': 15},
        }
    def validate_number(self, value):
        if value and not re.fullmatch(r'^\+?\d{7,15}$', value):
            raise serializers.ValidationError("Número de teléfono inválido.")
        return value

# Serializer para cambiar la contraseña
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

# Para pruebas sin auth: cambio de contraseña por ID (valida current_password y confirmación)
class ChangePasswordByIdSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context['user']  # <- se inyecta desde la vista
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
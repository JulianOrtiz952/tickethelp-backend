from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

# Serializer para crear usuarios
class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="correo ya registrado")]
    )
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model  = User
        fields = ['id', 'email', 'number', 'role', 'created_at', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

# Serializer para leer usuarios
class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id','email','number','role','is_active','date_joined','first_name','last_name']
        
# Serializer para eliminar usuarios
class UserDeleteSerializer(serializers.ModelSerializer):
    # Se debe verificar si el usuario tiene tickets activos antes de eliminarlo
    active_tickets = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id','email','number','role','is_active','created_at','first_name','last_name','active_tickets']

    def get_active_tickets(self, obj):
        return obj.has_active_tickets()
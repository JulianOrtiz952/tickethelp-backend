# users/serializers.py
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="correo ya registrado")]
    )
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ['email','number','role','password','first_name','last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id','email','number','role','is_active','date_joined','first_name','last_name']

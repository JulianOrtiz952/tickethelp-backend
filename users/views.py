from rest_framework import viewsets, permissions, status, decorators, response
from django.contrib.auth import get_user_model
from rest_framework.validators import UniqueValidator
from rest_framework import serializers

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="correo ya registrado")]
    )
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta:
        model  = User
        fields = ['name','lastName','email','number','role','password','first_name','last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id','name','lastName','email','number','role','is_active','date_joined','first_name','last_name']
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'ADMIN'

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        return UserCreateSerializer if self.action in ['create','update','partial_update'] else UserReadSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.has_active_tickets():
            return response.Response(
                {"detail": "No se puede eliminar porque tiene tickets activos. Puede desactivarlo."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)

    @decorators.action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return response.Response({"detail": "Usuario desactivado."})

class BaseRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    def get_serializer_class(self):
        return UserCreateSerializer if self.action in ['create','update','partial_update'] else UserReadSerializer
    def perform_create(self, serializer):
        serializer.save(role=self.Role)

class AdminViewSet(BaseRoleViewSet):
    ROLE = 'ADMIN'
    def get_queryset(self): return User.objects.filter(role=self.ROLE)

class TechnicianViewSet(BaseRoleViewSet):
    ROLE = 'TECH'
    def get_queryset(self): return User.objects.filter(role=self.ROLE)

class ClientViewSet(BaseRoleViewSet):
    ROLE = 'CLIENT'
    def get_queryset(self): return User.objects.filter(role=self.ROLE)

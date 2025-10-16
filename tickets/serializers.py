from rest_framework import serializers
from users.models import User
from tickets.models import Ticket, Estado

class TicketSerializer(serializers.ModelSerializer):

    administrador = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.ADMIN), required=True
    )
    tecnico = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.TECH), required=True
    )
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.CLIENT), required=True
    )
    estado = serializers.PrimaryKeyRelatedField(
        queryset=Estado.objects.all(), required=True
    )

    class Meta:
        model = Ticket
        fields = '__all__'

    
    def validate(self, attrs):
        admin = attrs["administrador"]
        tech  = attrs["tecnico"]
        cli   = attrs["cliente"]

        # Roles correctos (doble seguridad si alguien intenta forzar un ID por API) (GPT)
        if admin.role != User.Role.ADMIN:
            raise serializers.ValidationError({"administrador": "Debe ser ADMIN."})
        if tech.role != User.Role.TECH:
            raise serializers.ValidationError({"tecnico": "Debe ser TECH."})
        if cli.role != User.Role.CLIENT:
            raise serializers.ValidationError({"cliente": "Debe ser CLIENT."})
        
        # Que estén activos
        for field, user in [("administrador", admin), ("tecnico", tech), ("cliente", cli)]:
            if not user.is_active:
                raise serializers.ValidationError({field: "El usuario está desactivado."})
        
        
        return attrs

class EstadoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Estado
        fields = '__all__'
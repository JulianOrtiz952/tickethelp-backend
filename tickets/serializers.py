from rest_framework import serializers
from django.db.models import Count
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
        tech = attrs["tecnico"]
        cli = attrs["cliente"]

        if admin.role != User.Role.ADMIN:
            raise serializers.ValidationError({"administrador": "Debe ser ADMIN."})
        if tech.role != User.Role.TECH:
            raise serializers.ValidationError({"tecnico": "Debe ser TECH."})
        if cli.role != User.Role.CLIENT:
            raise serializers.ValidationError({"cliente": "Debe ser CLIENT."})
        
        if not admin.is_active:
            raise serializers.ValidationError({"administrador": "El usuario está desactivado."})
        if not tech.is_active:
            raise serializers.ValidationError({"tecnico": "El usuario está desactivado."})
        if not cli.is_active:
            raise serializers.ValidationError({"cliente": "El usuario está desactivado."})
        
        return attrs

class EstadoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Estado
        fields = '__all__'


class LeastBusyTechnicianSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)

    def get_least_busy_technician_email(self):
        technician = User.objects.filter(
            role=User.Role.TECH, 
            is_active=True
        ).annotate(
            ticket_count=Count('tickets_asignados')
        ).order_by('ticket_count', '?').first()
        
        return technician.email if technician else None

    def to_representation(self, instance):
        return {
            'email': self.get_least_busy_technician_email()
        }

class ChangeTechnicianSerializer(serializers.Serializer):
    documento_tecnico = serializers.CharField(max_length=10, required=True)

    def validate_documento_tecnico(self, value):
        try:
            tecnico = User.objects.get(document=value, role=User.Role.TECH)
            if not tecnico.is_active:
                raise serializers.ValidationError("El técnico está desactivado.")
            return tecnico
        except User.DoesNotExist:
            raise serializers.ValidationError("No existe un técnico con ese documento.")
from rest_framework import serializers
from django.db.models import Count
from django.utils import timezone
from users.models import User
from tickets.models import Ticket, Estado, StateChangeRequest

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

        if isinstance(tech, list) and len(tech) > 1:
            raise serializers.ValidationError({"tecnico": "Solo se puede seleccionar un técnico."})

        if not tech:
            raise serializers.ValidationError({"tecnico": "Debe seleccionar un técnico."})

        if tech.role != User.Role.TECH:
            raise serializers.ValidationError({"tecnico": "Debe ser TECH."})
        
        if not tech.is_active:
            raise serializers.ValidationError({"tecnico": "El usuario está desactivado."})

        if admin.role != User.Role.ADMIN:
            raise serializers.ValidationError({"administrador": "Debe ser ADMIN."})
        if not admin.is_active:
            raise serializers.ValidationError({"administrador": "El usuario está desactivado."})

        if cli.role != User.Role.CLIENT:
            raise serializers.ValidationError({"cliente": "Debe ser CLIENT."})
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
    documento_tecnico = serializers.CharField(max_length=10, required=True, allow_blank=False)

    def validate_documento_tecnico(self, value):
        if not value or value.strip() == "":
            raise serializers.ValidationError("Debe proporcionar el documento del técnico.")
        
        try:
            tecnico = User.objects.get(document=value, role=User.Role.TECH)
        except User.DoesNotExist:
            raise serializers.ValidationError("No existe un técnico con ese documento.")
        
        if not tecnico.is_active:
            raise serializers.ValidationError("El técnico está desactivado.")
        
        return tecnico

    def validate(self, attrs):
        documento = attrs.get('documento_tecnico')
        if isinstance(documento, list) and len(documento) > 1:
            raise serializers.ValidationError({"documento_tecnico": "Solo se puede seleccionar un técnico."})
        
        return attrs


class ActiveTechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['document', 'email', 'first_name', 'last_name', 'number']


class StateChangeSerializer(serializers.Serializer):
    to_state = serializers.PrimaryKeyRelatedField(queryset=Estado.objects.all(), required=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_to_state(self, value):
        if not value:
            raise serializers.ValidationError("Debe seleccionar un estado de destino.")
        return value

    def validate(self, attrs):
        ticket = self.context['ticket']
        to_state = attrs['to_state']
        
        if ticket.estado == to_state:
            raise serializers.ValidationError({"to_state": "El ticket ya está en este estado."})
        
        return attrs


class StateApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'], required=True)
    rejection_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        action = attrs['action']
        rejection_reason = attrs.get('rejection_reason', '')
        
        if action == 'reject' and not rejection_reason.strip():
            raise serializers.ValidationError({"rejection_reason": "Debe proporcionar una razón para el rechazo."})
        
        return attrs


class PendingApprovalSerializer(serializers.ModelSerializer):
    ticket_titulo = serializers.CharField(source='ticket.titulo', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    from_state_name = serializers.CharField(source='from_state.nombre', read_only=True)
    to_state_name = serializers.CharField(source='to_state.nombre', read_only=True)

    class Meta:
        model = StateChangeRequest
        fields = ['id', 'ticket', 'ticket_titulo', 'requested_by', 'requested_by_name', 
                 'from_state', 'from_state_name', 'to_state', 'to_state_name', 
                 'reason', 'created_at', 'status']
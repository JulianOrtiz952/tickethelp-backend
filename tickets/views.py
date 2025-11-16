from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from tickets.permissions import IsAdmin, IsAdminOrTechnician
from tickets.permissions import IsAdmin, IsTechnician
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
import tickets
from tickets.models import Ticket, Estado, StateChangeRequest
from tickets.serializers import TicketSerializer, EstadoSerializer, LeastBusyTechnicianSerializer, ChangeTechnicianSerializer, ActiveTechnicianSerializer, StateChangeSerializer, StateApprovalSerializer, PendingApprovalSerializer, RequestFinalizationSerializer
from notifications.services import NotificationService

User = get_user_model()


class TicketAV(ListCreateAPIView):

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        active_technicians = User.objects.filter(role=User.Role.TECH, is_active=True).count()
        if active_technicians == 0:
            return Response({
                'error': 'No hay técnicos activos disponibles para asignar tickets.',
                'message': 'Debe crear al menos un técnico activo antes de crear tickets.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)

class EstadoAV(ListCreateAPIView):

    queryset = Estado.objects.all().order_by("nombre")
    serializer_class = EstadoSerializer
    permission_classes = [IsAdmin]


class LeastBusyTechnicianAV(RetrieveAPIView):
    
    serializer_class = LeastBusyTechnicianSerializer
    permission_classes = [IsAdmin]
    
    def get_object(self):
        return None
    
    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        data = serializer.to_representation(None)
        
        if data['id']:
            return Response(data)
        else:
            return Response(data, status=status.HTTP_404_NOT_FOUND)

class ChangeTechnicianAV(UpdateAPIView):
    http_method_names = ['put', 'patch', 'options', 'head']
    serializer_class = ChangeTechnicianSerializer
    permission_classes = [IsAdmin]
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)
    
    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            new_technician = serializer.validated_data['documento_tecnico']
            old_technician = ticket.tecnico
            
            ticket.tecnico = new_technician
            try:
                ticket.save()
            except Exception as e:
                logger = __import__('logging').getLogger(__name__)
                logger.error(f"Error guardando ticket al cambiar técnico: {e}")
                return Response({'error': 'error_saving_ticket', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'message': 'Técnico actualizado correctamente',
                'ticket_id': ticket.pk,
                'nuevo_tecnico': {
                    'documento': new_technician.document,
                    'email': new_technician.email,
                    'nombre': f"{new_technician.first_name} {new_technician.last_name}"
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        # Evitar que GET devuelva información; explícitamente 405
        return Response({'detail': 'Method "GET" not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ActiveTechniciansAV(ListAPIView):
    
    serializer_class = ActiveTechnicianSerializer
    permission_classes = [IsAdminOrTechnician]
    
    def get_queryset(self):
        return User.objects.filter(role=User.Role.TECH, is_active=True).order_by('first_name', 'last_name')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Lista de técnicos activos disponibles',
            'total_tecnicos': queryset.count(),
            'tecnicos': serializer.data
        }, status=status.HTTP_200_OK)


class StateChangeAV(UpdateAPIView):
    permission_classes = [IsTechnician]   # puedes dejarlo así; el “quitar permisos” se refería al flujo de aprobación
    serializer_class = StateChangeSerializer

    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)

    def put(self, request, *args, **kwargs):
        ticket = self.get_object()

        # Obtener usuario desde query param o request.user (como ya lo tienes)
        user_document = request.query_params.get('user_document')
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Response({
                    'error': 'Usuario no encontrado',
                    'message': 'El documento de usuario proporcionado no existe'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return Response({
                    'error': 'Usuario requerido',
                    'message': 'Debe proporcionar user_document como parámetro de consulta'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Solo el técnico asignado puede cambiar (si quieres permitir admin también, lo ajustamos)
        if ticket.tecnico != user:
            return Response({
                'error': 'No autorizado',
                'message': 'Solo el técnico asignado puede cambiar el estado'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data, context={'ticket': ticket})
        serializer.is_valid(raise_exception=True)

        to_state = serializer.validated_data['to_state']

        # Aplicar el cambio inmediato, sin solicitudes de aprobación
        ticket.estado = to_state
        ticket.save(update_fields=['estado'])

        return Response({
            'message': 'Estado actualizado correctamente',
            'ticket_id': ticket.pk,
            'from_state_id': to_state.id - 1,  # por regla, siempre era actual+1
            'to_state_id': to_state.id
        }, status=status.HTTP_200_OK)


class StateApprovalAV(UpdateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = StateApprovalSerializer
    
    def get_object(self):
        request_id = self.kwargs.get('request_id')
        return get_object_or_404(StateChangeRequest, pk=request_id, status=StateChangeRequest.Status.PENDING)
    
    def put(self, request, *args, **kwargs):
        state_request = self.get_object()
        
        # Obtener usuario desde parámetros de consulta o request.user
        user_document = request.query_params.get('user_document')
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Response({
                    'error': 'Usuario no encontrado',
                    'message': 'El documento de usuario proporcionado no existe'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return Response({
                    'error': 'Usuario requerido',
                    'message': 'Debe proporcionar user_document como parámetro de consulta'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar que el usuario sea administrador
        if user.role != User.Role.ADMIN:
            return Response({
                'error': 'No autorizado',
                'message': 'Solo los administradores pueden aprobar/rechazar solicitudes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # ID 5 = estado finalizado (closed)
        FINAL_STATE_ID = 5
        
        # No permitir aprobar cambios de estado si el ticket ya está finalizado
        if state_request.ticket.estado_id == FINAL_STATE_ID:
            return Response({
                'error': 'Ticket finalizado',
                'message': 'No se puede aprobar un cambio de estado para un ticket finalizado. La solicitud será rechazada automáticamente.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            
            if action == 'approve':
                # Aprobar el cambio de estado
                state_request.ticket.estado = state_request.to_state
                state_request.ticket.save()
                
                state_request.status = StateChangeRequest.Status.APPROVED
                state_request.approved_by = user
                state_request.approved_at = timezone.now()
                state_request.save()
                
                # Enviar notificación al técnico
                NotificationService.enviar_aprobacion_cambio_estado(state_request)
                
                if state_request.to_state.es_final:
                    NotificationService.enviar_ticket_cerrado(state_request.ticket, state_request)
                
                return Response({
                    'message': 'Cambio de estado aprobado y aplicado',
                    'ticket_id': state_request.ticket.pk,
                    'new_state': state_request.to_state.nombre
                }, status=status.HTTP_200_OK)
            
            else:  # reject
                rejection_reason = serializer.validated_data.get('rejection_reason', '')
                
                state_request.status = StateChangeRequest.Status.REJECTED
                state_request.approved_by = user
                state_request.approved_at = timezone.now()
                state_request.rejection_reason = rejection_reason
                state_request.save()
                
                # Enviar notificación al técnico
                NotificationService.enviar_rechazo_cambio_estado(state_request)
                
                return Response({
                    'message': 'Solicitud de cambio de estado rechazada',
                    'ticket_id': state_request.ticket.pk,
                    'rejection_reason': rejection_reason
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingApprovalsAV(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = PendingApprovalSerializer
    
    def get_queryset(self):
        return StateChangeRequest.objects.filter(status=StateChangeRequest.Status.PENDING).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'message': 'Solicitudes de cambio de estado pendientes',
            'total_pending': queryset.count(),
            'requests': serializer.data
        }, status=status.HTTP_200_OK)

class TicketListView(ListAPIView):
    serializer_class = TicketSerializer

    def get_queryset(self):
        user_document = self.request.query_params.get('user_document') #Cambiar poa request.user cuando haya auth 

        if not user_document or len(user_document.strip()) == 0:
            return Response({
                'error': 'Solicitud inválida',
                'message': 'El parámetro "user_document" está vacío o tiene un formato incorrecto.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(document=user_document)
        except User.DoesNotExist:
            return Response({
                'error': 'Usuario no encontrado',
                'message': 'El documento de usuario proporcionado no existe'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.role == User.Role.TECH:
            tickets = Ticket.objects.filter(tecnico=user)
            if not tickets:
                return Response({
                    'message': 'No tienes tickets registrados.'
                }, status=status.HTTP_200_OK)
            return tickets

        elif user.role == User.Role.ADMIN:
            tickets = Ticket.objects.all()
            if not tickets:
                return Response({
                    'message': 'No tienes tickets registrados.'
                }, status=status.HTTP_200_OK)
            return tickets

        elif user.role == User.Role.CLIENT:
            tickets = Ticket.objects.filter(cliente=user)
            if not tickets:
                return Response({
                    'message': 'No tienes tickets registrados.'
                }, status=status.HTTP_200_OK)
            return tickets

        return Ticket.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        if isinstance(queryset, Response):
            return queryset

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Lista de tickets',
            'total_tickets': queryset.count(),
            'tickets': serializer.data
        }, status=status.HTTP_200_OK)


class RequestFinalizationAV(UpdateAPIView):
    """
    Endpoint para que un técnico solicite la finalización de un ticket.
    El ticket pasa a "En pruebas pendiente de aprobación" y se crea una solicitud
    que debe ser aprobada por el administrador.
    """
    permission_classes = [IsTechnician]
    serializer_class = RequestFinalizationSerializer
    http_method_names = ['put', 'patch', 'options', 'head']

    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)

    def put(self, request, *args, **kwargs):
        # Escenario 7 - Usuario no autenticado
        # La validación de autenticación se hace automáticamente por IsTechnician
        # pero verificamos explícitamente para dar un mensaje claro
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return Response({
                'error': 'No autenticado',
                'message': 'Debe autenticarse para solicitar la finalización de tickets.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Escenario 6 - Usuario sin rol técnico
        if user.role != User.Role.TECH:
            return Response({
                'error': 'Sin permisos',
                'message': 'No tiene permisos para solicitar la finalización de tickets como técnico.'
            }, status=status.HTTP_403_FORBIDDEN)

        ticket = self.get_object()
        
        # Escenario 5 - Ticket no existe (manejado por get_object con get_object_or_404)
        # pero lo verificamos explícitamente para dar un mensaje claro
        if not ticket:
            return Response({
                'error': 'Ticket no encontrado',
                'message': 'El ticket especificado no fue encontrado.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Escenario 3 - Ticket no asignado al técnico
        if ticket.tecnico != user:
            return Response({
                'error': 'Sin permisos',
                'message': 'El técnico no tiene permisos para solicitar la finalización de ese ticket.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validar el serializer (incluye validación de estado)
        serializer = self.get_serializer(data=request.data, context={'ticket': ticket})
        
        if not serializer.is_valid():
            # Escenario 4 - Ticket en estado no válido
            errors = serializer.errors
            if 'non_field_errors' in errors:
                error_data = errors['non_field_errors'][0]
                if isinstance(error_data, dict) and error_data.get('error') == 'Estado no válido':
                    return Response({
                        'error': 'Estado no válido',
                        'message': error_data.get('message', 'El ticket no está en un estado apropiado para solicitar su finalización.')
                    }, status=status.HTTP_400_BAD_REQUEST)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Obtener el estado "En pruebas pendiente de aprobación" (id=6)
        try:
            estado_pendiente_aprobacion = Estado.objects.get(codigo='trial_pending_approval')
        except Estado.DoesNotExist:
            return Response({
                'error': 'Error del sistema',
                'message': 'El estado "En pruebas pendiente de aprobación" no está configurado en el sistema.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Obtener el estado "Finalizado" (id=5)
        try:
            estado_finalizado = Estado.objects.get(codigo='closed')
        except Estado.DoesNotExist:
            return Response({
                'error': 'Error del sistema',
                'message': 'El estado "Finalizado" no está configurado en el sistema.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Escenario 1 y 2 - Solicitud exitosa
        # Guardar el estado anterior
        estado_anterior = ticket.estado
        
        # Actualizar el estado del ticket a "En pruebas pendiente de aprobación"
        ticket.estado = estado_pendiente_aprobacion
        ticket.save(update_fields=['estado'])

        # Crear la solicitud de cambio de estado
        reason = serializer.validated_data.get('reason', '')
        state_request = StateChangeRequest.objects.create(
            ticket=ticket,
            requested_by=user,
            from_state=estado_anterior,
            to_state=estado_finalizado,
            status=StateChangeRequest.Status.PENDING,
            reason=reason
        )

        # Enviar notificación al administrador
        try:
            NotificationService.enviar_solicitud_cambio_estado(state_request)
        except Exception as e:
            # No fallar la solicitud si hay error en la notificación
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"Error enviando notificación de solicitud de finalización: {e}")

        # Preparar respuesta con información actualizada
        ticket_serializer = TicketSerializer(ticket)
        
        return Response({
            'message': 'Solicitud de finalización creada exitosamente',
            'ticket': ticket_serializer.data,
            'state_request': {
                'id': state_request.id,
                'created_at': state_request.created_at,
                'requested_by': {
                    'document': user.document,
                    'email': user.email,
                    'full_name': user.get_full_name()
                },
                'from_state': estado_anterior.nombre,
                'to_state': estado_finalizado.nombre,
                'status': state_request.status,
                'reason': reason
            }
        }, status=status.HTTP_200_OK)
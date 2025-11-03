from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
import tickets
from tickets.models import Ticket, Estado, StateChangeRequest
from tickets.serializers import TicketSerializer, EstadoSerializer, LeastBusyTechnicianSerializer, ChangeTechnicianSerializer, ActiveTechnicianSerializer, StateChangeSerializer, StateApprovalSerializer, PendingApprovalSerializer
from notifications.services import NotificationService
from rest_framework import viewsets, permissions
from .models import TicketHistory
from .serializers import TicketHistorySerializer

User = get_user_model()


class TicketAV(ListCreateAPIView):

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def create(self, request, *args, **kwargs):
        active_technicians = User.objects.filter(role=User.Role.TECH, is_active=True).count()
        if active_technicians == 0:
            return Response({
                'error': 'No hay técnicos activos disponibles para asignar tickets.',
                'message': 'Debe crear al menos un técnico activo antes de crear tickets.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener el usuario que está creando el ticket
        user_document = request.query_params.get('user_document')
        if user_document:
            try:
                usuario_creador = User.objects.get(document=user_document)
            except User.DoesNotExist:
                usuario_creador = None
        else:
            usuario_creador = getattr(request, 'user', None)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Crear el ticket
        ticket = serializer.save()
        
        # Crear entrada en el historial con todos los datos del ticket
        datos_ticket = {
            'titulo': ticket.titulo,
            'descripcion': ticket.descripcion,
            'equipo': ticket.equipo,
            'administrador': ticket.administrador.document if ticket.administrador else None,
            'administrador_nombre': ticket.administrador.get_full_name() if ticket.administrador else None,
            'cliente': ticket.cliente.document if ticket.cliente else None,
            'cliente_nombre': ticket.cliente.get_full_name() if ticket.cliente else None,
            'tecnico': ticket.tecnico.document if ticket.tecnico else None,
            'tecnico_nombre': ticket.tecnico.get_full_name() if ticket.tecnico else None,
            'estado': ticket.estado.nombre if ticket.estado else None,
        }
        
        TicketHistory.crear_entrada_historial(
            ticket=ticket,
            accion="Creación del ticket",
            realizado_por=usuario_creador,
            datos_ticket=datos_ticket
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class EstadoAV(ListCreateAPIView):

    queryset = Estado.objects.all().order_by("nombre")
    serializer_class = EstadoSerializer


class LeastBusyTechnicianAV(RetrieveAPIView):
    
    serializer_class = LeastBusyTechnicianSerializer
    
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
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)
    
    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        
        # Validar que el ticket no esté finalizado
        if ticket.estado and ticket.estado.es_final:
            return Response({
                'error': 'Ticket finalizado',
                'message': 'No se puede modificar un ticket que ya ha sido finalizado.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            new_technician = serializer.validated_data['documento_tecnico']
            old_technician = ticket.tecnico
            
            # Obtener el usuario que está realizando el cambio
            user_document = request.query_params.get('user_document')
            if user_document:
                try:
                    usuario_cambio = User.objects.get(document=user_document)
                except User.DoesNotExist:
                    usuario_cambio = None
            else:
                usuario_cambio = getattr(request, 'user', None)
            
            ticket.tecnico = new_technician
            try:
                ticket.save()
            except Exception as e:
                logger = __import__('logging').getLogger(__name__)
                logger.error(f"Error guardando ticket al cambiar técnico: {e}")
                return Response({'error': 'error_saving_ticket', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Crear entrada en el historial
            TicketHistory.crear_entrada_historial(
                ticket=ticket,
                accion=f"Cambio de técnico de {old_technician.get_full_name() if old_technician else 'Sin técnico'} a {new_technician.get_full_name()}",
                realizado_por=usuario_cambio,
                tecnico_anterior=old_technician,
                estado_anterior=ticket.estado.nombre if ticket.estado else None
            )

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
    permission_classes = [AllowAny]
    serializer_class = StateChangeSerializer
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)
    
    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        
        # Validar que el ticket no esté finalizado
        if ticket.estado and ticket.estado.es_final:
            return Response({
                'error': 'Ticket finalizado',
                'message': 'No se puede modificar un ticket que ya ha sido finalizado.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        if ticket.tecnico != user:
            return Response({
                'error': 'No autorizado',
                'message': 'Solo el técnico asignado puede solicitar cambios de estado'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data, context={'ticket': ticket})
        
        if serializer.is_valid():
            to_state = serializer.validated_data['to_state']
            reason = serializer.validated_data.get('reason', '')
            estado_anterior = ticket.estado.nombre if ticket.estado else None
            
            if to_state.es_final:
                state_request = StateChangeRequest.objects.create(
                    ticket=ticket,
                    requested_by=user,
                    from_state=ticket.estado,
                    to_state=to_state,
                    reason=reason
                )
                
                # Enviar notificación al administrador
                NotificationService.enviar_solicitud_cambio_estado(state_request)
                
                return Response({
                    'message': 'El estado final requiere validación del administrador, solicitud enviada correctamente',
                    'request_id': state_request.id,
                    'status': 'pending_approval',
                    'to_state': to_state.nombre
                }, status=status.HTTP_202_ACCEPTED)
            else:
                ticket.estado = to_state
                ticket.save()
                
                # Crear entrada en el historial
                TicketHistory.crear_entrada_historial(
                    ticket=ticket,
                    accion=f"Cambio de estado de '{estado_anterior}' a '{to_state.nombre}'",
                    realizado_por=user,
                    estado_anterior=estado_anterior
                )
                
                return Response({
                    'message': 'Estado actualizado correctamente',
                    'ticket_id': ticket.pk,
                    'new_state': to_state.nombre
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StateApprovalAV(UpdateAPIView):
    permission_classes = [AllowAny]
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
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            
            if action == 'approve':
                # Validar que el ticket no esté finalizado antes de aprobar
                if state_request.ticket.estado and state_request.ticket.estado.es_final:
                    return Response({
                        'error': 'Ticket ya finalizado',
                        'message': 'El ticket ya está en estado final, no se pueden realizar más cambios.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Aprobar el cambio de estado
                estado_anterior = state_request.ticket.estado.nombre if state_request.ticket.estado else None
                state_request.ticket.estado = state_request.to_state
                state_request.ticket.save()
                
                state_request.status = StateChangeRequest.Status.APPROVED
                state_request.approved_by = user
                state_request.approved_at = timezone.now()
                state_request.save()
                
                # Crear entrada en el historial
                accion_texto = f"Cambio de estado aprobado de '{estado_anterior}' a '{state_request.to_state.nombre}'"
                if state_request.to_state.es_final:
                    accion_texto += " - Ticket finalizado"
                
                TicketHistory.crear_entrada_historial(
                    ticket=state_request.ticket,
                    accion=accion_texto,
                    realizado_por=user,
                    estado_anterior=estado_anterior
                )
                
                # Enviar notificación al técnico
                NotificationService.enviar_aprobacion_cambio_estado(state_request)
                
                if state_request.to_state.es_final:
                    NotificationService.enviar_ticket_cerrado(state_request.ticket, state_request)
                
                return Response({
                    'message': 'Cambio de estado aprobado y aplicado',
                    'ticket_id': state_request.ticket.pk,
                    'new_state': state_request.to_state.nombre,
                    'is_final': state_request.to_state.es_final
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
    permission_classes = [AllowAny]
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


# =============================================================================
# HU13B - Historial: Vista para el historial de cambios de estado del ticket
# =============================================================================
# Esta vista permite consultar el historial de un ticket (solo administrador).
# =============================================================================

class TicketHistoryAV(RetrieveAPIView):
    """
    Endpoint para consultar el historial completo de un ticket por su ID.
    Solo accesible para administradores.
    """
    serializer_class = TicketHistorySerializer
    permission_classes = [AllowAny]  # Temporal, cambiar a IsAdminUser cuando haya autenticación
    
    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        if ticket_id:
            return TicketHistory.objects.filter(ticket_id=ticket_id).order_by('-fecha')
        return TicketHistory.objects.none()
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        
        # Validar que el ticket existe
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        
        # Validar que el usuario es administrador
        user_document = self.request.query_params.get('user_document')
        if user_document:
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Response({
                    'error': 'Usuario no encontrado',
                    'message': 'El documento de usuario proporcionado no existe'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = getattr(self.request, 'user', None)
            if not user or not user.is_authenticated:
                return Response({
                    'error': 'Usuario requerido',
                    'message': 'Debe proporcionar user_document como parámetro de consulta'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if user.role != User.Role.ADMIN:
            return Response({
                'error': 'No autorizado',
                'message': 'Solo los administradores pueden consultar el historial de tickets'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Retornar el queryset completo (no un objeto individual)
        return self.get_queryset()
    
    def retrieve(self, request, *args, **kwargs):
        queryset = self.get_object()
        
        # Si get_object retornó un Response (error), retornarlo
        if isinstance(queryset, Response):
            return queryset
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Obtener información del ticket
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        
        return Response({
            'message': 'Historial del ticket obtenido exitosamente',
            'ticket_id': ticket_id,
            'ticket_titulo': ticket.titulo,
            'estado_actual': ticket.estado.nombre if ticket.estado else 'Sin estado',
            'tecnico_actual': ticket.tecnico.get_full_name() if ticket.tecnico else 'Sin técnico asignado',
            'total_registros': queryset.count(),
            'historial': serializer.data
        }, status=status.HTTP_200_OK)
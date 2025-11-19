from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView
from rest_framework import status
from rest_framework.response import Response
from tickets.permissions import IsAdmin, IsAdminOrTechnician, IsClient, IsTechnician, IsAdminOrTechnicianOrClient, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
import logging
from tickets.models import Ticket, Estado, StateChangeRequest
from tickets.serializers import (
    TicketSerializer, EstadoSerializer, LeastBusyTechnicianSerializer,
    ChangeTechnicianSerializer, ActiveTechnicianSerializer, StateChangeSerializer,
    StateApprovalSerializer, PendingApprovalSerializer,
    TicketTimelineSerializer
)
from notifications.services import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


class TicketAV(ListCreateAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        if not User.objects.filter(role=User.Role.TECH, is_active=True).exists():
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
        status_code = status.HTTP_200_OK if data['id'] else status.HTTP_404_NOT_FOUND
        return Response(data, status=status_code)


class ChangeTechnicianAV(UpdateAPIView):
    http_method_names = ['put', 'patch', 'options', 'head']
    serializer_class = ChangeTechnicianSerializer
    permission_classes = [IsAdmin]
    
    def get_object(self):
        return get_object_or_404(Ticket, pk=self.kwargs.get('ticket_id'))
    
    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_technician = serializer.validated_data['documento_tecnico']
        ticket.tecnico = new_technician
        
        try:
            ticket.save()
        except Exception as e:
            logger.error(f"Error guardando ticket al cambiar técnico: {e}")
            return Response({
                'error': 'error_saving_ticket',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'message': 'Técnico actualizado correctamente',
            'ticket_id': ticket.pk,
            'nuevo_tecnico': {
                'documento': new_technician.document,
                'email': new_technician.email,
                'nombre': f"{new_technician.first_name} {new_technician.last_name}"
            }
        }, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        return Response({
            'detail': 'Method "GET" not allowed.'
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
    permission_classes = [IsTechnician]
    serializer_class = StateChangeSerializer

    def get_object(self):
        return get_object_or_404(Ticket, pk=self.kwargs.get('ticket_id'))

    def _get_user(self, request):
        user_document = request.query_params.get('user_document')
        if user_document:
            try:
                return User.objects.get(document=user_document)
            except User.DoesNotExist:
                return None
        return getattr(request, 'user', None)

    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        user = self._get_user(request)

        if not user or not user.is_authenticated or user.role != User.Role.TECH:
            return Response({
                'error': 'No autorizado',
                'message': 'Debe iniciar sesión como técnico para cambiar el estado de un ticket.'
            }, status=status.HTTP_403_FORBIDDEN)

        if ticket.tecnico != user:
            return Response({
                'error': 'No autorizado',
                'message': 'Solo el técnico asignado puede solicitar cambios de estado.'
            }, status=status.HTTP_403_FORBIDDEN)

        if ticket.estado.es_final:
            return Response({
                'error': 'No permitido',
                'message': 'El ticket ya está finalizado y no puede modificarse.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if ticket.estado.codigo == "trial_pending_approval":
            return Response({
                'error': 'No permitido',
                'message': 'El ticket está pendiente de aprobación y no puede ser modificado por el técnico.'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data, context={'ticket': ticket})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        to_state = serializer.validated_data['to_state']
        reason = serializer.validated_data.get('reason', '')
        
        if ticket.estado.codigo == "trial":
            if to_state.codigo == "closed":
                return Response({
                    'error': 'No permitido',
                    'message': 'No se puede pasar directamente de "En prueba" a "Finalizado". Debe pasar primero a "En pruebas pendiente de aprobación".'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if to_state.codigo == "trial_pending_approval":
                try:
                    estado_finalizado = Estado.objects.get(codigo='closed')
                except Estado.DoesNotExist:
                    return Response({
                        'error': 'Error del sistema',
                        'message': 'El estado "Finalizado" no está configurado en el sistema.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                estado_anterior = ticket.estado
                ticket.estado = to_state
                ticket.save(update_fields=['estado'])
                
                StateChangeRequest.objects.create(
                    ticket=ticket,
                    requested_by=user,
                    from_state=estado_anterior,
                    to_state=to_state,
                    status=StateChangeRequest.Status.APPROVED,
                    approved_by=user,
                    approved_at=timezone.now(),
                    reason=reason or "Solicitud de finalización"
                )
                
                state_request = StateChangeRequest.objects.create(
                    ticket=ticket,
                    requested_by=user,
                    from_state=estado_anterior,
                    to_state=estado_finalizado,
                    status=StateChangeRequest.Status.PENDING,
                    reason=reason
                )
                
                try:
                    NotificationService.enviar_solicitud_cambio_estado(state_request)
                except Exception as e:
                    logger.error(f"Error enviando notificación de solicitud de finalización: {e}")
                
                return Response({
                    'message': 'El ticket pasó a "En pruebas pendiente de aprobación" y se creó la solicitud de finalización.',
                    'ticket_id': ticket.pk,
                    'new_state': to_state.nombre,
                    'request_id': state_request.id,
                    'status': 'pending_approval'
                }, status=status.HTTP_200_OK)

        if to_state.es_final:
            state_request = StateChangeRequest.objects.create(
                ticket=ticket,
                requested_by=user,
                from_state=ticket.estado,
                to_state=to_state,
                reason=reason
            )
            NotificationService.enviar_solicitud_cambio_estado(state_request)
            return Response({
                'message': 'El estado final requiere validación del administrador, solicitud enviada correctamente.',
                'request_id': state_request.id,
                'status': 'pending_approval',
                'to_state': to_state.nombre
            }, status=status.HTTP_202_ACCEPTED)

        estado_anterior = ticket.estado
        ticket.estado = to_state
        ticket.save()
        
        StateChangeRequest.objects.create(
            ticket=ticket,
            requested_by=user,
            from_state=estado_anterior,
            to_state=to_state,
            status=StateChangeRequest.Status.APPROVED,
            approved_by=user,
            approved_at=timezone.now(),
            reason=reason or "Cambio de estado directo"
        )

        return Response({
            'message': 'Estado actualizado correctamente.',
            'ticket_id': ticket.pk,
            'new_state': to_state.nombre
        }, status=status.HTTP_200_OK)


class TestingApprovalAV(UpdateAPIView):
    """
    Vista para que el administrador apruebe o rechace las pruebas de un ticket.
    """
    permission_classes = [IsAdmin]
    serializer_class = StateApprovalSerializer
    http_method_names = ['patch', 'post', 'options', 'head']

    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)

    def _get_user(self, request):
        user_document = request.query_params.get('user_document')
        if user_document:
            try:
                return User.objects.get(document=user_document)
            except User.DoesNotExist:
                return None
        return getattr(request, 'user', None)

    def _process(self, request, *args, **kwargs):
        ticket = self.get_object()
        user = self._get_user(request)

        if not user or not user.is_authenticated or user.role != User.Role.ADMIN:
            return Response(
                {
                    "error": "No autorizado",
                    "message": "Debe autenticarse como administrador para aprobar/rechazar pruebas."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Validar que el ticket esté en estado "En pruebas pendiente de aprobación"
        if ticket.estado.codigo != "trial_pending_approval":
            return Response(
                {
                    "error": "estado_invalido",
                    "message": "El ticket no está en estado 'En pruebas pendiente de aprobación'."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        estado_anterior = ticket.estado
        now = timezone.now()

        if action == "approve":
            # Pasar de "En pruebas pendiente de aprobación" a "Finalizado"
            estado_final = get_object_or_404(Estado, codigo="closed")
            
            # Crear StateChangeRequest para la timeline
            StateChangeRequest.objects.create(
                ticket=ticket,
                requested_by=user,
                from_state=estado_anterior,
                to_state=estado_final,
                status=StateChangeRequest.Status.APPROVED,
                approved_by=user,
                approved_at=now,
                reason="Pruebas aprobadas por administrador"
            )
            
            ticket.estado = estado_final
            ticket.save(update_fields=["estado"])

            # Notificar que el ticket fue finalizado
            NotificationService.enviar_ticket_finalizado(ticket)

            return Response(
                {
                    "message": "Pruebas aprobadas, el ticket ha sido finalizado.",
                    "ticket": TicketSerializer(ticket).data
                },
                status=status.HTTP_200_OK
            )

        # action == "reject": volver a "En reparación"
        estado_reparacion = get_object_or_404(Estado, codigo="in_repair")
        
        # Crear StateChangeRequest para la timeline
        StateChangeRequest.objects.create(
            ticket=ticket,
            requested_by=user,
            from_state=estado_anterior,
            to_state=estado_reparacion,
            status=StateChangeRequest.Status.APPROVED,
            approved_by=user,
            approved_at=now,
            reason="Pruebas rechazadas por administrador"
        )
        
        ticket.estado = estado_reparacion
        ticket.save(update_fields=["estado"])

        # Notificar que el estado cambió de En pruebas a En reparación
        NotificationService.enviar_notificacion_estado_cambiado(ticket, estado_anterior.nombre)

        return Response(
            {
                "message": "Pruebas rechazadas, el ticket vuelve a reparación.",
                "ticket": TicketSerializer(ticket).data
            },
            status=status.HTTP_200_OK
        )

    def patch(self, request, *args, **kwargs):
        return self._process(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._process(request, *args, **kwargs)


class PendingApprovalsAV(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = PendingApprovalSerializer
    
    def get_queryset(self):
        return StateChangeRequest.objects.filter(
            status=StateChangeRequest.Status.PENDING
        ).select_related('ticket', 'requested_by', 'from_state', 'to_state').order_by('-created_at')
    
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Para clientes, usar siempre el usuario autenticado por seguridad
        if self.request.user.role == User.Role.CLIENT:
            return Ticket.objects.filter(cliente=self.request.user)
        
        # Para admin y técnico, permitir consultar por user_document o usar el usuario autenticado
        user_document = self.request.query_params.get('user_document')
        
        if user_document and user_document.strip():
            try:
                user = User.objects.get(document=user_document)
            except User.DoesNotExist:
                return Ticket.objects.none()
        else:
            # Si no se proporciona user_document, usar el usuario autenticado
            user = self.request.user

        if user.role == User.Role.TECH:
            return Ticket.objects.filter(tecnico=user)
        elif user.role == User.Role.ADMIN:
            return Ticket.objects.all()
        elif user.role == User.Role.CLIENT:
            return Ticket.objects.filter(cliente=user)
        
        return Ticket.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        if not queryset.exists():
            return Response({
                'message': 'No tienes tickets registrados.'
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'message': 'Lista de tickets',
            'total_tickets': queryset.count(),
            'tickets': serializer.data
        }, status=status.HTTP_200_OK)


class TicketTimelineAV(RetrieveAPIView):
    permission_classes = [IsClient]
    serializer_class = TicketTimelineSerializer

    def get_object(self):
        return get_object_or_404(Ticket, pk=self.kwargs.get('ticket_id'))

    def retrieve(self, request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or user.role != User.Role.CLIENT:
            return Response({
                'error': 'No autenticado',
                'message': 'Debe autenticarse como cliente para consultar el timeline de tickets.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        ticket = self.get_object()
        if ticket.cliente != user:
            return Response({
                'error': 'Sin permisos',
                'message': 'El ticket no pertenece al cliente.'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'ticket_id': ticket.pk,
            'estado_actual': ticket.estado.nombre,
            'timeline': self._build_timeline(ticket)
        }, status=status.HTTP_200_OK)

    def _build_timeline(self, ticket):
        estados_visitados = []
        
        try:
            estado_inicial = Estado.objects.get(id=1)
        except Estado.DoesNotExist:
            estado_inicial = ticket.estado
        
        estados_visitados.append({
            'estado_id': estado_inicial.id,
            'estado_nombre': estado_inicial.nombre,
            'fecha': ticket.creado_en
        })
        
        approved_changes = StateChangeRequest.objects.filter(
            ticket=ticket,
            status=StateChangeRequest.Status.APPROVED
        ).select_related('from_state', 'to_state').order_by('approved_at')
        
        estado_actual_reconstruido = estado_inicial
        
        for cambio in approved_changes:
            if estado_actual_reconstruido.id < cambio.from_state.id:
                for estado_id in range(estado_actual_reconstruido.id + 1, cambio.from_state.id + 1):
                    try:
                        estado_intermedio = Estado.objects.get(id=estado_id)
                        tiempo_entre = (cambio.approved_at - ticket.creado_en).total_seconds()
                        estados_totales = cambio.from_state.id - estado_actual_reconstruido.id
                        if estados_totales > 0:
                            tiempo_por_estado = tiempo_entre / estados_totales
                            segundos_ajuste = (estado_id - estado_actual_reconstruido.id) * tiempo_por_estado
                            fecha_estado = ticket.creado_en + timezone.timedelta(seconds=segundos_ajuste)
                        else:
                            fecha_estado = cambio.approved_at
                        
                        estados_visitados.append({
                            'estado_id': estado_intermedio.id,
                            'estado_nombre': estado_intermedio.nombre,
                            'fecha': fecha_estado
                        })
                        estado_actual_reconstruido = estado_intermedio
                    except Estado.DoesNotExist:
                        pass
            
            estados_visitados.append({
                'estado_id': cambio.to_state.id,
                'estado_nombre': cambio.to_state.nombre,
                'fecha': cambio.approved_at
            })
            estado_actual_reconstruido = cambio.to_state
        
        if ticket.estado.codigo == "trial_pending_approval":
            pending_change = StateChangeRequest.objects.filter(
                ticket=ticket,
                status=StateChangeRequest.Status.PENDING,
                from_state__codigo="trial"
            ).first()
            if pending_change:
                estados_visitados.append({
                    'estado_id': ticket.estado.id,
                    'estado_nombre': ticket.estado.nombre,
                    'fecha': pending_change.created_at
                })
                estado_actual_reconstruido = ticket.estado
        
        if estado_actual_reconstruido.id != ticket.estado.id:
            if estado_actual_reconstruido.id < ticket.estado.id:
                tiempo_total = (ticket.actualizado_en - ticket.creado_en).total_seconds()
                estados_totales = ticket.estado.id - estado_actual_reconstruido.id
                for estado_id in range(estado_actual_reconstruido.id + 1, ticket.estado.id + 1):
                    try:
                        estado_intermedio = Estado.objects.get(id=estado_id)
                        if estados_totales > 0:
                            tiempo_por_estado = tiempo_total / estados_totales
                            segundos_ajuste = (estado_id - estado_actual_reconstruido.id) * tiempo_por_estado
                            fecha_estado = ticket.creado_en + timezone.timedelta(seconds=segundos_ajuste)
                        else:
                            fecha_estado = ticket.actualizado_en
                        
                        estados_visitados.append({
                            'estado_id': estado_intermedio.id,
                            'estado_nombre': estado_intermedio.nombre,
                            'fecha': fecha_estado
                        })
                    except Estado.DoesNotExist:
                        pass
            else:
                estados_visitados.append({
                    'estado_id': ticket.estado.id,
                    'estado_nombre': ticket.estado.nombre,
                    'fecha': ticket.actualizado_en
                })
        
        estados_visitados.sort(key=lambda x: x['fecha'] or timezone.now())
        
        timeline = []
        for estado_info in estados_visitados:
            fecha_completa = estado_info['fecha']
            timeline.append({
                'estado_id': estado_info['estado_id'],
                'estado': estado_info['estado_nombre'],
                'fecha': fecha_completa.strftime('%Y-%m-%d') if fecha_completa else None,
                'hora': fecha_completa.strftime('%H:%M:%S') if fecha_completa else None
            })
        
        return timeline
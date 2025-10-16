from django.shortcuts import render, get_object_or_404
from tickets.models import Ticket, Estado
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from tickets.serializers import TicketSerializer, EstadoSerializer
from notifications.signals import enviar_solicitud_finalizacion
import logging

logger = logging.getLogger(__name__)

class TicketAV(APIView):
    """
    Vista para crear y listar tickets.
    Las notificaciones se envían automáticamente via signals.
    """

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save()
            logger.info(f"Ticket #{ticket.pk} creado exitosamente")
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    def get(self, request):
        tickets = Ticket.objects.all().select_related('cliente', 'tecnico', 'estado')
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data, status=200)
    
class EstadoAV(APIView):
    """Vista para listar estados disponibles."""
    
    queryset = Estado.objects.all().order_by("nombre")
    serializer_class = EstadoSerializer
    
    def get(self, request):
        estados = Estado.objects.filter(es_activo=True).order_by("nombre")
        serializer = EstadoSerializer(estados, many=True)
        return Response(serializer.data, status=200)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def ticket_detail(request, ticket_id):
    """
    Vista para obtener, actualizar o modificar un ticket específico.
    """
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'GET':
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        # Verificar permisos básicos
        user = request.user
        
        # Solo el cliente, técnico asignado o administrador pueden modificar
        if not (ticket.cliente == user or ticket.tecnico == user or user.role == 'ADMIN'):
            return Response(
                {'error': 'No tienes permisos para modificar este ticket.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = request.method == 'PATCH'
        serializer = TicketSerializer(ticket, data=request.data, partial=partial)
        
        if serializer.is_valid():
            ticket_actualizado = serializer.save()
            logger.info(f"Ticket #{ticket_actualizado.pk} actualizado por {user.email}")
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_ticket_completion(request, ticket_id):
    """
    Permite al técnico solicitar la finalización de un ticket.
    Envía notificación al administrador.
    """
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    user = request.user
    
    # Solo el técnico asignado puede solicitar finalización
    if ticket.tecnico != user:
        return Response(
            {'error': 'Solo el técnico asignado puede solicitar la finalización.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Verificar que el ticket no esté ya finalizado
    if ticket.estado.codigo == 'finalizado':
        return Response(
            {'error': 'El ticket ya está finalizado.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Enviar solicitud de finalización
        resultados = enviar_solicitud_finalizacion(ticket)
        
        if resultados.get('errores'):
            logger.warning(f"Errores enviando solicitud de finalización: {resultados['errores']}")
            return Response(
                {'error': 'Error enviando solicitud de finalización.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'Solicitud de finalización enviada exitosamente.',
            'notifications_sent': resultados.get('notificaciones_internas', 0),
            'emails_sent': resultados.get('emails_enviados', 0)
        })
        
    except Exception as e:
        logger.error(f"Error en solicitud de finalización: {e}")
        return Response(
            {'error': 'Error interno del servidor.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_ticket_completion(request, ticket_id):
    """
    Permite al administrador aprobar la finalización de un ticket.
    Cambia el estado a 'finalizado' y envía notificaciones.
    """
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    user = request.user
    
    # Solo administradores pueden aprobar finalización
    if user.role != 'ADMIN':
        return Response(
            {'error': 'Solo los administradores pueden aprobar la finalización.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Verificar que el ticket no esté ya finalizado
    if ticket.estado.codigo == 'finalizado':
        return Response(
            {'error': 'El ticket ya está finalizado.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Obtener estado finalizado
        estado_finalizado = Estado.objects.get(codigo='finalizado')
        
        # Actualizar el ticket
        ticket.estado = estado_finalizado
        ticket.save()
        
        logger.info(f"Ticket #{ticket.pk} finalizado por administrador {user.email}")
        
        return Response({
            'message': 'Ticket finalizado exitosamente.',
            'ticket_id': ticket.pk,
            'estado': ticket.estado.nombre
        })
        
    except Estado.DoesNotExist:
        return Response(
            {'error': 'Estado "finalizado" no encontrado en el sistema.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"Error finalizando ticket: {e}")
        return Response(
            {'error': 'Error interno del servidor.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
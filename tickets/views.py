from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from tickets.models import Ticket, Estado
from tickets.serializers import TicketSerializer, EstadoSerializer, LeastBusyTechnicianSerializer, ChangeTechnicianSerializer


class TicketAV(ListCreateAPIView):

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

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
        
        if data['email']:
            return Response(data)
        else:
            return Response(data, status=status.HTTP_404_NOT_FOUND)

class ChangeTechnicianAV(UpdateAPIView):
    
    serializer_class = ChangeTechnicianSerializer
    
    def get_object(self):
        ticket_id = self.kwargs.get('ticket_id')
        return get_object_or_404(Ticket, pk=ticket_id)
    
    def put(self, request, *args, **kwargs):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            new_technician = serializer.validated_data['documento_tecnico']
            ticket.tecnico = new_technician
            ticket.save()
            
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
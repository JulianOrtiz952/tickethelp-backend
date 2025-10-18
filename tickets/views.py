from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework import status
from rest_framework.response import Response
from tickets.models import Ticket, Estado
from tickets.serializers import TicketSerializer, EstadoSerializer, LeastBusyTechnicianSerializer


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
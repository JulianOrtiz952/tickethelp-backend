from rest_framework.generics import ListCreateAPIView
from rest_framework import status
from rest_framework.response import Response

from tickets.models import Ticket, Estado
from tickets.serializers import TicketSerializer, EstadoSerializer


class TicketAV(ListCreateAPIView):

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

class EstadoAV(ListCreateAPIView):

    queryset = Estado.objects.all().order_by("nombre")
    serializer_class = EstadoSerializer
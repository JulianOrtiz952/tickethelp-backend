from django.shortcuts import render
from tickets.models import Ticket, Estado
from rest_framework.views import APIView
from tickets.serializers import TicketSerializer, EstadoSerializer
from rest_framework.response import Response

class TicketAV(APIView):

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    def get(self, request):
        ticket = Ticket.objects.all()
        serializer = TicketSerializer(ticket, many=True)
        return Response(serializer.data, status=200)
    
class EstadoAV(APIView):

    queryset = Estado.objects.all().order_by("nombre")
    serializer_class = EstadoSerializer
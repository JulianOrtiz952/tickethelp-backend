from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from tickets.models import Ticket
from tickets.permissions import IsAdmin
from .serializers import GeneralStatsSerializer


class GeneralStatsView(APIView):
    """
    Vista para obtener estadísticas generales del sistema.
    Solo accesible para administradores.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        """
        Retorna las estadísticas generales del sistema:
        - Cantidad total de tickets con estado "Open"
        - Cantidad total de tickets con estado "closed" (Finalizado)
        
        Returns:
            Responde con la cantidad de tickets abiertos y finalizados
        """
        # Contar tickets con estado "Open"
        tickets_open_count = Ticket.objects.filter(estado__codigo='open').count()
        
        # Contar tickets con estado "closed" (Finalizado)
        tickets_finalizados_count = Ticket.objects.filter(estado__codigo='closed').count()
        
        # Serializar y retornar los datos
        stats_data = {
            'tickets_abiertos': tickets_open_count,
            'tickets_finalizados': tickets_finalizados_count
        }
        
        serializer = GeneralStatsSerializer(stats_data)
        
        return Response(serializer.data, status=status.HTTP_200_OK) 

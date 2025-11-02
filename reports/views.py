from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from tickets.models import Ticket
from tickets.permissions import IsAdmin
from .serializers import GeneralStatsSerializer, TechnicianPerformanceSerializer

User = get_user_model()


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


class TechnicianPerformanceRankingView(APIView):
    """
    Vista para obtener el ranking de desempeño de técnicos.
    Calcula el total de tickets resueltos por cada técnico y su porcentaje de éxito,
    basado en los tickets asignados el mes anterior.
    Solo accesible para administradores.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        """
        Calcula y retorna el ranking de desempeño de técnicos basado en:
        - Tickets asignados el mes anterior
        - Tickets finalizados exitosamente (estado "closed")
        - Porcentaje de éxito
        
        Returns:
            Responde con el ranking de técnicos ordenado por porcentaje de éxito
        """
        # Calcular el rango de fechas del mes anterior
        hoy = timezone.now()
        primer_dia_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calcular el primer día del mes anterior
        if primer_dia_mes_actual.month == 1:
            primer_dia_mes_anterior = primer_dia_mes_actual.replace(year=primer_dia_mes_actual.year - 1, month=12, day=1)
        else:
            primer_dia_mes_anterior = primer_dia_mes_actual.replace(month=primer_dia_mes_actual.month - 1, day=1)
        
        # Calcular el último día del mes anterior (un día antes del primer día del mes actual)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(seconds=1)
        
        # Obtener todos los técnicos activos
        tecnicos = User.objects.filter(role=User.Role.TECH, is_active=True)
        
        ranking_data = []
        
        for tecnico in tecnicos:
            # Tickets asignados al técnico el mes anterior
            tickets_asignados = Ticket.objects.filter(
                tecnico=tecnico,
                creado_en__gte=primer_dia_mes_anterior,
                creado_en__lte=ultimo_dia_mes_anterior
            )
            
            tickets_asignados_count = tickets_asignados.count()
            
            # Tickets resueltos exitosamente (estado "closed") el mes anterior
            tickets_resueltos_count = tickets_asignados.filter(
                estado__codigo='closed'
            ).count()
            
            # Calcular porcentaje de éxito
            if tickets_asignados_count > 0:
                porcentaje_exito = (tickets_resueltos_count / tickets_asignados_count) * 100
            else:
                porcentaje_exito = 0.0
            
            ranking_data.append({
                'nombre_completo': f"{tecnico.first_name} {tecnico.last_name}".strip() or tecnico.email,
                'tickets_asignados': tickets_asignados_count,
                'tickets_resueltos': tickets_resueltos_count,
                'porcentaje_exito': round(porcentaje_exito, 2)
            })
        
        # Ordenar por porcentaje de éxito (descendente), luego por tickets resueltos
        ranking_data.sort(
            key=lambda x: (x['porcentaje_exito'], x['tickets_resueltos']),
            reverse=True
        )
        
        # Serializar los datos
        serializer = TechnicianPerformanceSerializer(ranking_data, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
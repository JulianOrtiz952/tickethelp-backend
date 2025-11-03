from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from tickets.models import Ticket
from tickets.permissions import IsAdmin
from .serializers import GeneralStatsSerializer, TechnicianPerformanceSerializer, ActiveClientsEvolutionSerializer

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
        
        # Calcular el último día del mes anterior (un segundo antes del primer día del mes actual)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(seconds=1)
        
        # Agregación por técnico en una sola consulta
        tickets_mes_anterior = (
            Ticket.objects.filter(
                tecnico__role=User.Role.TECH,
                tecnico__is_active=True,
                creado_en__gte=primer_dia_mes_anterior,
                creado_en__lte=ultimo_dia_mes_anterior
            )
            .select_related('tecnico')
            .values('tecnico', 'tecnico__first_name', 'tecnico__last_name', 'tecnico__email')
            .annotate(
                tickets_asignados=Count('id'),
                tickets_resueltos=Count('id', filter=Q(estado__codigo='closed')),
            )
        )

        ranking_data = []
        for row in tickets_mes_anterior:
            asignados = row['tickets_asignados'] or 0
            resueltos = row['tickets_resueltos'] or 0
            porcentaje = (resueltos / asignados * 100.0) if asignados > 0 else 0.0
            nombre_completo = f"{(row['tecnico__first_name'] or '').strip()} {(row['tecnico__last_name'] or '').strip()}".strip()
            if not nombre_completo:
                nombre_completo = row.get('tecnico__email') or ''
            ranking_data.append({
                'nombre_completo': nombre_completo,
                'tickets_asignados': asignados,
                'tickets_resueltos': resueltos,
                'porcentaje_exito': round(porcentaje, 2)
            })

        # Ordenar en memoria por porcentaje y resueltos
        ranking_data.sort(key=lambda x: (x['porcentaje_exito'], x['tickets_resueltos']), reverse=True)

        # Serializar los datos
        serializer = TechnicianPerformanceSerializer(ranking_data, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActiveClientsEvolutionView(APIView):
    """
    Evolución anual de clientes activos: clientes únicos por mes con al menos un ticket 'open'.
    Solo accesible para administradores.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        # Año solicitado o actual
        year_param = request.query_params.get('year')
        try:
            year = int(year_param) if year_param else timezone.now().year
        except ValueError:
            return Response({"detail": "Parámetro 'year' inválido"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Rango anual
        inicio_anio = datetime(year, 1, 1, 0, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        inicio_anio_siguiente = datetime(year + 1, 1, 1, 0, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        fin_anio = inicio_anio_siguiente - timedelta(seconds=1)
        
        # Query base para el año
        qs_anual = Ticket.objects.filter(
            estado__codigo='open',
            creado_en__gte=inicio_anio,
            creado_en__lte=fin_anio,
            cliente__isnull=False,
        )

        # Total único de clientes en el año con una sola consulta
        total_clientes = qs_anual.values('cliente').distinct().count()

        # Conteo mensual de clientes únicos en una sola pasada usando TruncMonth
        mensual_counts = (
            qs_anual
            .annotate(month=TruncMonth('creado_en'))
            .values('month')
            .annotate(total=Count('cliente', distinct=True))
        )

        # Inicializar todos los meses en 0 y completar con resultados
        mensual = {f"{m:02d}": 0 for m in range(1, 13)}
        for row in mensual_counts:
            month = row['month']
            if month and month.year == year:
                mensual[f"{month.month:02d}"] = row['total']
        
        data = {
            'year': year,
            'total_clientes': total_clientes,
            'mensual': mensual,
        }
        serializer = ActiveClientsEvolutionSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, Coalesce
from django.db.models.functions.datetime import ExtractHour, ExtractWeekDay
from tickets.models import Ticket, StateChangeRequest
from tickets.permissions import IsAdmin
from .serializers import (
    GeneralStatsSerializer,
    TechnicianPerformanceSerializer,
    ActiveClientsEvolutionSerializer,
    ActivityHeatmapSerializer,
)

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
        tickets_open_count = Ticket.objects.filter(estado__codigo='open').count()
        tickets_finalizados_count = Ticket.objects.filter(estado_id=5).count()
        stats_data = {
            'tickets_abiertos': tickets_open_count,
            'tickets_finalizados': tickets_finalizados_count
        }
        serializer = GeneralStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TechnicianPerformanceRankingView(APIView):
    """
    Ranking de desempeño de técnicos basado en el mes anterior.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        hoy = timezone.now()
        primer_dia_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if primer_dia_mes_actual.month == 1:
            primer_dia_mes_anterior = primer_dia_mes_actual.replace(year=primer_dia_mes_actual.year - 1, month=12, day=1)
        else:
            primer_dia_mes_anterior = primer_dia_mes_actual.replace(month=primer_dia_mes_actual.month - 1, day=1)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(seconds=1)

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
            nombre_completo = f"{(row['tecnico__first_name'] or '').strip()} {(row['tecnico__last_name'] or '').strip()}".strip() or (row.get('tecnico__email') or '')
            ranking_data.append({
                'nombre_completo': nombre_completo,
                'tickets_asignados': asignados,
                'tickets_resueltos': resueltos,
                'porcentaje_exito': round(porcentaje, 2)
            })

        ranking_data.sort(key=lambda x: (x['porcentaje_exito'], x['tickets_resueltos']), reverse=True)
        serializer = TechnicianPerformanceSerializer(ranking_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActiveClientsEvolutionView(APIView):
    """
    Evolución anual de clientes activos: clientes únicos por mes con al menos un ticket 'open'.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        year_param = request.query_params.get('year')
        try:
            year = int(year_param) if year_param else timezone.now().year
        except ValueError:
            return Response({"detail": "Parámetro 'year' inválido"}, status=status.HTTP_400_BAD_REQUEST)

        inicio_anio = datetime(year, 1, 1, 0, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        inicio_anio_siguiente = datetime(year + 1, 1, 1, 0, 0, 0, 0, tzinfo=timezone.get_current_timezone())
        fin_anio = inicio_anio_siguiente - timedelta(seconds=1)

        qs_anual = Ticket.objects.filter(
            estado__codigo='open',
            creado_en__gte=inicio_anio,
            creado_en__lte=fin_anio,
            cliente__isnull=False,
        )

        total_clientes = qs_anual.values('cliente').distinct().count()
        mensual_counts = (
            qs_anual
            .annotate(month=TruncMonth('creado_en'))
            .values('month')
            .annotate(total=Count('cliente', distinct=True))
        )

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


class ActivityHeatmapView(APIView):
    """
    Mapa de calor de actividad de cambios de estado.
    Cuenta cambios por día de la semana (Lun..Dom) y franja horaria (00-06,06-12,12-18,18-24).
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        # Filtro opcional por año y mes
        tz = timezone.get_current_timezone()
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        # Timestamp de evento: aprobado si existe, si no creación
        timestamp = Coalesce('approved_at', 'created_at')

        qs = StateChangeRequest.objects.all()
        if year:
            try:
                year_int = int(year)
            except ValueError:
                return Response({"detail": "Parámetro 'year' inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            year_int = None

        if month:
            try:
                month_int = int(month)
                if month_int < 1 or month_int > 12:
                    raise ValueError
            except ValueError:
                return Response({"detail": "Parámetro 'month' inválido"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            month_int = None

        # Aplicar rango temporal si se especifica
        if year_int:
            start = datetime(year_int, month_int or 1, 1, tzinfo=tz)
            if month_int:
                if month_int == 12:
                    end = datetime(year_int + 1, 1, 1, tzinfo=tz) - timedelta(seconds=1)
                else:
                    end = datetime(year_int, month_int + 1, 1, tzinfo=tz) - timedelta(seconds=1)
            else:
                end = datetime(year_int + 1, 1, 1, tzinfo=tz) - timedelta(seconds=1)
            qs = qs.filter(approved_at__isnull=False, approved_at__gte=start, approved_at__lte=end) | qs.filter(approved_at__isnull=True, created_at__gte=start, created_at__lte=end)

        # Agregar por día de la semana y hora
        aggregated = (
            qs
            .annotate(event_ts=timestamp)
            .annotate(weekday=ExtractWeekDay('event_ts'), hour=ExtractHour('event_ts'))
            .values('weekday', 'hour')
            .annotate(total=Count('id'))
        )

        # Matriz 4x7 (filas: franjas, cols: días) inicializada en 0
        ranges = [(0, 6), (6, 12), (12, 18), (18, 24)]
        labels_ranges = ['00-06', '06-12', '12-18', '18-24']
        labels_days = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        matrix = [[0 for _ in range(7)] for _ in range(4)]

        max_value = 0
        for row in aggregated:
            # ExtractWeekDay: 1=Domingo ... 7=Sábado (según backend). Normalizamos a Lun=0..Dom=6.
            weekday = row['weekday']
            hour = row['hour']
            total = row['total']

            # Convertimos: 1=Dom -> 6; 2=Lun -> 0; ... 7=Sáb -> 5
            col = (weekday - 2) % 7

            # Determinar fila por franja
            if hour < 6:
                row_idx = 0
            elif hour < 12:
                row_idx = 1
            elif hour < 18:
                row_idx = 2
            else:
                row_idx = 3

            matrix[row_idx][col] += total
            if matrix[row_idx][col] > max_value:
                max_value = matrix[row_idx][col]

        payload = {
            'days': labels_days,
            'ranges': labels_ranges,
            'matrix': matrix,
            'max_value': int(max_value),
        }
        serializer = ActivityHeatmapSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
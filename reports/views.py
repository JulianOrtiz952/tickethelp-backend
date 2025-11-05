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
from django.db.models import Avg, F, OuterRef, Subquery, ExpressionWrapper, DurationField

from .serializers import (
    GeneralStatsSerializer,
    TechnicianPerformanceSerializer,
    ActiveClientsEvolutionSerializer,
    ActivityHeatmapSerializer,
    AverageResolutionTimeSerializer
)

User = get_user_model()


class GeneralStatsView(APIView):
    """
    Vista para obtener estadísticas generales del sistema.
    Solo accesible para administradores.
    """
    permission_classes = [IsAdmin]
    FINAL_STATE_ID = 5

    def get(self, request):
        # Conteos
        total_tickets = Ticket.objects.count()
        tickets_finalizados_count = Ticket.objects.filter(estado_id=self.FINAL_STATE_ID).count()
        tickets_abiertos_count = Ticket.objects.exclude(estado_id=self.FINAL_STATE_ID).count()

        # Promedio de éxito (sobre la totalidad de tickets)
        promedio_exito = round((tickets_finalizados_count / total_tickets) * 100.0, 2) if total_tickets else 0.0

        stats_data = {
            'tickets_abiertos': tickets_abiertos_count,
            'tickets_finalizados': tickets_finalizados_count,
            'promedio_exito': promedio_exito,
        }
        serializer = GeneralStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TechnicianPerformanceRankingView(APIView):
    """
    Ranking de desempeño (histórico):
    - tickets_asignados: total histórico por técnico.
    - tickets_resueltos: total histórico en estado_id=5 por técnico.
    - porcentaje_exito: resueltos/asignados * 100.
    - Top 5: primero por resueltos DESC, luego asignados DESC.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Count, Q

        FINAL_STATE_ID = 5
        LIMIT = int(request.query_params.get('limit', 5))

        # Tomamos TODOS los técnicos activos
        qs = (
            User.objects.filter(role=User.Role.TECH, is_active=True)
            .annotate(
                tickets_asignados=Count('tickets_asignados', distinct=True),
                tickets_resueltos=Count(
                    'tickets_asignados',
                    filter=Q(tickets_asignados__estado_id=FINAL_STATE_ID),
                    distinct=True
                ),
            )
        )

        # Normalizamos y calculamos % éxito
        rows = []
        for u in qs:
            asign = u.tickets_asignados or 0
            res   = u.tickets_resueltos or 0
            pct   = round((res / asign) * 100.0, 2) if asign > 0 else 0.0
            nombre = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip() or (u.email or '')
            rows.append({
                'tecnico_id': u.pk,
                'nombre_completo': nombre,
                'tickets_asignados': asign,
                'tickets_resueltos': res,
                'porcentaje_exito': pct,
            })

        # Orden: más resueltos, luego más asignados
        rows.sort(key=lambda x: (x['tickets_resueltos'], x['tickets_asignados']), reverse=True)

        # Asegura máximo LIMIT
        top = rows[:LIMIT]

        # Formato final
        payload = [
            {
                "nombre_completo": x['nombre_completo'],
                "tickets_asignados": x['tickets_asignados'],
                "tickets_resueltos": x['tickets_resueltos'],
                "porcentaje_exito": x['porcentaje_exito'],
            }
            for x in top
        ]
        return Response(payload, status=status.HTTP_200_OK)




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

class AverageResolutionTimeView(APIView):
    """
    Tiempo promedio de solución:
    - Considera tickets en estado final (id=5).
    - resolved_at = primera aprobación (approved_at) hacia estado 5.
      Si no hay, se toma actualizado_en como respaldo.
    - Promedio = avg(resolved_at - creado_en).
    """
    permission_classes = [IsAdmin]

    FINAL_STATE_ID = 5  # estado "finalizado"

    def get(self, request):
        # Subquery: primer approved_at hacia el estado final
        first_approved_subq = (
            StateChangeRequest.objects
            .filter(
                ticket=OuterRef('pk'),
                to_state_id=self.FINAL_STATE_ID,
                status=StateChangeRequest.Status.APPROVED,
            )
            .order_by('approved_at')
            .values('approved_at')[:1]
        )

        # Tickets finalizados (estado_id=5)
        base_qs = (
            Ticket.objects
            .filter(estado_id=self.FINAL_STATE_ID)
            .annotate(resolved_at=Subquery(first_approved_subq))
        )

        # resolved_at de respaldo: actualizado_en
        base_qs = base_qs.annotate(
            resolved_at_final=Coalesce(F('resolved_at'), F('actualizado_en'))
        )

        # duration = resolved_at_final - creado_en
        duration_expr = ExpressionWrapper(
            F('resolved_at_final') - F('creado_en'),
            output_field=DurationField()
        )

        agg = base_qs.aggregate(
            avg_duration=Avg(duration_expr),
            total=Count('id')
        )

        avg_duration = agg['avg_duration']
        total = agg['total'] or 0

        if not avg_duration or total == 0:
            payload = {
                'promedio_horas': 0.0,
                'promedio_dias': 0.0,
                'tickets_contemplados': 0
            }
            ser = AverageResolutionTimeSerializer(payload)
            return Response(ser.data, status=status.HTTP_200_OK)

        # Convertir a horas/días
        avg_seconds = avg_duration.total_seconds()
        payload = {
            'promedio_horas': round(avg_seconds / 3600.0, 2),
            'promedio_dias': round(avg_seconds / 86400.0, 2),
            'tickets_contemplados': int(total)
        }
        ser = AverageResolutionTimeSerializer(payload)
        return Response(ser.data, status=status.HTTP_200_OK)
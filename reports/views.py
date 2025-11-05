from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Case, When, IntegerField
from django.db.models.functions import TruncMonth, Coalesce, Now
from django.db.models.functions.datetime import ExtractHour, ExtractWeekDay
from tickets.models import Ticket, StateChangeRequest, Estado
from tickets.permissions import IsAdmin
from django.db.models import Avg, F, OuterRef, Subquery, ExpressionWrapper, DurationField

from .serializers import (
    GeneralStatsSerializer,
    TechnicianPerformanceSerializer,
    ActiveClientsEvolutionSerializer,
    ActivityHeatmapSerializer,
    FlowFunnelSerializer,
    FlowFunnelItemSerializer,
    AverageResolutionTimeSerializer,
    TTRPromedioSerializer
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
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Count, Q

        FINAL_STATE_ID = 5
        LIMIT = int(request.query_params.get('limit', 5))

        # Técnicos activos con agregados HISTÓRICOS
        qs = (
            User.objects.filter(role=User.Role.TECH, is_active=True)
            .annotate(
                total_asignados=Count('tickets_asignados', distinct=True),
                total_resueltos=Count(
                    'tickets_asignados',
                    filter=Q(tickets_asignados__estado_id=FINAL_STATE_ID),
                    distinct=True
                ),
            )
        )

        rows = []
        for u in qs:
            asign = u.total_asignados or 0
            res   = u.total_resueltos or 0
            pct   = round((res / asign) * 100.0, 2) if asign > 0 else 0.0
            nombre = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip() or (u.email or '')
            rows.append({
                'tecnico_id': u.pk,
                'nombre_completo': nombre,
                'tickets_asignados': asign,   # ← lo que pides: TODOS los asignados
                'tickets_resueltos': res,     # ← resueltos en estado 5
                'porcentaje_exito': pct,
            })

        # Orden: más resueltos, luego más asignados
        rows.sort(key=lambda x: (x['tickets_resueltos'], x['tickets_asignados']), reverse=True)

        payload = [
            {
                "nombre_completo": x['nombre_completo'],
                "tickets_asignados": x['tickets_asignados'],
                "tickets_resueltos": x['tickets_resueltos'],
                "porcentaje_exito": x['porcentaje_exito'],
            }
            for x in rows[:LIMIT]
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
            estado_id=1,  # 1=open
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

class StateDistributionView(APIView):
    """
    Distribución porcentual de tickets por estado (para gráfico circular).

    Rango de fechas:
      - Si NO se envía: to_date = hoy, from_date = hoy - 30 días.
      - Si se envía: ?from=YYYY-MM-DD&to=YYYY-MM-DD
        * Validar formato de fecha
        * from <= to
        * (to - from) <= 365 días
        * to no puede ser futuro (opcionalmente puedes permitirlo si quieres)

    Cálculo:
      - Considera los tickets con creado_en dentro del rango [from 00:00:00, to 23:59:59].
      - Agrupa por estado y calcula porcentaje = cantidad / total * 100.
      - Si algún estado no tiene tickets en el rango, se devuelve con cantidad=0, porcentaje=0.0
    """
    permission_classes = [IsAdmin]

    MAX_DAYS = 365

    def get(self, request):
        tz = timezone.get_current_timezone()

        # 1) Parseo y validaciones de fechas
        from_str = request.query_params.get('from')
        to_str   = request.query_params.get('to')

        today = timezone.localdate()
        if not to_str and not from_str:
            to_date = today
            from_date = to_date - timedelta(days=30)
        else:
            # Validar formato YYYY-MM-DD
            def parse_date_safe(s, name):
                try:
                    return datetime.strptime(s, "%Y-%m-%d").date()
                except Exception:
                    raise ValueError(f"Parámetro '{name}' inválido. Formato esperado: YYYY-MM-DD")

            try:
                if not from_str or not to_str:
                    return Response(
                        {"detail": "Debe enviar ambos parámetros 'from' y 'to' en formato YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                from_date = parse_date_safe(from_str, "from")
                to_date   = parse_date_safe(to_str, "to")
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            # from <= to
            if from_date > to_date:
                return Response({"detail": "El parámetro 'from' no puede ser mayor que 'to'."},
                                status=status.HTTP_400_BAD_REQUEST)

            # rango <= 365 días
            if (to_date - from_date).days > self.MAX_DAYS:
                return Response({"detail": f"El rango no puede superar {self.MAX_DAYS} días."},
                                status=status.HTTP_400_BAD_REQUEST)

            # to no en el futuro (opcional)
            if to_date > today:
                return Response({"detail": "La fecha 'to' no puede estar en el futuro."},
                                status=status.HTTP_400_BAD_REQUEST)

        # 2) Normalizar a datetimes con zona
        start_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0, tzinfo=tz)
        end_dt   = datetime(to_date.year,   to_date.month,   to_date.day,   23, 59, 59, tzinfo=tz)

        # 3) Traer todos los estados (asumimos 5 en tu sistema)
        estados = list(Estado.objects.all().values('id', 'codigo', 'nombre'))

        # 4) Conteo por estado en el rango
        counts = (
            Ticket.objects
            .filter(creado_en__gte=start_dt, creado_en__lte=end_dt)
            .values('estado_id')
            .annotate(cantidad=Count('id'))
        )
        counts_map = {row['estado_id']: row['cantidad'] for row in counts}
        total = sum(counts_map.values())

        # 5) Construir respuesta con todos los estados (incluyendo los 0)
        items = []
        for e in estados:
            cant = counts_map.get(e['id'], 0)
            pct = round((cant / total) * 100.0, 2) if total > 0 else 0.0
            items.append({
                'estado_codigo': e['codigo'],
                'estado_nombre': e['nombre'],
                'cantidad': int(cant),
                'porcentaje': pct,
            })

        payload = {
            'total': int(total),
            'from_date': from_date,
            'to_date': to_date,
            'items': items
        }

        # Serializar (por seguridad de tipos)
        ser = StateDistributionResponseSerializer(payload)
        return Response(ser.data, status=status.HTTP_200_OK)

class FlowFunnelView(APIView):
    """
    Embudo de flujo: agrupa tickets por estados intermedios (excluye 'open' y finales).
    Retorna totales ordenados según el flujo del proceso.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        # Total de tickets creados (estado "open") como base 100%
        total_tickets_creados = Ticket.objects.filter(estado__codigo='open').count()
        
        # Estados a excluir: "open" (creado) y estados finales (es_final=True)
        estados_intermedios = Estado.objects.exclude(
            codigo='open'
        ).exclude(
            es_final=True
        ).order_by('id')

        # Agregar tickets por estado intermedio
        aggregated = (
            Ticket.objects.filter(estado__in=estados_intermedios)
            .values('estado__id', 'estado__codigo', 'estado__nombre')
            .annotate(total=Count('id'))
            .order_by('estado__id')
        )

        items = []
        for row in aggregated:
            # Calcular porcentaje respecto al total de tickets creados
            porcentaje = (row['total'] / total_tickets_creados * 100.0) if total_tickets_creados > 0 else 0.0
            
            items.append({
                'codigo': row['estado__codigo'],
                'nombre': row['estado__nombre'],
                'porcentaje': round(porcentaje, 2)
            })

        payload = {'items': items}
        serializer = FlowFunnelSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TicketAgingTopView(APIView):
    """
    Top N tickets con más tiempo abiertos (no finalizados).
    - Métrica: Now() - creado_en (duración).
    - Excluye estado_id = 10 (finalizado).
    - Desempate: ID menor.
    - Incluye datos del técnico y del cliente.
    """
    permission_classes = [IsAdmin]
    FINAL_STATE_ID = 10  # según tu requerimiento
    DEFAULT_LIMIT = 10

    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', self.DEFAULT_LIMIT))
            if limit <= 0 or limit > 100:
                limit = self.DEFAULT_LIMIT
        except ValueError:
            limit = self.DEFAULT_LIMIT

        qs = (
            Ticket.objects
            .exclude(estado_id=self.FINAL_STATE_ID)
            .annotate(age=ExpressionWrapper(Now() - F('creado_en'), output_field=DurationField()))
            .select_related('estado', 'tecnico', 'cliente')
            .order_by('-age', 'id')[:limit]
            .values(
                'id', 'titulo', 'creado_en',
                'estado__codigo', 'estado__nombre',
                'age',
                'tecnico__document', 'tecnico__first_name', 'tecnico__last_name', 'tecnico__email',
                'cliente__document', 'cliente__first_name', 'cliente__last_name', 'cliente__email',
            )
        )

        items = []
        for r in qs:
            age = r['age']
            dias = round(age.total_seconds() / 86400.0, 2) if age else 0.0

            # nombres legibles
            t_nombre = f"{(r['tecnico__first_name'] or '').strip()} {(r['tecnico__last_name'] or '').strip()}".strip() or None
            c_nombre = f"{(r['cliente__first_name'] or '').strip()} {(r['cliente__last_name'] or '').strip()}".strip() or None

            items.append({
                'ticket_id': r['id'],
                'titulo': r['titulo'],
                'estado_codigo': r['estado__codigo'],
                'estado_nombre': r['estado__nombre'],
                'creado_en': r['creado_en'],
                'dias': dias,

                'tecnico_id': r['tecnico__document'],
                'tecnico_nombre': t_nombre,
                'tecnico_email': r['tecnico__email'],

                'cliente_id': r['cliente__document'],
                'cliente_nombre': c_nombre,
                'cliente_email': r['cliente__email'],
            })

        ser = TicketAgingItemSerializer(items, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

class ResolutionsByWeekdayView(APIView):
    permission_classes = [IsAdmin]
    FINAL_STATE_ID = 5

    def get(self, request):
        from django.db.models.functions import ExtractWeekDay
        from django.db.models import Count, Q

        # 1) Cambios aprobados hacia estado final (source principal)
        agg_scr = (
            StateChangeRequest.objects
            .filter(
                to_state_id=self.FINAL_STATE_ID,
                status=StateChangeRequest.Status.APPROVED,
                approved_at__isnull=False,            # ⬅️ evita weekday None
            )
            .annotate(weekday=ExtractWeekDay('approved_at'))
            .values('weekday')
            .annotate(total=Count('id'))
        )
        counts_scr = {row['weekday']: row['total'] for row in agg_scr if row['weekday'] is not None}

        # 2) Tickets en estado final SIN aprobación registrada → respaldo: actualizado_en
        agg_fallback = (
            Ticket.objects
            .filter(
                estado_id=self.FINAL_STATE_ID,
                actualizado_en__isnull=False          # ⬅️ evita weekday None
            )
            .exclude(
                state_requests__to_state_id=self.FINAL_STATE_ID,
                state_requests__status=StateChangeRequest.Status.APPROVED,
                state_requests__approved_at__isnull=False
            )
            .annotate(weekday=ExtractWeekDay('actualizado_en'))
            .values('weekday')
            .annotate(total=Count('id'))
        )
        counts_fb = {row['weekday']: row['total'] for row in agg_fallback if row['weekday'] is not None}

        # 3) Sumar ambos orígenes y mapear a Lun..Dom
        def to_lun_dom_index(wd):
            # Guard: si viene None, no mapeamos
            if wd is None:
                return None
            # ExtractWeekDay: 1=Dom, 2=Lun, ..., 7=Sáb → 0..6 (Lun..Dom)
            return (wd - 2) % 7

        totals_by_idx = [0]*7  # 0=Lun ... 6=Dom
        for k, v in counts_scr.items():
            idx = to_lun_dom_index(k)
            if idx is not None:
                totals_by_idx[idx] += v
        for k, v in counts_fb.items():
            idx = to_lun_dom_index(k)
            if idx is not None:
                totals_by_idx[idx] += v

        payload = {
            'lunes':      int(totals_by_idx[0]),
            'martes':     int(totals_by_idx[1]),
            'miercoles':  int(totals_by_idx[2]),
            'jueves':     int(totals_by_idx[3]),
            'viernes':    int(totals_by_idx[4]),
            'sabado':     int(totals_by_idx[5]),
            'domingo':    int(totals_by_idx[6]),
        }
        ser = WeekdayResolutionCountSerializer(payload)
        return Response(ser.data, status=status.HTTP_200_OK)


class TTRPromedioView(APIView):
    """
    Tiempo Total de Resolución (TTR) promedio:
    - Calcula el TTR promedio global del sistema
    - Calcula el TTR promedio por cada técnico
    - TTR = tiempo desde creación del ticket hasta cierre (estado final)
    - resolved_at = primera aprobación (approved_at) hacia estado 5.
      Si no hay, se toma actualizado_en como respaldo.
    
    Optimizado: Una sola consulta para calcular TTR global y por técnico.
    """
    permission_classes = [IsAdmin]

    FINAL_STATE_ID = 5  # estado "finalizado"

    def get(self, request):
        # Subquery reutilizable: primer approved_at hacia el estado final
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

        # Base queryset: tickets finalizados con duración calculada
        base_qs = (
            Ticket.objects
            .filter(estado_id=self.FINAL_STATE_ID)
            .select_related('tecnico')
            .annotate(
                resolved_at=Subquery(first_approved_subq),
                resolved_at_final=Coalesce(F('resolved_at'), F('actualizado_en')),
                duration=ExpressionWrapper(
                    F('resolved_at_final') - F('creado_en'),
                    output_field=DurationField()
                )
            )
        )

        # === CALCULAR TTR GLOBAL ===
        agg_global = base_qs.aggregate(
            avg_duration=Avg('duration'),
            total=Count('id')
        )

        avg_duration_global = agg_global['avg_duration']
        total_global = agg_global['total'] or 0

        if avg_duration_global and total_global > 0:
            avg_seconds_global = avg_duration_global.total_seconds()
            promedio_global = {
                'promedio_horas': round(avg_seconds_global / 3600.0, 2),
                'promedio_dias': round(avg_seconds_global / 86400.0, 2),
                'tickets_contemplados': total_global
            }
        else:
            promedio_global = {
                'promedio_horas': 0.0,
                'promedio_dias': 0.0,
                'tickets_contemplados': 0
            }

        # === CALCULAR TTR POR TÉCNICO (en una sola consulta agregada) ===
        # Agregar por técnico: solo técnicos con tickets finalizados
        tecnicos_agg = (
            base_qs
            .filter(tecnico__isnull=False)
            .values('tecnico_id', 'tecnico__first_name', 'tecnico__last_name', 'tecnico__email')
            .annotate(
                avg_duration=Avg('duration'),
                total=Count('id')
            )
            .filter(total__gt=0)  # Solo técnicos con tickets
        )

        por_tecnico_list = []
        for row in tecnicos_agg:
            avg_duration_tec = row['avg_duration']
            if avg_duration_tec:
                avg_seconds_tec = avg_duration_tec.total_seconds()
                
                # Construir nombre completo
                first_name = (row['tecnico__first_name'] or '').strip()
                last_name = (row['tecnico__last_name'] or '').strip()
                nombre_completo = f"{first_name} {last_name}".strip()
                if not nombre_completo:
                    nombre_completo = row['tecnico__email'] or f"Usuario {row['tecnico_id']}"

                por_tecnico_list.append({
                    'tecnico_id': row['tecnico_id'],
                    'nombre_completo': nombre_completo,
                    'promedio_horas': round(avg_seconds_tec / 3600.0, 2),
                    'promedio_dias': round(avg_seconds_tec / 86400.0, 2),
                    'tickets_contemplados': row['total']
                })

        # Ordenar por TTR promedio (menor tiempo primero = mejor rendimiento)
        por_tecnico_list.sort(key=lambda x: x['promedio_horas'])

        payload = {
            'promedio_global': promedio_global,
            'por_tecnico': por_tecnico_list
        }

        serializer = TTRPromedioSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
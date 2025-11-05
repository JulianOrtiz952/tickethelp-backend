from rest_framework import serializers


class GeneralStatsSerializer(serializers.Serializer):
    """
    Serializer para las estadísticas generales del sistema.
    Retorna la cantidad de tickets abiertos y cerrados.
    """
    tickets_abiertos = serializers.IntegerField(
        help_text="Cantidad total de tickets que NO están en estado 5"
    )
    tickets_finalizados = serializers.IntegerField(
        help_text="Cantidad total de tickets en estado 5"
    )
    promedio_exito = serializers.FloatField(
        help_text="Porcentaje de éxito = tickets_finalizados / total_tickets * 100"
    )

class TechnicianPerformanceSerializer(serializers.Serializer):
    """
    Serializer para el ranking de desempeño de técnicos.
    Retorna información del técnico y sus estadísticas de resolución.
    """
    nombre_completo = serializers.CharField(help_text="Nombre completo del técnico")
    tickets_asignados = serializers.IntegerField(
        help_text="Total de tickets asignados el mes anterior"
    )
    tickets_resueltos = serializers.IntegerField(
        help_text="Total de tickets resueltos exitosamente el mes anterior"
    )
    porcentaje_exito = serializers.FloatField(
        help_text="Porcentaje de éxito en la resolución de tickets"
    )


class ActiveClientsEvolutionSerializer(serializers.Serializer):
    """
    Evolución anual de clientes activos (con al menos un ticket 'open' en el mes).
    - year: año consultado
    - total_clientes: clientes únicos en todo el año
    - mensual: mapa {"01": 10, ..., "12": 5}
    """
    year = serializers.IntegerField()
    total_clientes = serializers.IntegerField()
    mensual = serializers.DictField(child=serializers.IntegerField(), help_text="Mapa mes->cantidad de clientes únicos")


class ActivityHeatmapSerializer(serializers.Serializer):
    """
    Matriz de heatmap de actividad de cambios de estado.
    - days: etiquetas de días (Lun..Dom)
    - ranges: etiquetas de franjas (00-06,06-12,12-18,18-24)
    - matrix: 4x7 con conteos por [fila=franja][col=día]
    - max_value: máximo en la matriz (para escala)
    """
    days = serializers.ListField(child=serializers.CharField())
    ranges = serializers.ListField(child=serializers.CharField())
    matrix = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()))
    max_value = serializers.IntegerField()

class AverageResolutionTimeSerializer(serializers.Serializer):
    promedio_horas = serializers.FloatField()
    promedio_dias = serializers.FloatField()
    tickets_contemplados = serializers.IntegerField()


class TechnicianTTRSerializer(serializers.Serializer):
    """
    Serializer para TTR promedio de un técnico individual.
    """
    tecnico_id = serializers.IntegerField()
    nombre_completo = serializers.CharField()
    promedio_horas = serializers.FloatField()
    promedio_dias = serializers.FloatField()
    tickets_contemplados = serializers.IntegerField()


class GlobalTTRSerializer(serializers.Serializer):
    """
    Serializer para TTR promedio global.
    """
    promedio_horas = serializers.FloatField()
    promedio_dias = serializers.FloatField()
    tickets_contemplados = serializers.IntegerField()


class TTRPromedioSerializer(serializers.Serializer):
    """
    Serializer para TTR promedio global y por técnico.
    """
    promedio_global = GlobalTTRSerializer(help_text="TTR promedio global")
    por_tecnico = TechnicianTTRSerializer(many=True, help_text="Lista de TTR promedio por cada técnico")


class FlowFunnelItemSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    porcentaje = serializers.FloatField(help_text="Porcentaje respecto al total de tickets creados")


class FlowFunnelSerializer(serializers.Serializer):
    """
    Embudo de flujo: porcentajes por estados intermedios (excluye 'open' y finales).
    items: lista ordenada según flujo del proceso.
    """
    items = FlowFunnelItemSerializer(many=True)


class StateDistributionItemSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    estado_nombre = serializers.CharField()
    cantidad = serializers.IntegerField()
    porcentaje = serializers.FloatField()


class StateDistributionResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    from_date = serializers.DateField() 
    to_date = serializers.DateField()
    items = StateDistributionItemSerializer(many=True)


class TicketAgingItemSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    titulo = serializers.CharField()
    estado_codigo = serializers.CharField()
    estado_nombre = serializers.CharField()
    creado_en = serializers.DateTimeField()
    dias = serializers.FloatField()

    tecnico_id = serializers.CharField(allow_null=True, required=False)
    tecnico_nombre = serializers.CharField(allow_null=True, required=False)
    tecnico_email = serializers.EmailField(allow_null=True, required=False)

    cliente_id = serializers.CharField(allow_null=True, required=False)
    cliente_nombre = serializers.CharField(allow_null=True, required=False)
    cliente_email = serializers.EmailField(allow_null=True, required=False)


class WeekdayResolutionCountSerializer(serializers.Serializer):
    lunes = serializers.IntegerField()
    martes = serializers.IntegerField()
    miercoles = serializers.IntegerField()
    jueves = serializers.IntegerField()
    viernes = serializers.IntegerField()
    sabado = serializers.IntegerField()
    domingo = serializers.IntegerField()

class TTAStateItemSerializer(serializers.Serializer):
    estado_id = serializers.IntegerField()
    estado_codigo = serializers.CharField()
    estado_nombre = serializers.CharField()
    promedio_segundos = serializers.FloatField()
    promedio_horas = serializers.FloatField()
    promedio_dias = serializers.FloatField()
    muestras = serializers.IntegerField()

class TTATotalSerializer(serializers.Serializer):
    tta_segundos = serializers.FloatField()
    tta_horas = serializers.FloatField()
    tta_dias = serializers.FloatField()
    estados_sumados = serializers.IntegerField()
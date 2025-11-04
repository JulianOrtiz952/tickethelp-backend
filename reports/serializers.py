from rest_framework import serializers


class GeneralStatsSerializer(serializers.Serializer):
    """
    Serializer para las estadísticas generales del sistema.
    Retorna la cantidad de tickets abiertos y cerrados.
    """
    tickets_abiertos = serializers.IntegerField(
        help_text="Cantidad total de tickets con estado 'Open'"
    )
    tickets_finalizados = serializers.IntegerField(
        help_text="Cantidad total de tickets con estado 'closed' (Finalizado)"
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
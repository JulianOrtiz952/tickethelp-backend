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


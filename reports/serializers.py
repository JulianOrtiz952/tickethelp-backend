from rest_framework import serializers


class GeneralStatsSerializer(serializers.Serializer):
    """
    Serializer para las estadísticas generales del sistema.
    Retorna la cantidad de tickets abiertos y cerrados.
    """
    tickets_open = serializers.IntegerField(
        help_text="Cantidad total de tickets con estado 'Open'"
    )
    tickets_cerrados = serializers.IntegerField(
        help_text="Cantidad total de tickets con estado 'closed' (Finalizado)"
    )


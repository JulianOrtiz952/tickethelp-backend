from django.test import SimpleTestCase
from reports.serializers import AverageResolutionTimeSerializer

class ReportsSerializerPUTests(SimpleTestCase):
    """
    Pruebas Unitarias (PU) para la estructura de serializers de Reportes.
    Como reports/serializers.py solo define lectura (readonly), validamos 
    que sus capos base acepten y serialicen los datos simulados correctamente.
    """

    def test_average_resolution_time_serializer(self):
        """Verifica que el serializer procesa correctamente floats e ints"""
        data = {
            'promedio_horas': 45.2,
            'promedio_dias': 1.88,
            'tickets_contemplados': 120
        }
        
        serializer = AverageResolutionTimeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['tickets_contemplados'], 120)

    def test_average_resolution_time_invalid_type(self):
        """Verifica que rechace strings en tipos numéricos"""
        data = {
            'promedio_horas': "texto",
            'promedio_dias': 1.88,
            'tickets_contemplados': 120
        }
        
        serializer = AverageResolutionTimeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('promedio_horas', serializer.errors)

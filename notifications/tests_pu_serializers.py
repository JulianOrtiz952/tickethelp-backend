from django.test import TestCase
from notifications.models import NotificationType
from notifications.serializers import CreateNotificationSerializer
from rest_framework.exceptions import ValidationError

class NotificationsSerializerPUTests(TestCase):
    """
    Pruebas Unitarias (PU) aislando las validaciones personalizadas.
    Se requiere TestCase para validar los codigos requeridos contra la DB.
    """

    def setUp(self):
        # Crear datos básicos de Notificación
        self.tipo_alerta = NotificationType.objects.create(
            codigo='alerta', 
            nombre='Alerta de sistema',
            es_activo=True
        )
        self.tipo_inactivo = NotificationType.objects.create(
            codigo='inactivo', 
            nombre='Alerta de sistema apagado',
            es_activo=False
        )

    def test_validate_tipo_codigo_success(self):
        """Verificar que un tipo de notificación creado y activo pase la validación"""
        serializer = CreateNotificationSerializer()
        # validate_tipo_codigo returns the object code if successful
        res = serializer.validate_tipo_codigo('alerta')
        self.assertEqual(res, 'alerta')

    def test_validate_tipo_codigo_inactive_fails(self):
        """Verificar que falle si el tipo de notificación NO está activo"""
        serializer = CreateNotificationSerializer()
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_tipo_codigo('inactivo')
            
        self.assertIn("no encontrado o inactivo", str(ctx.exception))

    def test_validate_tipo_codigo_not_found(self):
        """Verificar que falle la validación si se inventa un código"""
        serializer = CreateNotificationSerializer()
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_tipo_codigo('codigoinventado')
            
        self.assertIn("no encontrado", str(ctx.exception))

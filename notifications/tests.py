from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tickets.models import Ticket, Estado
from .models import Notification, NotificationType

User = get_user_model()


class NotificationModelTest(TestCase):
    """Tests para los modelos de notificaciones."""
    
    def setUp(self):
        self.cliente = User.objects.create_user(
            email='cliente@test.com',
            document='12345678',
            password='testpass123',
            role=User.Role.CLIENT
        )
        
        self.tecnico = User.objects.create_user(
            email='tecnico@test.com',
            document='87654321',
            password='testpass123',
            role=User.Role.TECH
        )
        
        self.estado = Estado.objects.create(
            codigo='abierto',
            nombre='Abierto',
            es_activo=True
        )
        
        self.ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket de prueba',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado
        )
        
        self.notification_type, created = NotificationType.objects.get_or_create(
            codigo='ticket_creado',
            defaults={
                'nombre': 'Ticket Creado',
                'enviar_a_cliente': True
            }
        )
        
        self.notification = Notification.objects.create(
            usuario=self.cliente,
            ticket=self.ticket,
            tipo=self.notification_type,
            titulo='Nuevo Ticket Creado',
            mensaje='Se ha creado un nuevo ticket para su atención.'
        )
    
    def test_notification_creation(self):
        """Test que verifica la creación de una notificación."""
        self.assertEqual(self.notification.usuario, self.cliente)
        self.assertEqual(self.notification.ticket, self.ticket)
        self.assertEqual(self.notification.tipo, self.notification_type)
        self.assertEqual(self.notification.titulo, 'Nuevo Ticket Creado')
        self.assertEqual(self.notification.estado, Notification.Estado.PENDIENTE)
        self.assertIsNotNone(self.notification.fecha_creacion)
    
    def test_marcar_como_leida(self):
        """Test que verifica marcar una notificación como leída."""
        self.notification.marcar_como_enviada()
        self.notification.marcar_como_leida()
        
        self.assertEqual(self.notification.estado, Notification.Estado.LEIDA)
        self.assertIsNotNone(self.notification.fecha_lectura)
    
    def test_properties(self):
        """Test que verifica las propiedades de la notificación."""
        self.assertTrue(self.notification.es_pendiente)
        self.assertFalse(self.notification.es_leida)
        
        self.notification.marcar_como_enviada()
        self.notification.marcar_como_leida()
        
        self.assertTrue(self.notification.es_leida)
        self.assertFalse(self.notification.es_pendiente)
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tickets.models import Ticket, Estado
from .models import Notification, NotificationType

User = get_user_model()


class NotificationTypeModelTest(TestCase):
    """Tests para el modelo NotificationType."""
    
    def setUp(self):
        self.notification_type, created = NotificationType.objects.get_or_create(
            codigo='ticket_creado',
            defaults={
                'nombre': 'Ticket Creado',
                'descripcion': 'Notificación cuando se crea un nuevo ticket',
                'enviar_a_cliente': True,
                'enviar_a_tecnico': True,
                'enviar_a_admin': False
            }
        )
    
    def test_notification_type_creation(self):
        """Test que verifica la creación de un tipo de notificación."""
        self.assertEqual(self.notification_type.codigo, 'ticket_creado')
        self.assertEqual(self.notification_type.nombre, 'Ticket Creado')
        self.assertTrue(self.notification_type.enviar_a_cliente)
        self.assertTrue(self.notification_type.enviar_a_tecnico)
        self.assertFalse(self.notification_type.enviar_a_admin)
        self.assertTrue(self.notification_type.es_activo)
    
    def test_notification_type_str(self):
        """Test que verifica la representación string del tipo de notificación."""
        expected = "Ticket Creado (ticket_creado)"
        self.assertEqual(str(self.notification_type), expected)
    
    def test_notification_type_unique_codigo(self):
        """Test que verifica que el código sea único."""
        with self.assertRaises(Exception):
            NotificationType.objects.create(
                codigo='ticket_creado',  # Código duplicado
                nombre='Otro Ticket Creado'
            )


class NotificationModelTest(TestCase):
    """Tests para el modelo Notification."""
    
    def setUp(self):
        # Crear usuarios
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
        
        # Crear estado
        self.estado = Estado.objects.create(
            codigo='abierto',
            nombre='Abierto',
            es_activo=True
        )
        
        # Crear ticket
        self.ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket de prueba',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado
        )
        
        # Crear tipo de notificación
        self.notification_type, created = NotificationType.objects.get_or_create(
            codigo='ticket_creado',
            defaults={
                'nombre': 'Ticket Creado',
                'enviar_a_cliente': True
            }
        )
        
        # Crear notificación
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
    
    def test_notification_str(self):
        """Test que verifica la representación string de la notificación."""
        expected = f"[ticket_creado] Nuevo Ticket Creado - {self.cliente.email}"
        self.assertEqual(str(self.notification), expected)
    
    def test_marcar_como_enviada(self):
        """Test que verifica marcar una notificación como enviada."""
        self.notification.marcar_como_enviada()
        
        self.assertEqual(self.notification.estado, Notification.Estado.ENVIADA)
        self.assertIsNotNone(self.notification.fecha_envio)
    
    def test_marcar_como_leida(self):
        """Test que verifica marcar una notificación como leída."""
        self.notification.marcar_como_enviada()
        self.notification.marcar_como_leida()
        
        self.assertEqual(self.notification.estado, Notification.Estado.LEIDA)
        self.assertIsNotNone(self.notification.fecha_lectura)
    
    def test_marcar_como_fallida(self):
        """Test que verifica marcar una notificación como fallida."""
        self.notification.marcar_como_fallida()
        
        self.assertEqual(self.notification.estado, Notification.Estado.FALLIDA)
    
    def test_properties(self):
        """Test que verifica las propiedades de la notificación."""
        # Inicialmente es pendiente
        self.assertTrue(self.notification.es_pendiente)
        self.assertFalse(self.notification.es_leida)
        
        # Después de marcar como leída
        self.notification.marcar_como_enviada()
        self.notification.marcar_como_leida()
        
        self.assertTrue(self.notification.es_leida)
        self.assertFalse(self.notification.es_pendiente)
    
    def test_datos_adicionales(self):
        """Test que verifica el campo de datos adicionales."""
        datos = {'prioridad': 'alta', 'equipo': 'servidor-01'}
        self.notification.datos_adicionales = datos
        self.notification.save()
        
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.datos_adicionales, datos)
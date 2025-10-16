"""
Tests de integración para el sistema de notificaciones con tickets.
Verifica que las notificaciones se envíen correctamente en el flujo de tickets.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from unittest.mock import patch

from tickets.models import Ticket, Estado
from .models import Notification, NotificationType
from .services import NotificationService

User = get_user_model()


class NotificationIntegrationTestCase(TestCase):
    """Tests de integración para notificaciones con tickets."""
    
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
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            document='11111111',
            password='testpass123',
            role=User.Role.ADMIN
        )
        
        # Crear estados
        self.estado_abierto = Estado.objects.create(
            codigo='abierto',
            nombre='Abierto',
            es_activo=True
        )
        
        self.estado_en_proceso = Estado.objects.create(
            codigo='en_proceso',
            nombre='En Proceso',
            es_activo=True
        )
        
        self.estado_finalizado = Estado.objects.create(
            codigo='finalizado',
            nombre='Finalizado',
            es_activo=True,
            es_final=True
        )
        
        # Inicializar tipos de notificaciones
        self.notification_type_creado = NotificationType.objects.create(
            codigo='ticket_creado',
            nombre='Ticket Creado',
            enviar_a_cliente=True,
            enviar_a_tecnico=True,
            enviar_a_admin=True
        )
        
        self.notification_type_asignado = NotificationType.objects.create(
            codigo='ticket_asignado',
            nombre='Ticket Asignado',
            enviar_a_tecnico=True
        )
        
        self.notification_type_estado = NotificationType.objects.create(
            codigo='estado_cambiado',
            nombre='Estado Cambiado',
            enviar_a_cliente=True
        )
        
        self.notification_type_finalizado = NotificationType.objects.create(
            codigo='ticket_finalizado',
            nombre='Ticket Finalizado',
            enviar_a_cliente=True,
            enviar_a_tecnico=True
        )
    
    def test_ticket_creation_notifications(self):
        """Test que verifica las notificaciones al crear un ticket."""
        # Limpiar notificaciones existentes
        Notification.objects.all().delete()
        
        # Crear ticket
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Verificar que se crearon notificaciones
        notificaciones = Notification.objects.filter(ticket=ticket)
        
        # Debe haber notificaciones para cliente y técnico
        self.assertGreaterEqual(notificaciones.count(), 2)
        
        # Verificar notificación al cliente
        notif_cliente = notificaciones.filter(usuario=self.cliente).first()
        self.assertIsNotNone(notif_cliente)
        self.assertEqual(notif_cliente.tipo.codigo, 'ticket_creado')
        
        # Verificar notificación al técnico
        notif_tecnico = notificaciones.filter(usuario=self.tecnico).first()
        self.assertIsNotNone(notif_tecnico)
        self.assertEqual(notif_tecnico.tipo.codigo, 'ticket_asignado')
    
    def test_ticket_state_change_notifications(self):
        """Test que verifica las notificaciones al cambiar el estado de un ticket."""
        # Crear ticket
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Limpiar notificaciones existentes
        Notification.objects.filter(ticket=ticket).delete()
        
        # Cambiar estado
        ticket.estado = self.estado_en_proceso
        ticket.save()
        
        # Verificar que se creó notificación de cambio de estado
        notificaciones = Notification.objects.filter(
            ticket=ticket,
            tipo__codigo='estado_cambiado'
        )
        
        self.assertEqual(notificaciones.count(), 1)
        
        notif = notificaciones.first()
        self.assertEqual(notif.usuario, self.cliente)
        self.assertIn('En Proceso', notif.mensaje)
    
    def test_ticket_technician_change_notifications(self):
        """Test que verifica las notificaciones al cambiar el técnico."""
        # Crear nuevo técnico
        tecnico2 = User.objects.create_user(
            email='tecnico2@test.com',
            document='22222222',
            password='testpass123',
            role=User.Role.TECH
        )
        
        # Crear ticket
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Limpiar notificaciones existentes
        Notification.objects.filter(ticket=ticket).delete()
        
        # Cambiar técnico
        ticket.tecnico = tecnico2
        ticket.save()
        
        # Verificar notificaciones
        notificaciones = Notification.objects.filter(ticket=ticket)
        
        # Debe haber notificación al técnico anterior y al nuevo
        notif_tecnico_anterior = notificaciones.filter(usuario=self.tecnico).first()
        notif_tecnico_nuevo = notificaciones.filter(usuario=tecnico2).first()
        
        self.assertIsNotNone(notif_tecnico_anterior)
        self.assertIsNotNone(notif_tecnico_nuevo)
    
    def test_ticket_completion_notifications(self):
        """Test que verifica las notificaciones al finalizar un ticket."""
        # Crear ticket
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_en_proceso
        )
        
        # Limpiar notificaciones existentes
        Notification.objects.filter(ticket=ticket).delete()
        
        # Finalizar ticket
        ticket.estado = self.estado_finalizado
        ticket.save()
        
        # Verificar notificaciones de finalización
        notificaciones = Notification.objects.filter(
            ticket=ticket,
            tipo__codigo='ticket_finalizado'
        )
        
        # Debe haber notificaciones para cliente y técnico
        self.assertEqual(notificaciones.count(), 2)
        
        notif_cliente = notificaciones.filter(usuario=self.cliente).first()
        notif_tecnico = notificaciones.filter(usuario=self.tecnico).first()
        
        self.assertIsNotNone(notif_cliente)
        self.assertIsNotNone(notif_tecnico)
    
    @patch('notifications.services.NotificationService._enviar_email')
    def test_notification_service_email_sending(self, mock_send_email):
        """Test que verifica el envío de emails en el servicio de notificaciones."""
        # Configurar mock para que no falle
        mock_send_email.return_value = None
        
        # Crear ticket
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Enviar notificaciones manualmente
        resultados = NotificationService.enviar_notificacion_ticket_creado(ticket)
        
        # Verificar resultados
        self.assertIn('emails_enviados', resultados)
        self.assertIn('notificaciones_internas', resultados)
        self.assertIn('errores', resultados)
        
        # Verificar que se intentó enviar emails
        self.assertGreater(mock_send_email.call_count, 0)
    
    def test_notification_service_error_handling(self):
        """Test que verifica el manejo de errores en el servicio."""
        # Crear ticket sin cliente (debería manejar el error)
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=None,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Enviar notificaciones
        resultados = NotificationService.enviar_notificacion_ticket_creado(ticket)
        
        # Debe manejar el error sin fallar
        self.assertIsInstance(resultados, dict)
        self.assertIn('errores', resultados)
    
    def test_notification_stats_integration(self):
        """Test que verifica las estadísticas de notificaciones."""
        # Crear algunas notificaciones
        ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Descripción del ticket',
            cliente=self.cliente,
            tecnico=self.tecnico,
            estado=self.estado_abierto
        )
        
        # Verificar estadísticas del cliente
        stats_cliente = Notification.objects.filter(usuario=self.cliente).aggregate(
            total=Count('id'),
            pendientes=Count('id', filter=Q(estado=Notification.Estado.PENDIENTE)),
            leidas=Count('id', filter=Q(estado=Notification.Estado.LEIDA))
        )
        
        self.assertGreater(stats_cliente['total'], 0)
        self.assertGreaterEqual(stats_cliente['pendientes'], 0)
        self.assertGreaterEqual(stats_cliente['leidas'], 0)

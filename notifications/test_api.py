from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone

from .models import Notification, NotificationType
from tickets.models import Ticket, Estado

User = get_user_model()


class NotificationAPITestCase(APITestCase):
    """Tests para la API de notificaciones."""
    
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
        self.notification_type = NotificationType.objects.create(
            codigo='ticket_creado',
            nombre='Ticket Creado',
            enviar_a_cliente=True
        )
        
        # Crear notificaciones
        self.notification1 = Notification.objects.create(
            usuario=self.cliente,
            ticket=self.ticket,
            tipo=self.notification_type,
            titulo='Notificación 1',
            mensaje='Mensaje de prueba 1',
            estado=Notification.Estado.PENDIENTE
        )
        
        self.notification2 = Notification.objects.create(
            usuario=self.cliente,
            ticket=self.ticket,
            tipo=self.notification_type,
            titulo='Notificación 2',
            mensaje='Mensaje de prueba 2',
            estado=Notification.Estado.ENVIADA
        )
        
        self.notification3 = Notification.objects.create(
            usuario=self.tecnico,
            ticket=self.ticket,
            tipo=self.notification_type,
            titulo='Notificación 3',
            mensaje='Mensaje de prueba 3',
            estado=Notification.Estado.LEIDA
        )
    
    def test_notification_list_authenticated(self):
        """Test que verifica la lista de notificaciones para usuario autenticado."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('notifications', response.data)
        self.assertIn('total', response.data)
        
        # Debe retornar solo las notificaciones del cliente
        notifications = response.data['notifications']
        self.assertEqual(len(notifications), 2)
        self.assertEqual(response.data['total'], 2)
    
    def test_notification_list_unauthenticated(self):
        """Test que verifica que usuarios no autenticados no pueden acceder."""
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        
        # Django REST Framework puede retornar 401 o 403 dependiendo de la configuración
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_notification_list_with_filters(self):
        """Test que verifica los filtros en la lista de notificaciones."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:notification-list')
        
        # Filtrar por estado
        response = self.client.get(url, {'estado': 'PENDIENTE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        
        # Filtrar por no leídas
        response = self.client.get(url, {'leidas': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
    
    def test_notification_detail_authenticated(self):
        """Test que verifica el detalle de una notificación."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:notification-detail', args=[self.notification1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.notification1.id)
        self.assertEqual(response.data['titulo'], 'Notificación 1')
        
        # Verificar que se marcó como leída
        self.notification1.refresh_from_db()
        self.assertEqual(self.notification1.estado, Notification.Estado.LEIDA)
    
    def test_notification_detail_unauthorized(self):
        """Test que verifica que no se puede acceder a notificaciones de otros usuarios."""
        self.client.force_authenticate(user=self.tecnico)
        url = reverse('notifications:notification-detail', args=[self.notification1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_mark_notifications_as_read(self):
        """Test que verifica marcar notificaciones como leídas."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:mark-as-read')
        
        data = {
            'notification_ids': [self.notification1.id, self.notification2.id]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('updated_count', response.data)
        
        # Verificar que se marcaron como leídas
        self.notification1.refresh_from_db()
        self.notification2.refresh_from_db()
        self.assertEqual(self.notification1.estado, Notification.Estado.LEIDA)
        self.assertEqual(self.notification2.estado, Notification.Estado.LEIDA)
    
    def test_mark_notifications_as_read_unauthorized(self):
        """Test que verifica que no se pueden marcar notificaciones de otros usuarios."""
        self.client.force_authenticate(user=self.tecnico)
        url = reverse('notifications:mark-as-read')
        
        data = {
            'notification_ids': [self.notification1.id]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_mark_all_as_read(self):
        """Test que verifica marcar todas las notificaciones como leídas."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:mark-all-as-read')
        
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('updated_count', response.data)
        
        # Verificar que todas se marcaron como leídas
        self.notification1.refresh_from_db()
        self.notification2.refresh_from_db()
        self.assertEqual(self.notification1.estado, Notification.Estado.LEIDA)
        self.assertEqual(self.notification2.estado, Notification.Estado.LEIDA)
    
    def test_notification_stats(self):
        """Test que verifica las estadísticas de notificaciones."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:notification-stats')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['pendientes'], 1)
        self.assertEqual(response.data['enviadas'], 1)
        self.assertEqual(response.data['leidas'], 0)
        self.assertEqual(response.data['no_leidas'], 2)
    
    def test_notification_types(self):
        """Test que verifica la lista de tipos de notificaciones."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:notification-types')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
    
    def test_delete_notification(self):
        """Test que verifica eliminar una notificación."""
        self.client.force_authenticate(user=self.cliente)
        url = reverse('notifications:delete-notification', args=[self.notification1.id])
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verificar que se eliminó
        self.assertFalse(Notification.objects.filter(id=self.notification1.id).exists())
    
    def test_delete_notification_unauthorized(self):
        """Test que verifica que no se pueden eliminar notificaciones de otros usuarios."""
        self.client.force_authenticate(user=self.tecnico)
        url = reverse('notifications:delete-notification', args=[self.notification1.id])
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


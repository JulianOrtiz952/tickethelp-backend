from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from tickets.models import Ticket, Estado

User = get_user_model()

class TechnicianReassignmentTests(APITestCase):
    def setUp(self):
        # Create Admin
        self.admin = User.objects.create_superuser(
            document='admin1',
            email='admin@example.com',
            password='Password123!',
            role='ADMIN'
        )
        
        # Create Technicians
        self.tech1 = User.objects.create_user(
            document='tech1',
            email='tech1@example.com',
            password='Password123!',
            role='TECH'
        )
        self.tech2 = User.objects.create_user(
            document='tech2',
            email='tech2@example.com',
            password='Password123!',
            role='TECH'
        )
        
        # Create Client
        self.client_user = User.objects.create_user(
            document='client1',
            email='client@example.com',
            password='Password123!',
            role='CLIENT'
        )
        
        # Create State
        self.state_open, _ = Estado.objects.get_or_create(
            codigo='open', 
            defaults={'id': 1, 'nombre': 'Abierto', 'es_final': False}
        )
        
        # Create Ticket assigned to tech1
        self.ticket = Ticket.objects.create(
            titulo='Test Ticket',
            descripcion='Description',
            cliente=self.client_user,
            tecnico=self.tech1,
            administrador=self.admin,
            estado=self.state_open
        )
        
        self.client.force_authenticate(user=self.admin)
        self.url = reverse('change-technician', kwargs={'ticket_id': self.ticket.id})

    def test_reassign_same_technician(self):
        """CB-03: Ensure reassignment fails if the technician is the same."""
        data = {
            'documento_tecnico': self.tech1.document
        }
        response = self.client.put(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(str(response.data['detail'][0]), "No puede asignar el mismo técnico actual")

    def test_reassign_different_technician_success(self):
        """CB-03: Ensure reassignment succeeds for a different technician."""
        data = {
            'documento_tecnico': self.tech2.document
        }
        response = self.client.put(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.tecnico, self.tech2)

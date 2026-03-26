from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from tickets.models import Ticket, Estado
from django.core.files.uploadedfile import SimpleUploadedFile

class TicketEndpointsTests(APITestCase):
    def setUp(self):
        # Crear usuarios
        self.admin = User.objects.create_user(
            email='admin@test.com', password='Password123!', document='111', role=User.Role.ADMIN, is_active=True
        )
        self.tech = User.objects.create_user(
            email='tech@test.com', password='Password123!', document='222', role=User.Role.TECH, is_active=True
        )
        self.client_user = User.objects.create_user(
            email='client@test.com', password='Password123!', document='333', role=User.Role.CLIENT, is_active=True
        )
        
        # Crear estados base necesarios
        self.e_open, _ = Estado.objects.get_or_create(codigo='open', defaults={'nombre': 'Abierto', 'es_final': False})
        self.e_diag, _ = Estado.objects.get_or_create(codigo='diagnosis', defaults={'nombre': 'En diagnóstico', 'es_final': False})
        self.e_canceled, _ = Estado.objects.get_or_create(codigo='canceled', defaults={'nombre': 'Cancelado', 'es_final': True})
        self.e_closed, _ = Estado.objects.get_or_create(codigo='closed', defaults={'nombre': 'Cerrado', 'es_final': True})
        self.e_trial, _ = Estado.objects.get_or_create(codigo='trial', defaults={'nombre': 'Pruebas', 'es_final': False})
        
        # Crear ticket base para pruebas
        self.ticket = Ticket.objects.create(
            cliente=self.client_user,
            administrador=self.admin,
            tecnico=self.tech,
            estado=self.e_open,
            titulo="Mouse roto",
            descripcion="No sirve el click derecho",
            equipo="Logitech"
        )

    # ------------------------------------------------------------
    # 1. Tests de CANCELAR TICKET (TicketCancelAV)
    # ------------------------------------------------------------
    def test_cancel_ticket_success_client(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('cancel-ticket', args=[self.ticket.pk])
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado.codigo, 'canceled')

    def test_cancel_ticket_fail_invalid_state(self):
        # Cambiamos estado a 'closed' (no permitido cancelar)
        self.ticket.estado = self.e_closed
        self.ticket.save()

        self.client.force_authenticate(user=self.client_user)
        url = reverse('cancel-ticket', args=[self.ticket.pk])
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'No permitido')

    def test_cancel_ticket_fail_unauthorized_client(self):
        # Otro cliente no puede cancelar el ticket
        other_client = User.objects.create_user(
            email='otro@test.com', password='Password123!', document='999', role=User.Role.CLIENT, is_active=True
        )
        self.client.force_authenticate(user=other_client)
        url = reverse('cancel-ticket', args=[self.ticket.pk])
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------
    # 2. Tests de SUBIR ARCHIVOS (TicketAttachmentAV)
    # ------------------------------------------------------------
    def test_upload_attachment_success_admin(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('ticket-attachments', args=[self.ticket.pk])
        
        # Archivo simulado (PDF)
        file = SimpleUploadedFile("documento.pdf", b"file_content", content_type="application/pdf")
        
        response = self.client.post(url, {'archivo': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('adjunto', response.data)

    def test_upload_attachment_fail_client(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('ticket-attachments', args=[self.ticket.pk])
        file = SimpleUploadedFile("imagen.jpg", b"image", content_type="image/jpeg")
        
        response = self.client.post(url, {'archivo': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_attachment_fail_large_file(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('ticket-attachments', args=[self.ticket.pk])
        # Simulamos un archivo gigantesco (11MB) en la vista validando
        # Lo haremos pasándole un content_type no permitido para forzar error 400 rápido
        file = SimpleUploadedFile("malicioso.exe", b"virus", content_type="application/x-msdownload")
        
        response = self.client.post(url, {'archivo': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('archivo', response.data)
        
    def test_upload_attachment_fail_closed_ticket(self):
        self.ticket.estado = self.e_closed
        self.ticket.save()
        self.client.force_authenticate(user=self.admin)
        url = reverse('ticket-attachments', args=[self.ticket.pk])
        file = SimpleUploadedFile("doc.pdf", b"pdf", content_type="application/pdf")
        
        response = self.client.post(url, {'archivo': file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('error'), 'Ticket cerrado')

    # ------------------------------------------------------------
    # 3. Tests de LISTADO DE TICKETS (TicketListView)
    # ------------------------------------------------------------
    def test_list_tickets_client(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('ticket-consulta')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Asegurar que ve al menos su ticket creado
        self.assertEqual(response.data['total_tickets'], 1)

    # ------------------------------------------------------------
    # 4. Tests de TIMELINE (TicketTimelineAV)
    # ------------------------------------------------------------
    def test_timeline_ticket_client(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('ticket-timeline', args=[self.ticket.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('timeline', response.data)
        self.assertEqual(response.data['estado_actual'], 'Abierto')
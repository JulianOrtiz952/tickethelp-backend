from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User

class ReportsEndpointsTests(APITestCase):
    def setUp(self):
        # Crear usuario administrador
        self.admin = User.objects.create_user(
            email='admin_reports@test.com', password='Password123!', document='admin_01', role=User.Role.ADMIN, is_active=True
        )
        # Crear usuario técnico
        self.tech = User.objects.create_user(
            email='tech_reports@test.com', password='Password123!', document='tech_01', role=User.Role.TECH, is_active=True
        )

    def test_general_stats_admin_success(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('general-stats')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificamos que contenga llaves estadísticas
        self.assertIn('tickets_abiertos', response.data)

    def test_general_stats_tech_forbidden(self):
        self.client.force_authenticate(user=self.tech)
        url = reverse('general-stats')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_technician_performance_ranking(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('performance-ranking')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_status_distribution(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('status-distribution')
        response = self.client.get(url, {'start_date': '2026-01-01', 'end_date': '2026-12-31'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_technician_own_performance(self):
        self.client.force_authenticate(user=self.tech)
        url = reverse('technician-performance')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

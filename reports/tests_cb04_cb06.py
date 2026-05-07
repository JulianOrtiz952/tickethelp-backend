from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class ReportParameterTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            document='admin1',
            email='admin@example.com',
            password='Password123!',
            role='ADMIN'
        )
        self.client.force_authenticate(user=self.admin)
        self.ranking_url = reverse('performance-ranking')
        self.evolution_url = reverse('clients-evolution')

    def test_performance_ranking_negative_limit(self):
        """CB-04: Ensure ranking fails with negative limit."""
        response = self.client.get(f"{self.ranking_url}?limit=-5")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "El parámetro limit debe ser mayor que cero")

    def test_performance_ranking_non_numeric_limit(self):
        """CB-04: Ensure ranking fails with non-numeric limit."""
        response = self.client.get(f"{self.ranking_url}?limit=abc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "El parámetro limit debe ser un número entero mayor que cero")

    def test_clients_evolution_invalid_year_range(self):
        """CB-06: Ensure evolution fails with out-of-range year."""
        response = self.client.get(f"{self.evolution_url}?year=999999")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "El parámetro year es inválido")

    def test_clients_evolution_non_numeric_year(self):
        """CB-06: Ensure evolution fails with non-numeric year."""
        response = self.client.get(f"{self.evolution_url}?year=abcd")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "El parámetro year es inválido")

    def test_parameters_valid_success(self):
        """Ensure endpoints work with valid parameters."""
        response_ranking = self.client.get(f"{self.ranking_url}?limit=10")
        self.assertEqual(response_ranking.status_code, status.HTTP_200_OK)
        
        response_evolution = self.client.get(f"{self.evolution_url}?year=2024")
        self.assertEqual(response_evolution.status_code, status.HTTP_200_OK)

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User

class NotificationsEndpointsTests(APITestCase):
    def setUp(self):
        # Crear usuario
        self.client_user = User.objects.create_user(
            email='client_notif@test.com', password='Password123!', document='client_notif_01', role=User.Role.CLIENT, is_active=True
        )

    def test_list_notifications(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('notifications:notification-list')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_notifications(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('notifications:user-notifications')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

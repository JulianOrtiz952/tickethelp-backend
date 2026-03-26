from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User

class UserEndpointsTests(APITestCase):
    def setUp(self):
        # Crear usuarios para el test
        self.admin = User.objects.create_user(
            email='admin_users@test.com', password='Password123!', document='admin_01', role=User.Role.ADMIN, is_active=True
        )
        self.client_user = User.objects.create_user(
            email='client_users@test.com', password='Password123!', document='client_01', role=User.Role.CLIENT, is_active=True
        )

    def test_list_users_as_admin(self):
        """El administrador puede listar a todos los usuarios"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users_as_client_fails(self):
        """El cliente no puede listar a todos los usuarios"""
        self.client.force_authenticate(user=self.client_user)
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_me_profile(self):
        """Un usuario puede ver y actualizar su propio perfil"""
        self.client.force_authenticate(user=self.client_user)
        url = reverse('users-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_update_profile(self):
        """Un usuario puede editar sus datos permitidos"""
        self.client.force_authenticate(user=self.client_user)
        url = reverse('users-me')
        data = {
            'first_name': 'Nuevo Nombre',
            'last_name': 'Actualizado'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.first_name, 'Nuevo Nombre')

    def test_deactivate_user(self):
        """Un admin puede desactivar a un usuario"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user-deactivate', args=[self.client_user.document])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)

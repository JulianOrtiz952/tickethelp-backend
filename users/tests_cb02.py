from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordChangeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            document='12345678',
            email='testuser@example.com',
            password='OldPassword123!',
            first_name='Test',
            last_name='User',
            role='ADMIN'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('change_password')

    def test_change_password_wrong_current_password(self):
        """CB-02: Ensure password change fails with incorrect current password."""
        data = {
            'current_password': 'WrongPassword',
            'new_password': 'NewPassword123!',
            'new_password_confirm': 'NewPassword123!'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)
        self.assertEqual(response.data['current_password'][0], "La contraseña actual es incorrecta.")

    def test_change_password_weak_new_password(self):
        """CB-02: Ensure password change fails with weak new password."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': '123',
            'new_password_confirm': '123'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # DRF error message for min_length or password_validation
        self.assertTrue('new_password' in response.data or 'non_field_errors' in response.data)

    def test_change_password_same_as_old(self):
        """CB-02: Ensure password change fails if new password is same as current (via validator)."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'OldPassword123!',
            'new_password_confirm': 'OldPassword123!'
        }
        response = self.client.post(self.url, data)
        # validate_password should catch this if the rule is enabled, 
        # but our specific serializer logic also handles strength.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_success(self):
        """CB-02: Ensure successful password change when all data is valid."""
        data = {
            'current_password': 'OldPassword123!',
            'new_password': 'NewValidPassword123!',
            'new_password_confirm': 'NewValidPassword123!'
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], "Contraseña actualizada con éxito")
        
        # Verify password was actually changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewValidPassword123!'))

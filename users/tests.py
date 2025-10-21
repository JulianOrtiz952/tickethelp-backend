# =============================================================================
# HU14A - Login: Pruebas unitarias para el sistema de autenticación
# =============================================================================
# Este archivo contiene las pruebas unitarias para validar la implementación
# de los escenarios de la HU14A - Login
# =============================================================================

from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

class UserTests(APITestCase):
    """
    Pruebas unitarias para el sistema de autenticación de la HU14A.
    
    Implementa pruebas para los siguientes escenarios:
    - Escenario 1: Inicio de sesión exitoso ✅
    - Escenario 7: Usuario inactivo ✖️
    - Escenario 12: Contraseña por defecto ✖️
    - Escenario 4: Cambio de contraseña ✅
    - Escenario 13: Contraseña muy corta ✖️
    - Escenario 17: Contraseña con espacios ✖️
    """

    def setUp(self):
        """
        Configuración inicial para las pruebas.
        
        Crea un usuario de prueba con datos válidos y configura
        el entorno necesario para ejecutar las pruebas de la HU14A.
        """
        # Configurar los datos para las pruebas (usuario de ejemplo)
        self.user_data = {
            "email": "usuario@example.com",
            "password": "Contraseña123",
            "document": "1234567890",
            "role": "CLIENT",
        }
        self.user = get_user_model().objects.create_user(**self.user_data)

        # Usuario normal sin restricciones de contraseña para la mayoría de pruebas
        self.user.must_change_password = False
        self.user.save()

        # Obtener el token JWT para pruebas autenticadas
        self.token = self.get_jwt_token(self.user)

    def get_jwt_token(self, user):
        """
        Genera un token JWT para un usuario.
        
        Args:
            user: Usuario para el cual generar el token
            
        Returns:
            str: Token JWT de acceso
        """
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_login_successful(self):
        """
        Prueba el Escenario 1 - Inicio de sesión exitoso ✅
        
        Valida que un usuario con credenciales válidas pueda
        autenticarse exitosamente y reciba un token JWT.
        """
        url = '/api/users/auth/login/'  # URL del endpoint de login
        data = {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }

        response = self.client.post(url, data, format='json')

        # Verifica que la respuesta contenga un token JWT
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('user', response.data)

    def test_login_with_inactive_user(self):
        """
        Prueba el Escenario 7 - Usuario inactivo ✖️
        
        Valida que un usuario con cuenta inactiva no pueda
        autenticarse y reciba el mensaje de error apropiado.
        """
        # Configurar usuario como inactivo
        self.user.is_active = False
        self.user.save()

        url = '/api/users/auth/login/'
        data = {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }

        response = self.client.post(url, data, format='json')

        # Verificar respuesta de error
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # El mensaje puede variar según la implementación de SimpleJWT
        self.assertIn("No active account", str(response.data['detail']))

    def test_login_with_default_password(self):
        """
        Prueba el Escenario 12 - Contraseña por defecto ✖️
        
        Valida que un usuario que debe cambiar su contraseña
        no pueda autenticarse y reciba el mensaje de error apropiado.
        """
        # Configurar usuario para que deba cambiar contraseña
        self.user.must_change_password = True
        self.user.save()

        url = '/api/users/auth/login/'
        data = {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }

        response = self.client.post(url, data, format='json')

        # Verificar respuesta de error
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], "Por favor, cambie la contraseña")

    def test_change_password_successful(self):
        """
        Prueba el Escenario 4 - Cambio de contraseña ✅
        
        Valida que un usuario autenticado pueda cambiar su contraseña
        exitosamente y que se actualice el campo must_change_password.
        """
        url = '/api/users/auth/change-password/'  # URL del endpoint de cambio de contraseña
        data = {
            'new_password': 'NuevaContraseña123!'  # Contraseña que cumple todas las validaciones
        }

        # Autenticarse con el token JWT
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        response = self.client.post(url, data, format='json')

        # Verificar respuesta exitosa
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], "Contraseña actualizada con éxito")

    def test_change_password_invalid(self):
        """
        Prueba el Escenario 13 - Contraseña inválida (muy corta) ✖️
        
        Valida que una contraseña de menos de 8 caracteres
        sea rechazada con el mensaje de error apropiado.
        """
        url = '/api/users/auth/change-password/'
        data = {
            'new_password': 'Corto1'  # Contraseña de solo 6 caracteres
        }

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        response = self.client.post(url, data, format='json')

        # Verificar respuesta de error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Contraseña muy corta")

    def test_change_password_with_spaces(self):
        """
        Prueba el Escenario 17 - Contraseña inválida (con espacios) ✖️
        
        Valida que una contraseña que contenga espacios en blanco
        sea rechazada con el mensaje de error apropiado.
        """
        url = '/api/users/auth/change-password/'
        data = {
            'new_password': 'Nueva Contraseña 123!'  # Contraseña con espacios
        }

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        response = self.client.post(url, data, format='json')

        # Verificar respuesta de error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Espacio en blanco no permitido")
from django.test import SimpleTestCase
from users.serializers import UserCreateSerializer, UserUpdateProfilePictureSerializer
from rest_framework.exceptions import ValidationError

class UserSerializerPUTests(SimpleTestCase):
    """
    Pruebas Unitarias (PU) aislando la lógica de validación de los serializers de Usuarios.
    """

    def test_validate_number_success(self):
        """El número de teléfono debe ser válido si tiene 10 dígitos, son números y empieza con 3"""
        serializer = UserCreateSerializer()
        valid_number = "3123456789"
        self.assertEqual(serializer.validate_number(valid_number), valid_number)

    def test_validate_number_fails_length(self):
        """Un número con longitud incorrecta debe fallar"""
        serializer = UserCreateSerializer()
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_number("312")
        self.assertIn("exactamente 10 dígitos", str(ctx.exception))

    def test_validate_number_fails_not_digit(self):
        """Un número con letras debe fallar"""
        serializer = UserCreateSerializer()
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_number("312345678A")
        self.assertIn("solo puede contener dígitos", str(ctx.exception))

    def test_validate_number_fails_starts_wrong(self):
        """Un número que no empiece con 3 debe fallar"""
        serializer = UserCreateSerializer()
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_number("4123456789")
        self.assertIn("debe empezar con 3", str(ctx.exception))

    def test_validate_profile_picture_success(self):
        serializer = UserUpdateProfilePictureSerializer()
        url = "https://example.com/pic.jpg"
        self.assertEqual(serializer.validate_profile_picture(url), url)

    def test_validate_profile_picture_fails(self):
        serializer = UserUpdateProfilePictureSerializer()
        url = "ftp://example.com/pic.jpg"
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate_profile_picture(url)
        self.assertIn("debe comenzar con http", str(ctx.exception))

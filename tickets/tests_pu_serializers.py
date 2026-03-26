from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from tickets.serializers import TicketAttachmentUploadSerializer
from rest_framework.exceptions import ValidationError

class TicketSerializerPUTests(SimpleTestCase):
    """
    Pruebas Unitarias (PU) para la lógica de los serializers.
    No tocan la base de datos (SimpleTestCase).
    """

    def test_attachment_upload_serializer_valid_file(self):
        """Verificar que un archivo de PDF pequeño pasa la validación (PU)"""
        serializer = TicketAttachmentUploadSerializer()
        file = SimpleUploadedFile("doc.pdf", b"test content", content_type="application/pdf")
        
        # Validar directamente el método de la clase
        validated_file = serializer.validate_archivo(file)
        self.assertEqual(validated_file, file)

    def test_attachment_upload_serializer_invalid_type(self):
        """Verificar que un tipo MIME no permitido lanza ValidationError (PU)"""
        serializer = TicketAttachmentUploadSerializer()
        file = SimpleUploadedFile("script.sh", b"bash", content_type="application/x-sh")
        
        with self.assertRaises(ValidationError) as context:
            serializer.validate_archivo(file)
            
        self.assertIn("Tipo de archivo no permitido", str(context.exception))

    def test_attachment_upload_serializer_too_large(self):
        """Verificar que un archivo demasiado grande (simulado) lanza ValidationError (PU)"""
        serializer = TicketAttachmentUploadSerializer()
        file = SimpleUploadedFile("big.pdf", b"x", content_type="application/pdf")
        # Forzar un tamaño de 20 MB artificialmente para probar la validación sin RAM
        file.size = 20 * 1024 * 1024 
        
        with self.assertRaises(ValidationError) as context:
            serializer.validate_archivo(file)
            
        self.assertIn("demasiado grande", str(context.exception))

from unittest.mock import MagicMock
from tickets.serializers import StateApprovalSerializer, StateChangeSerializer

class StateLogicPUTests(SimpleTestCase):
    """
    Pruebas Unitarias (PU) para la lógica crítica de transiciones de estado.
    Usamos Mocks para simular la base de datos y mantener la prueba ultra-rápida.
    """

    def test_state_approval_serializer_reject_requires_reason(self):
        """Si la acción es rechazar pruebas ('reject'), debe exigirse un motivo"""
        serializer = StateApprovalSerializer()
        data = {'action': 'reject', 'rejection_reason': ' '}
        
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate(data)
        
        self.assertIn("Debe proporcionar una razón", str(ctx.exception))

    def test_state_approval_serializer_approve_success(self):
        """Si la acción es aprobar, no se exige motivo"""
        serializer = StateApprovalSerializer()
        data = {'action': 'approve', 'rejection_reason': ''}
        
        # Debe retornar el mismo dict sin fallar
        self.assertEqual(serializer.validate(data), data)

    def test_state_change_serializer_prevent_closed_ticket_change(self):
        """No se debe permitir cambiar de estado un ticket ya finalizado"""
        ticket_mock = MagicMock()
        ticket_mock.estado.es_final = True
        serializer = StateChangeSerializer(context={'ticket': ticket_mock})
        
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate({'to_state': MagicMock()})
            
        self.assertIn("No se puede cambiar el estado de un ticket finalizado", str(ctx.exception))

    def test_state_change_serializer_prevent_trial_to_finalized(self):
        """Se bloquea el pase de Pruebas(6) a Finalizado(5) directamente"""
        ticket_mock = MagicMock()
        ticket_mock.estado.es_final = False
        ticket_mock.estado_id = 6  # Pruebas
        serializer = StateChangeSerializer(context={'ticket': ticket_mock})
        
        to_state_mock = MagicMock()
        to_state_mock.id = 5
        to_state_mock.codigo = "finalized"
        
        with self.assertRaises(ValidationError) as ctx:
            serializer.validate({'to_state': to_state_mock})
            
        self.assertIn("No se puede pasar directamente de 'Pruebas' a 'Finalizado'", str(ctx.exception))

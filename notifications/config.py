"""
Configuración para el sistema de notificaciones.
"""
from django.conf import settings


class NotificationConfig:
    """Configuración centralizada para notificaciones."""
    
    EMAIL_ENABLED = getattr(settings, 'NOTIFICATIONS_EMAIL_ENABLED', True)
    EMAIL_FROM = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com')
    
    NOTIFICATION_TYPES = {
        'ticket_creado': {
            'nombre': 'Ticket Creado',
            'descripcion': 'Notificación cuando se crea un nuevo ticket',
            'enviar_a_cliente': True,
            'enviar_a_tecnico': True,
            'enviar_a_admin': True,
        },
        'ticket_asignado': {
            'nombre': 'Ticket Asignado',
            'descripcion': 'Notificación cuando se asigna un ticket a un técnico',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': True,
            'enviar_a_admin': False,
        },
        'estado_cambiado': {
            'nombre': 'Estado Cambiado',
            'descripcion': 'Notificación cuando cambia el estado de un ticket',
            'enviar_a_cliente': True,
            'enviar_a_tecnico': False,
            'enviar_a_admin': False,
        },
        'solicitud_finalizacion': {
            'nombre': 'Solicitud de Finalización',
            'descripcion': 'Notificación al admin cuando se solicita finalizar un ticket',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': False,
            'enviar_a_admin': True,
        },
        'solicitud_cambio_estado': {
            'nombre': 'Solicitud de Cambio de Estado',
            'descripcion': 'Notificación al admin cuando se solicita un cambio de estado que requiere aprobación',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': False,
            'enviar_a_admin': True,
        },
        'cambio_estado_aprobado': {
            'nombre': 'Cambio de Estado Aprobado',
            'descripcion': 'Notificación al técnico cuando su solicitud de cambio de estado es aprobada',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': True,
            'enviar_a_admin': False,
        },
        'cambio_estado_rechazado': {
            'nombre': 'Cambio de Estado Rechazado',
            'descripcion': 'Notificación al técnico cuando su solicitud de cambio de estado es rechazada',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': True,
            'enviar_a_admin': False,
        },
        'ticket_finalizado': {
            'nombre': 'Ticket Finalizado',
            'descripcion': 'Notificación cuando un ticket es finalizado',
            'enviar_a_cliente': True,
            'enviar_a_tecnico': True,
            'enviar_a_admin': False,
        },
        'tecnico_cambiado': {
            'nombre': 'Técnico Cambiado',
            'descripcion': 'Notificación cuando se cambia el técnico asignado',
            'enviar_a_cliente': False,
            'enviar_a_tecnico': True,
            'enviar_a_admin': False,
        }
    }
    
    @classmethod
    def get_notification_type_config(cls, codigo: str) -> dict:
        """Obtiene la configuración de un tipo de notificación."""
        return cls.NOTIFICATION_TYPES.get(codigo, {})
    
    @classmethod
    def is_email_enabled(cls) -> bool:
        """Verifica si el envío de emails está habilitado."""
        return cls.EMAIL_ENABLED and hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST
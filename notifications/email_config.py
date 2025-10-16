"""
Configuración de email para notificaciones.
Define templates y configuraciones para el envío de emails.
"""
from django.conf import settings
from django.utils import timezone


class EmailConfig:
    """Configuración para emails de notificaciones."""
    
    # Configuración básica
    DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com')
    EMAIL_BACKEND = getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    
    # Templates de email (texto plano por ahora)
    EMAIL_TEMPLATES = {
        'ticket_creado': {
            'subject': 'Nuevo Ticket Creado - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

Se ha creado un nuevo ticket en nuestro sistema:

Título: {ticket_titulo}
ID: #{ticket_id}
Estado: {ticket_estado}
Fecha: {ticket_fecha}

Descripción:
{ticket_descripcion}

Su ticket será procesado por nuestro equipo técnico.

Gracias por usar nuestros servicios.

---
Sistema de Tickets
            '''.strip()
        },
        
        'ticket_asignado': {
            'subject': 'Ticket Asignado - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

Se le ha asignado un nuevo ticket:

Título: {ticket_titulo}
ID: #{ticket_id}
Cliente: {ticket_cliente}
Estado: {ticket_estado}
Fecha: {ticket_fecha}

Descripción:
{ticket_descripcion}

Por favor, revise y actualice el estado del ticket según corresponda.

---
Sistema de Tickets
            '''.strip()
        },
        
        'estado_cambiado': {
            'subject': 'Estado del Ticket Actualizado - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

El estado de su ticket ha sido actualizado:

Título: {ticket_titulo}
ID: #{ticket_id}
Estado anterior: {estado_anterior}
Estado actual: {ticket_estado}
Fecha de actualización: {fecha_actualizacion}

Descripción:
{ticket_descripcion}

Gracias por su paciencia.

---
Sistema de Tickets
            '''.strip()
        },
        
        'solicitud_finalizacion': {
            'subject': 'Solicitud de Finalización - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

El técnico {tecnico_nombre} solicita finalizar el siguiente ticket:

Título: {ticket_titulo}
ID: #{ticket_id}
Cliente: {ticket_cliente}
Estado actual: {ticket_estado}

Descripción:
{ticket_descripcion}

Por favor, revise y apruebe la finalización si considera que el trabajo está completo.

---
Sistema de Tickets
            '''.strip()
        },
        
        'ticket_finalizado': {
            'subject': 'Ticket Finalizado - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

Su ticket ha sido finalizado exitosamente:

Título: {ticket_titulo}
ID: #{ticket_id}
Estado: {ticket_estado}
Fecha de finalización: {fecha_finalizacion}

Descripción:
{ticket_descripcion}

Gracias por usar nuestros servicios. Si tiene alguna consulta adicional, no dude en contactarnos.

---
Sistema de Tickets
            '''.strip()
        },
        
        'tecnico_cambiado': {
            'subject': 'Técnico Asignado Modificado - #{ticket_id}',
            'template': '''
Hola {usuario_nombre},

El técnico asignado al ticket ha sido modificado:

Título: {ticket_titulo}
ID: #{ticket_id}
Técnico anterior: {tecnico_anterior}
Técnico actual: {ticket_tecnico}
Estado: {ticket_estado}

Descripción:
{ticket_descripcion}

El nuevo técnico se pondrá en contacto con usted pronto.

---
Sistema de Tickets
            '''.strip()
        }
    }
    
    @classmethod
    def get_template(cls, tipo_codigo: str) -> dict:
        """Obtiene el template de email para un tipo específico."""
        return cls.EMAIL_TEMPLATES.get(tipo_codigo, {})
    
    @classmethod
    def format_email_content(cls, template: str, context: dict) -> str:
        """Formatea el contenido del email con el contexto proporcionado."""
        try:
            return template.format(**context)
        except KeyError as e:
            # Si falta alguna variable, usar el template sin formatear
            return template
    
    @classmethod
    def get_email_context(cls, ticket, usuario, **kwargs) -> dict:
        """Genera el contexto para los templates de email."""
        return {
            'usuario_nombre': usuario.email,
            'ticket_id': ticket.pk,
            'ticket_titulo': ticket.titulo,
            'ticket_descripcion': ticket.descripcion,
            'ticket_estado': ticket.estado.nombre,
            'ticket_fecha': ticket.fecha.strftime('%d/%m/%Y %H:%M'),
            'ticket_cliente': ticket.cliente.email if ticket.cliente else 'No asignado',
            'ticket_tecnico': ticket.tecnico.email if ticket.tecnico else 'No asignado',
            'fecha_actualizacion': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'fecha_finalizacion': timezone.now().strftime('%d/%m/%Y %H:%M'),
            **kwargs
        }

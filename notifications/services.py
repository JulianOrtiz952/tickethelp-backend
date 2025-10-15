"""
Servicio de notificaciones para el sistema de tickets.
Maneja tanto notificaciones por email como notificaciones internas.
"""
import logging
from typing import List, Optional, Dict, Any
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Notification, NotificationType
from tickets.models import Ticket

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio centralizado para el manejo de notificaciones.
    Coordina el envío de emails y el registro de notificaciones internas.
    """
    
    # Configuración de templates de email
    EMAIL_TEMPLATES = {
        'ticket_creado': {
            'subject': 'Nuevo Ticket Creado - #{ticket_id}',
            'template': 'notifications/emails/ticket_creado.html'
        },
        'ticket_asignado': {
            'subject': 'Ticket Asignado - #{ticket_id}',
            'template': 'notifications/emails/ticket_asignado.html'
        },
        'estado_cambiado': {
            'subject': 'Estado del Ticket Actualizado - #{ticket_id}',
            'template': 'notifications/emails/estado_cambiado.html'
        },
        'solicitud_finalizacion': {
            'subject': 'Solicitud de Finalización - #{ticket_id}',
            'template': 'notifications/emails/solicitud_finalizacion.html'
        },
        'ticket_finalizado': {
            'subject': 'Ticket Finalizado - #{ticket_id}',
            'template': 'notifications/emails/ticket_finalizado.html'
        },
        'tecnico_cambiado': {
            'subject': 'Técnico Asignado Modificado - #{ticket_id}',
            'template': 'notifications/emails/tecnico_cambiado.html'
        }
    }
    
    @classmethod
    def enviar_notificacion_ticket_creado(cls, ticket: Ticket) -> Dict[str, Any]:
        """
        Envía notificaciones cuando se crea un nuevo ticket.
        
        Args:
            ticket: Instancia del ticket creado
            
        Returns:
            Dict con el resultado del envío
        """
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # 1. Notificación al cliente
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 
                    'ticket_creado',
                    'Su ticket ha sido creado exitosamente',
                    'Su ticket ha sido registrado en nuestro sistema y será procesado por nuestro equipo técnico.',
                    resultados
                )
            
            # 2. Notificación al técnico (si está asignado)
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket,
                    'ticket_asignado',
                    'Nuevo ticket asignado',
                    'Se le ha asignado un nuevo ticket que requiere su atención.',
                    resultados
                )
            
            # 3. Notificación al administrador (si no es quien creó el ticket)
            if ticket.administrador and ticket.administrador != ticket.cliente:
                cls._enviar_notificacion_admin(
                    ticket,
                    'ticket_creado',
                    'Nuevo ticket creado en el sistema',
                    'Se ha creado un nuevo ticket en el sistema que requiere supervisión.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket creado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_notificacion_estado_cambiado(cls, ticket: Ticket, estado_anterior: str) -> Dict[str, Any]:
        """
        Envía notificaciones cuando cambia el estado de un ticket.
        """
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Notificación al cliente
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket,
                    'estado_cambiado',
                    f'Estado del ticket actualizado a: {ticket.estado.nombre}',
                    f'El estado de su ticket ha cambiado de "{estado_anterior}" a "{ticket.estado.nombre}".',
                    resultados,
                    datos_adicionales={'estado_anterior': estado_anterior}
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de cambio de estado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_solicitud_finalizacion(cls, ticket: Ticket) -> Dict[str, Any]:
        """
        Envía notificación al administrador cuando se solicita finalizar un ticket.
        """
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Buscar administradores activos
            administradores = User.objects.filter(role=User.Role.ADMIN, is_active=True)
            
            for admin in administradores:
                cls._enviar_notificacion_admin(
                    ticket,
                    'solicitud_finalizacion',
                    'Solicitud de finalización de ticket',
                    f'El técnico {ticket.tecnico.email} solicita finalizar el ticket #{ticket.pk}.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando solicitud de finalización: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_ticket_finalizado(cls, ticket: Ticket) -> Dict[str, Any]:
        """
        Envía notificaciones cuando un ticket es finalizado por el administrador.
        """
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Notificación al cliente
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket,
                    'ticket_finalizado',
                    'Ticket finalizado',
                    'Su ticket ha sido finalizado exitosamente. Gracias por usar nuestros servicios.',
                    resultados
                )
            
            # Notificación al técnico
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket,
                    'ticket_finalizado',
                    'Ticket finalizado',
                    'El ticket que tenía asignado ha sido finalizado por el administrador.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket finalizado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_tecnico_cambiado(cls, ticket: Ticket, tecnico_anterior: Optional[User]) -> Dict[str, Any]:
        """
        Envía notificaciones cuando se cambia el técnico asignado.
        """
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Notificación al técnico anterior
            if tecnico_anterior:
                cls._enviar_notificacion_tecnico(
                    ticket,
                    'tecnico_cambiado',
                    'Ticket reasignado',
                    f'El ticket #{ticket.pk} ha sido reasignado a otro técnico.',
                    resultados,
                    usuario_destino=tecnico_anterior
                )
            
            # Notificación al nuevo técnico
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket,
                    'ticket_asignado',
                    'Nuevo ticket asignado',
                    'Se le ha asignado un nuevo ticket que requiere su atención.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de cambio de técnico: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def _enviar_notificacion_cliente(cls, ticket: Ticket, tipo_codigo: str, titulo: str, 
                                   mensaje: str, resultados: Dict, usuario_destino: User = None,
                                   datos_adicionales: Dict = None):
        """Envía notificación al cliente del ticket."""
        usuario = usuario_destino or ticket.cliente
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_tecnico(cls, ticket: Ticket, tipo_codigo: str, titulo: str,
                                   mensaje: str, resultados: Dict, usuario_destino: User = None,
                                   datos_adicionales: Dict = None):
        """Envía notificación al técnico del ticket."""
        usuario = usuario_destino or ticket.tecnico
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_admin(cls, ticket: Ticket, tipo_codigo: str, titulo: str,
                                 mensaje: str, resultados: Dict, usuario_destino: User = None,
                                 datos_adicionales: Dict = None):
        """Envía notificación al administrador."""
        usuario = usuario_destino or ticket.administrador
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_completa(cls, usuario: User, ticket: Ticket, tipo_codigo: str,
                                    titulo: str, mensaje: str, resultados: Dict,
                                    datos_adicionales: Dict = None):
        """
        Envía tanto la notificación por email como la notificación interna.
        """
        if not usuario or not usuario.email:
            return
        
        # 1. Crear notificación interna
        cls._crear_notificacion_interna(
            usuario, ticket, tipo_codigo, titulo, mensaje, datos_adicionales
        )
        resultados['notificaciones_internas'] += 1
        
        # 2. Enviar email
        try:
            cls._enviar_email(usuario, ticket, tipo_codigo, titulo, mensaje)
            resultados['emails_enviados'] += 1
        except Exception as e:
            logger.error(f"Error enviando email a {usuario.email}: {e}")
            resultados['emails_fallidos'] += 1
            resultados['errores'].append(f"Email fallido para {usuario.email}: {str(e)}")
    
    @classmethod
    def _crear_notificacion_interna(cls, usuario: User, ticket: Ticket, tipo_codigo: str,
                                  titulo: str, mensaje: str, datos_adicionales: Dict = None):
        """Crea una notificación interna en la base de datos."""
        try:
            tipo_notificacion, created = NotificationType.objects.get_or_create(
                codigo=tipo_codigo,
                defaults={
                    'nombre': titulo,
                    'descripcion': f'Notificación automática para {tipo_codigo}',
                    'enviar_a_cliente': usuario.role == User.Role.CLIENT,
                    'enviar_a_tecnico': usuario.role == User.Role.TECH,
                    'enviar_a_admin': usuario.role == User.Role.ADMIN,
                }
            )
            
            Notification.objects.create(
                usuario=usuario,
                ticket=ticket,
                tipo=tipo_notificacion,
                titulo=titulo,
                mensaje=mensaje,
                datos_adicionales=datos_adicionales or {},
                estado=Notification.Estado.ENVIADA,
                fecha_envio=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Error creando notificación interna: {e}")
    
    @classmethod
    def _enviar_email(cls, usuario: User, ticket: Ticket, tipo_codigo: str,
                     titulo: str, mensaje: str):
        """Envía un email de notificación."""
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Configuración de email no encontrada, saltando envío de email")
            return
        
        template_config = cls.EMAIL_TEMPLATES.get(tipo_codigo, {})
        subject = template_config.get('subject', f'Notificación - {titulo}')
        
        # Reemplazar variables en el subject
        subject = subject.format(
            ticket_id=ticket.pk,
            ticket_titulo=ticket.titulo,
            usuario_nombre=usuario.email
        )
        
        # Por ahora enviamos un email simple, después se puede mejorar con templates HTML
        email_message = f"""
{titulo}

{mensaje}

Detalles del Ticket:
- ID: #{ticket.pk}
- Título: {ticket.titulo}
- Estado: {ticket.estado.nombre}
- Fecha: {ticket.fecha}

Gracias por usar nuestros servicios.

---
Sistema de Tickets
        """.strip()
        
        send_mail(
            subject=subject,
            message=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.email],
            fail_silently=False
        )

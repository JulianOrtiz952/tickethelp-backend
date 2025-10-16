import logging
from typing import Dict, Any, Optional
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

from .models import Notification, NotificationType
from tickets.models import Ticket

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio centralizado para el manejo de notificaciones."""
    
    @classmethod
    def enviar_notificacion_ticket_creado(cls, ticket: Ticket) -> Dict[str, Any]:
        """Envía notificaciones cuando se crea un nuevo ticket."""
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Notificar al cliente
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'ticket_creado',
                    'Su ticket ha sido creado exitosamente',
                    'Su ticket ha sido registrado en nuestro sistema.',
                    resultados
                )
            
            # Notificar al técnico si está asignado
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket, 'ticket_asignado',
                    'Nuevo ticket asignado',
                    'Se le ha asignado un nuevo ticket.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket creado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_notificacion_estado_cambiado(cls, ticket: Ticket, estado_anterior: str) -> Dict[str, Any]:
        """Envía notificaciones cuando cambia el estado de un ticket."""
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'estado_cambiado',
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
        """Envía notificación al administrador cuando se solicita finalizar un ticket."""
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            administradores = User.objects.filter(role=User.Role.ADMIN, is_active=True)
            
            for admin in administradores:
                cls._enviar_notificacion_admin(
                    ticket, 'solicitud_finalizacion',
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
        """Envía notificaciones cuando un ticket es finalizado."""
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'ticket_finalizado',
                    'Ticket finalizado',
                    'Su ticket ha sido finalizado exitosamente.',
                    resultados
                )
            
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket, 'ticket_finalizado',
                    'Ticket finalizado',
                    'El ticket que tenía asignado ha sido finalizado.',
                    resultados
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket finalizado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_tecnico_cambiado(cls, ticket: Ticket, tecnico_anterior: Optional[User]) -> Dict[str, Any]:
        """Envía notificaciones cuando se cambia el técnico asignado."""
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            if tecnico_anterior:
                cls._enviar_notificacion_tecnico(
                    ticket, 'tecnico_cambiado',
                    'Ticket reasignado',
                    f'El ticket #{ticket.pk} ha sido reasignado a otro técnico.',
                    resultados,
                    usuario_destino=tecnico_anterior
                )
            
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket, 'ticket_asignado',
                    'Nuevo ticket asignado',
                    'Se le ha asignado un nuevo ticket.',
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
        """Envía tanto la notificación por email como la notificación interna."""
        # Verificación robusta de existencia y validez del usuario
        if not cls._validar_usuario_para_notificacion(usuario):
            logger.warning(f"Usuario inválido para notificación: {usuario}")
            return
        
        # Crear notificación interna
        cls._crear_notificacion_interna(
            usuario, ticket, tipo_codigo, titulo, mensaje, datos_adicionales
        )
        resultados['notificaciones_internas'] += 1
        
        # Enviar email
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
        """Envía un email de notificación usando plantillas HTML personalizadas."""
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Configuración de email no encontrada, saltando envío de email")
            return
        
        subject = f"{titulo} - Ticket #{ticket.pk}"
        
        # Determinar la plantilla HTML según el tipo de usuario y tipo de notificación
        template_html = cls._obtener_plantilla_html(usuario, tipo_codigo)
        
        # Contexto para la plantilla
        context = {
            'usuario': usuario,
            'ticket': ticket,
            'subject': subject,
            'titulo': titulo,
            'mensaje': mensaje,
        }
        
        try:
            # Renderizar plantilla HTML
            html_content = render_to_string(template_html, context)
            
            # Crear mensaje de texto plano como fallback
            text_content = cls._generar_contenido_texto_plano(usuario, ticket, titulo, mensaje)
            
            # Crear email con contenido HTML y texto plano
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com'),
                to=[usuario.email]
            )
            
            # Adjuntar versión HTML
            email.attach_alternative(html_content, "text/html")
            
            # Enviar email
            email.send()
            
        except Exception as e:
            logger.error(f"Error renderizando plantilla HTML para {usuario.email}: {e}")
            # Fallback a email de texto plano si falla la plantilla HTML
            cls._enviar_email_texto_plano(usuario, ticket, titulo, mensaje)
    
    @classmethod
    def _obtener_plantilla_html(cls, usuario: User, tipo_codigo: str) -> str:
        """Determina qué plantilla HTML usar según el tipo de usuario y notificación."""
        # Mapeo de plantillas por tipo de usuario y código de notificación
        plantillas = {
            # Cliente
            (User.Role.CLIENT, 'ticket_creado'): 'emails/ticket_created_client.html',
            (User.Role.CLIENT, 'estado_cambiado'): 'emails/ticket_state_changed_client.html',
            (User.Role.CLIENT, 'ticket_finalizado'): 'emails/ticket_state_changed_client.html',
            
            # Técnico
            (User.Role.TECH, 'ticket_creado'): 'emails/ticket_created_technician.html',
            (User.Role.TECH, 'ticket_asignado'): 'emails/ticket_assigned_technician.html',
            (User.Role.TECH, 'ticket_finalizado'): 'emails/ticket_created_technician.html',
            (User.Role.TECH, 'tecnico_cambiado'): 'emails/ticket_assigned_technician.html',
            
            # Administrador
            (User.Role.ADMIN, 'ticket_creado'): 'emails/ticket_created_admin.html',
            (User.Role.ADMIN, 'solicitud_finalizacion'): 'emails/ticket_created_admin.html',
        }
        
        # Buscar plantilla específica
        plantilla = plantillas.get((usuario.role, tipo_codigo))
        
        if not plantilla:
            # Plantilla por defecto según el tipo de usuario
            if usuario.role == User.Role.CLIENT:
                plantilla = 'emails/ticket_created_client.html'
            elif usuario.role == User.Role.TECH:
                plantilla = 'emails/ticket_created_technician.html'
            elif usuario.role == User.Role.ADMIN:
                plantilla = 'emails/ticket_created_admin.html'
            else:
                plantilla = 'emails/ticket_created_client.html'  # Fallback
        
        return plantilla
    
    @classmethod
    def _generar_contenido_texto_plano(cls, usuario: User, ticket: Ticket, titulo: str, mensaje: str) -> str:
        """Genera contenido de texto plano como fallback."""
        return f"""
{titulo}

Hola {usuario.first_name or usuario.email},

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
    
    @classmethod
    def _enviar_email_texto_plano(cls, usuario: User, ticket: Ticket, titulo: str, mensaje: str):
        """Envía email de texto plano como fallback."""
        subject = f"{titulo} - Ticket #{ticket.pk}"
        text_content = cls._generar_contenido_texto_plano(usuario, ticket, titulo, mensaje)
        
        send_mail(
            subject=subject,
            message=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com'),
            recipient_list=[usuario.email],
            fail_silently=False
        )
    
    @classmethod
    def _validar_usuario_para_notificacion(cls, usuario: User) -> bool:
        """
        Valida que un usuario sea válido para recibir notificaciones.
        Reutiliza patrones de validación del proyecto.
        """
        try:
            # Verificación básica de existencia
            if not usuario:
                logger.warning("Usuario es None")
                return False
            
            # Verificar que el usuario tenga email válido
            if not usuario.email or not usuario.email.strip():
                logger.warning(f"Usuario {usuario.document if hasattr(usuario, 'document') else 'sin_documento'} no tiene email válido")
                return False
            
            # Verificar que el usuario esté activo (reutilizando patrón del modelo)
            if not usuario.is_active:
                logger.warning(f"Usuario {usuario.document if hasattr(usuario, 'document') else 'sin_documento'} está inactivo")
                return False
            
            # Verificar que el usuario exista en la base de datos
            # Reutilizando el patrón de users/views.py línea 194
            if hasattr(usuario, 'document'):
                usuario_existente = User.objects.filter(
                    document=usuario.document,
                    is_active=True
                ).exists()
                
                if not usuario_existente:
                    logger.warning(f"Usuario con documento {usuario.document} no existe en la base de datos")
                    return False
            
            # Verificar que el email sea válido (formato básico)
            if '@' not in usuario.email or '.' not in usuario.email.split('@')[-1]:
                logger.warning(f"Email {usuario.email} tiene formato inválido")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando usuario para notificación: {e}")
            return False
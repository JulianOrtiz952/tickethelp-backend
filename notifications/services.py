import logging
import time
import socket
from typing import Dict, Any, Optional
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from threading import Thread
from smtplib import SMTPException, SMTPServerDisconnected

from .models import Notification, NotificationType
from tickets.models import Ticket

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    
    @classmethod
    def enviar_notificacion_ticket_creado(cls, ticket: Ticket) -> Dict[str, Any]:
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'ticket_creado',
                    'Su ticket ha sido creado exitosamente',
                    'Su ticket ha sido registrado en nuestro sistema.',
                    resultados
                )
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
    def enviar_solicitud_cambio_estado(cls, state_request) -> Dict[str, Any]:
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Optimización: Pre-cargar relaciones y cachear valores
            ticket = state_request.ticket
            ticket_pk = ticket.pk
            from_state_nombre = state_request.from_state.nombre
            to_state_nombre = state_request.to_state.nombre
            reason = state_request.reason or "Sin razón especificada"
            
            # Cachear nombre del técnico
            tecnico_nombre = 'Sistema'
            if state_request.requested_by:
                tecnico_nombre = state_request.requested_by.get_full_name()
            
            # Obtener todos los administradores activos
            administradores = User.objects.filter(role=User.Role.ADMIN, is_active=True)
            
            for admin in administradores:
                cls._enviar_notificacion_admin(
                    ticket, 'solicitud_cambio_estado',
                    'Solicitud de cambio de estado',
                    f'El técnico {tecnico_nombre} solicita cambiar el estado del ticket #{ticket_pk} de "{from_state_nombre}" a "{to_state_nombre}". Razón: {reason}',
                    resultados,
                    usuario_destino=admin,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'reason': reason,
                        'requested_by': tecnico_nombre
                    }
                )
                
        except Exception as e:
            logger.error(f"Error enviando solicitud de cambio de estado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_aprobacion_cambio_estado(cls, state_request) -> Dict[str, Any]:
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Optimización: Pre-cargar relaciones y cachear valores usados múltiples veces
            ticket = state_request.ticket
            ticket_pk = ticket.pk
            ticket_titulo = ticket.titulo
            to_state_nombre = state_request.to_state.nombre
            from_state_nombre = state_request.from_state.nombre
            
            # Cachear nombres de usuarios para evitar múltiples queries
            approved_by_name = 'Sistema'
            if state_request.approved_by:
                approved_by_name = state_request.approved_by.get_full_name()
            
            requested_by_name = 'Sistema'
            if state_request.requested_by:
                requested_by_name = state_request.requested_by.get_full_name()
            
            # Notificar al técnico que solicitó el cambio
            if state_request.requested_by:
                cls._enviar_notificacion_tecnico(
                    ticket, 'cambio_estado_aprobado',
                    'Solicitud de cambio de estado aprobada',
                    f'Su solicitud para cambiar el estado del ticket #{ticket_pk} a "{to_state_nombre}" ha sido aprobada.',
                    resultados,
                    usuario_destino=state_request.requested_by,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'approved_by': approved_by_name,
                        'new_state': to_state_nombre
                    }
                )
            
            # Notificar al cliente sobre el cambio de estado
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'estado_cambiado',
                    f'Estado del ticket actualizado a "{to_state_nombre}"',
                    f'El estado de su ticket #{ticket_pk} "{ticket_titulo}" ha sido actualizado a "{to_state_nombre}".',
                    resultados,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'approved_by': approved_by_name
                    }
                )
            
            # Notificar al administrador que aprobó el cambio
            if state_request.approved_by:
                cls._enviar_notificacion_admin(
                    ticket, 'cambio_estado_aprobado',
                    'Cambio de estado aprobado',
                    f'Ha aprobado el cambio de estado del ticket #{ticket_pk} de "{from_state_nombre}" a "{to_state_nombre}".',
                    resultados,
                    usuario_destino=state_request.approved_by,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'requested_by': requested_by_name
                    }
                )
                
        except Exception as e:
            logger.error(f"Error enviando aprobación de cambio de estado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_rechazo_cambio_estado(cls, state_request) -> Dict[str, Any]:
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Optimización: Pre-cargar relaciones y cachear valores usados múltiples veces
            ticket = state_request.ticket
            ticket_pk = ticket.pk
            ticket_titulo = ticket.titulo
            to_state_nombre = state_request.to_state.nombre
            from_state_nombre = state_request.from_state.nombre
            rejection_reason = state_request.rejection_reason or "Sin razón especificada"
            
            # Cachear nombres de usuarios para evitar múltiples queries
            rejected_by_name = 'Sistema'
            if state_request.approved_by:
                rejected_by_name = state_request.approved_by.get_full_name()
            
            requested_by_name = 'Sistema'
            if state_request.requested_by:
                requested_by_name = state_request.requested_by.get_full_name()
            
            # Notificar al técnico que solicitó el cambio
            if state_request.requested_by:
                cls._enviar_notificacion_tecnico(
                    ticket, 'cambio_estado_rechazado',
                    'Solicitud de cambio de estado rechazada',
                    f'Su solicitud para cambiar el estado del ticket #{ticket_pk} a "{to_state_nombre}" ha sido rechazada. Razón: {rejection_reason}',
                    resultados,
                    usuario_destino=state_request.requested_by,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'rejected_by': rejected_by_name,
                        'rejection_reason': rejection_reason
                    }
                )
            
            # Notificar al cliente sobre el rechazo del cambio
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'cambio_estado_rechazado',
                    'Solicitud de cambio de estado rechazada',
                    f'La solicitud para cambiar el estado del ticket #{ticket_pk} "{ticket_titulo}" a "{to_state_nombre}" ha sido rechazada. El ticket permanecerá en "{from_state_nombre}".',
                    resultados,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'rejected_by': rejected_by_name,
                        'rejection_reason': rejection_reason
                    }
                )
            
            # Notificar al administrador que rechazó el cambio
            if state_request.approved_by:
                cls._enviar_notificacion_admin(
                    ticket, 'cambio_estado_rechazado',
                    'Cambio de estado rechazado',
                    f'Ha rechazado el cambio de estado del ticket #{ticket_pk} de "{from_state_nombre}" a "{to_state_nombre}". Razón: {rejection_reason}',
                    resultados,
                    usuario_destino=state_request.approved_by,
                    datos_adicionales={
                        'state_request_id': state_request.id,
                        'from_state': from_state_nombre,
                        'to_state': to_state_nombre,
                        'requested_by': requested_by_name,
                        'rejection_reason': rejection_reason
                    }
                )
                
        except Exception as e:
            logger.error(f"Error enviando rechazo de cambio de estado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_ticket_cerrado(cls, ticket: Ticket, state_request=None) -> Dict[str, Any]:
        resultados = {
            'emails_enviados': 0,
            'emails_fallidos': 0,
            'notificaciones_internas': 0,
            'errores': []
        }
        
        try:
            # Obtener información del estado anterior y mensaje de aprobación
            estado_anterior = state_request.from_state.nombre if state_request else "Estado Anterior"
            estado_final = ticket.estado.nombre
            approved_by = state_request.approved_by.get_full_name() if state_request and state_request.approved_by else "Administrador"
            approval_message = state_request.reason if state_request else None
            
            # Notificar al cliente
            if ticket.cliente:
                cls._enviar_notificacion_cliente(
                    ticket, 'ticket_cerrado',
                    'Ticket finalizado',
                    f'Su ticket #{ticket.pk} "{ticket.titulo}" ha sido finalizado exitosamente.',
                    resultados,
                    datos_adicionales={
                        'estado_anterior': estado_anterior,
                        'estado_final': estado_final,
                        'approved_by': approved_by,
                        'approval_message': approval_message,
                        'fecha_cierre': ticket.estado.updated_at if hasattr(ticket.estado, 'updated_at') else None
                    }
                )
            
            # Notificar al técnico
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket, 'ticket_cerrado',
                    'Ticket finalizado',
                    f'El ticket #{ticket.pk} "{ticket.titulo}" que tenía asignado ha sido finalizado exitosamente.',
                    resultados,
                    datos_adicionales={
                        'estado_anterior': estado_anterior,
                        'estado_final': estado_final,
                        'approved_by': approved_by,
                        'approval_message': approval_message,
                        'fecha_cierre': ticket.estado.updated_at if hasattr(ticket.estado, 'updated_at') else None
                    }
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket cerrado: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def enviar_tecnico_cambiado(cls, ticket: Ticket, tecnico_anterior: Optional[User]) -> Dict[str, Any]:
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
                    usuario_destino=tecnico_anterior,
                    datos_adicionales={
                        'old_technician': {
                            'id': tecnico_anterior.pk,
                            'nombre': tecnico_anterior.get_full_name(),
                            'email': tecnico_anterior.email,
                            'documento': tecnico_anterior.document,
                            'telefono': tecnico_anterior.number
                        },
                        'new_technician': {
                            'id': ticket.tecnico.pk,
                            'nombre': ticket.tecnico.get_full_name(),
                            'email': ticket.tecnico.email,
                            'documento': ticket.tecnico.document,
                            'telefono': ticket.tecnico.number
                        }
                    }
                )
            
            if ticket.tecnico:
                cls._enviar_notificacion_tecnico(
                    ticket, 'tecnico_cambiado',
                    'Ticket reasignado',
                    'Se le ha asignado un ticket que estaba con otro técnico.',
                    resultados,
                    datos_adicionales={
                        'old_technician': {
                            'id': tecnico_anterior.pk,
                            'nombre': tecnico_anterior.get_full_name(),
                            'email': tecnico_anterior.email,
                            'documento': tecnico_anterior.document,
                            'telefono': tecnico_anterior.number
                        } if tecnico_anterior else None,
                        'new_technician': {
                            'id': ticket.tecnico.pk,
                            'nombre': ticket.tecnico.get_full_name(),
                            'email': ticket.tecnico.email,
                            'documento': ticket.tecnico.document,
                            'telefono': ticket.tecnico.number
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de cambio de técnico: {e}")
            resultados['errores'].append(str(e))
        
        return resultados
    
    @classmethod
    def _enviar_notificacion_cliente(cls, ticket: Ticket, tipo_codigo: str, titulo: str, 
                                   mensaje: str, resultados: Dict, usuario_destino: User = None,
                                   datos_adicionales: Dict = None):
        usuario = usuario_destino or ticket.cliente
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_tecnico(cls, ticket: Ticket, tipo_codigo: str, titulo: str,
                                   mensaje: str, resultados: Dict, usuario_destino: User = None,
                                   datos_adicionales: Dict = None):
        usuario = usuario_destino or ticket.tecnico
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_admin(cls, ticket: Ticket, tipo_codigo: str, titulo: str,
                                 mensaje: str, resultados: Dict, usuario_destino: User = None,
                                 datos_adicionales: Dict = None):
        usuario = usuario_destino or ticket.administrador
        cls._enviar_notificacion_completa(
            usuario, ticket, tipo_codigo, titulo, mensaje, resultados, datos_adicionales
        )
    
    @classmethod
    def _enviar_notificacion_completa(cls, usuario: User, ticket: Ticket, tipo_codigo: str,
                                    titulo: str, mensaje: str, resultados: Dict,
                                    datos_adicionales: Dict = None):
        if not cls._validar_usuario_para_notificacion(usuario):
            logger.warning(f"Usuario inválido para notificación: {usuario}")
            return
        cls._crear_notificacion_interna(
            usuario, ticket, tipo_codigo, titulo, mensaje, datos_adicionales
        )
        resultados['notificaciones_internas'] += 1
        
        # Enviar email
        try:
            if datos_adicionales:
                ticket._notification_data = datos_adicionales
            cls._enviar_email(usuario, ticket, tipo_codigo, titulo, mensaje)
            resultados['emails_enviados'] += 1
        except Exception as e:
            logger.error(f"Error enviando email a {usuario.email}: {e}")
            resultados['emails_fallidos'] += 1
            resultados['errores'].append(f"Email fallido para {usuario.email}: {str(e)}")
    
    @classmethod
    def _crear_notificacion_interna(cls, usuario: User, ticket: Ticket, tipo_codigo: str,
                                  titulo: str, mensaje: str, datos_adicionales: Dict = None):
        try:
            # Optimización: usar only() para obtener solo los campos necesarios
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
            
            # Optimización: crear notificación con bulk_create si hay múltiples, o create si es una sola
            notification = Notification.objects.create(
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
            'datos_adicionales': getattr(ticket, '_notification_data', {}),
        }
        
        try:
            html_content = render_to_string(template_html, context)
            text_content = cls._generar_contenido_texto_plano(usuario, ticket, titulo, mensaje)

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com'),
                to=[usuario.email]
            )
            email.attach_alternative(html_content, "text/html")

            def _send():
                max_retries = 3
                retry_delay = 2  # segundos
                
                for attempt in range(max_retries):
                    try:
                        # Usar connection con timeout configurado
                        from django.core.mail import get_connection
                        connection = get_connection(
                            timeout=getattr(settings, 'EMAIL_TIMEOUT', 30)
                        )
                        email.connection = connection
                        email.send()
                        logger.info(f"Email enviado exitosamente a {usuario.email} (intento {attempt + 1})")
                        return  # Éxito, salir del loop
                    except (SMTPException, SMTPServerDisconnected, ConnectionError, TimeoutError, socket.error, OSError) as e:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(f"Error de conexión SMTP para {usuario.email} (intento {attempt + 1}/{max_retries}): {e}. Reintentando en {wait_time} segundos...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Error enviando email para {usuario.email} después de {max_retries} intentos: {e}")
                            try:
                                cls._enviar_email_texto_plano(usuario, ticket, titulo, mensaje)
                            except Exception as e2:
                                logger.error(f"Fallback texto plano falló para {usuario.email}: {e2}")
                    except Exception as e:
                        logger.error(f"Error inesperado enviando email a {usuario.email}: {e}")
                        # No reintentar para errores no relacionados con conexión
                        break

            Thread(target=_send, daemon=True).start()

        except Exception as e:
            logger.error(f"Error preparando email para {usuario.email}: {e}")
            try:
                cls._enviar_email_texto_plano(usuario, ticket, titulo, mensaje)
            except Exception:
                logger.error(f"No se pudo enviar email ni fallback para {usuario.email}")
    
    @classmethod
    def _obtener_plantilla_html(cls, usuario: User, tipo_codigo: str) -> str:
        plantillas = {
            (User.Role.CLIENT, 'ticket_creado'): 'emails/ticket_created_client.html',
            (User.Role.CLIENT, 'estado_cambiado'): 'emails/ticket_state_changed_client.html',
            (User.Role.CLIENT, 'ticket_finalizado'): 'emails/ticket_state_changed_client.html',
            (User.Role.CLIENT, 'ticket_cerrado'): 'emails/ticket_closed_client.html',
            (User.Role.TECH, 'ticket_creado'): 'emails/ticket_created_technician.html',
            (User.Role.TECH, 'ticket_asignado'): 'emails/ticket_assigned_technician.html',
            (User.Role.TECH, 'ticket_finalizado'): 'emails/ticket_created_technician.html',
            (User.Role.TECH, 'ticket_cerrado'): 'emails/ticket_created_technician.html',
            (User.Role.TECH, 'tecnico_cambiado'): 'emails/technician_changed.html',
            (User.Role.TECH, 'cambio_estado_aprobado'): 'emails/state_change_approved_technician.html',
            (User.Role.TECH, 'cambio_estado_rechazado'): 'emails/state_change_rejected_technician.html',
            (User.Role.ADMIN, 'ticket_creado'): 'emails/ticket_created_admin.html',
            (User.Role.ADMIN, 'solicitud_finalizacion'): 'emails/ticket_created_admin.html',
            (User.Role.ADMIN, 'solicitud_cambio_estado'): 'emails/state_change_request_admin.html',
        }
        
        plantilla = plantillas.get((usuario.role, tipo_codigo))
        if not plantilla:
            if usuario.role == User.Role.CLIENT:
                plantilla = 'emails/ticket_created_client.html'
            elif usuario.role == User.Role.TECH:
                plantilla = 'emails/ticket_created_technician.html'
            elif usuario.role == User.Role.ADMIN:
                plantilla = 'emails/ticket_created_admin.html'
            else:
                plantilla = 'emails/ticket_created_client.html'
        return plantilla
    
    @classmethod
    def _generar_contenido_texto_plano(cls, usuario: User, ticket: Ticket, titulo: str, mensaje: str) -> str:
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
        subject = f"{titulo} - Ticket #{ticket.pk}"
        text_content = cls._generar_contenido_texto_plano(usuario, ticket, titulo, mensaje)
        
        try:
            # Usar connection con timeout configurado
            from django.core.mail import get_connection
            connection = get_connection(
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 30)
            )
            send_mail(
                subject=subject,
                message=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tickethelp.com'),
                recipient_list=[usuario.email],
                fail_silently=False,
                connection=connection
            )
        except Exception as e:
            logger.error(f"Error enviando email de texto plano a {usuario.email}: {e}")
            raise
    
    @classmethod
    def _validar_usuario_para_notificacion(cls, usuario: User) -> bool:
        """
        Valida que un usuario sea válido para recibir notificaciones.
        Reutiliza patrones de validación del proyecto.
        """
        try:
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
            
            if '@' not in usuario.email or '.' not in usuario.email.split('@')[-1]:
                logger.warning(f"Email {usuario.email} tiene formato inválido")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando usuario para notificación: {e}")
            return False
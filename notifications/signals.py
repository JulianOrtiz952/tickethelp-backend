"""
Signals para integrar notificaciones con el flujo de tickets.
Se ejecutan automáticamente cuando ocurren eventos en los tickets.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from tickets.models import Ticket
from .services import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def ticket_created_notification(sender, instance, created, **kwargs):
    """
    Envía notificaciones cuando se crea un nuevo ticket.
    """
    if created:
        try:
            logger.info(f"Enviando notificaciones para ticket creado: #{instance.pk}")
            resultados = NotificationService.enviar_notificacion_ticket_creado(instance)
            
            logger.info(f"Notificaciones enviadas - Emails: {resultados['emails_enviados']}, "
                       f"Internas: {resultados['notificaciones_internas']}, "
                       f"Errores: {len(resultados['errores'])}")
            
            if resultados['errores']:
                logger.warning(f"Errores en notificaciones: {resultados['errores']}")
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones de ticket creado: {e}")


@receiver(pre_save, sender=Ticket)
def ticket_state_change_notification(sender, instance, **kwargs):
    """
    Envía notificaciones cuando cambia el estado de un ticket.
    """
    if instance.pk:  # Solo para tickets existentes
        try:
            # Obtener el estado anterior
            estado_anterior = Ticket.objects.get(pk=instance.pk).estado.nombre
            
            # Verificar si el estado cambió
            if estado_anterior != instance.estado.nombre:
                logger.info(f"Estado del ticket #{instance.pk} cambió de '{estado_anterior}' a '{instance.estado.nombre}'")
                
                # Enviar notificación de cambio de estado
                resultados = NotificationService.enviar_notificacion_estado_cambiado(
                    instance, estado_anterior
                )
                
                logger.info(f"Notificaciones de cambio de estado enviadas - "
                           f"Emails: {resultados['emails_enviados']}, "
                           f"Internas: {resultados['notificaciones_internas']}")
                
                # Si el estado es "finalizado", enviar notificación especial
                if instance.estado.codigo == 'finalizado':
                    logger.info(f"Ticket #{instance.pk} marcado como finalizado")
                    resultados_finalizado = NotificationService.enviar_ticket_finalizado(instance)
                    
                    logger.info(f"Notificaciones de finalización enviadas - "
                               f"Emails: {resultados_finalizado['emails_enviados']}, "
                               f"Internas: {resultados_finalizado['notificaciones_internas']}")
                
        except Ticket.DoesNotExist:
            # El ticket no existe aún, es una creación
            pass
        except Exception as e:
            logger.error(f"Error enviando notificaciones de cambio de estado: {e}")


@receiver(pre_save, sender=Ticket)
def ticket_technician_change_notification(sender, instance, **kwargs):
    """
    Envía notificaciones cuando se cambia el técnico asignado.
    """
    if instance.pk:
        try:
            ticket_anterior = Ticket.objects.get(pk=instance.pk)
            # Guardar técnico anterior en el objeto para usarlo después del save
            instance._previous_tecnico = ticket_anterior.tecnico
        except Ticket.DoesNotExist:
            instance._previous_tecnico = None
        except Exception as e:
            logger.error(f"Error leyendo ticket anterior para cambio de técnico: {e}")


# Función auxiliar para enviar solicitud de finalización
def enviar_solicitud_finalizacion(ticket):
    """
    Función auxiliar para enviar solicitud de finalización.
    Se puede llamar desde las vistas cuando el técnico solicita finalizar un ticket.
    """
    try:
        logger.info(f"Enviando solicitud de finalización para ticket #{ticket.pk}")
        resultados = NotificationService.enviar_solicitud_finalizacion(ticket)
        
        logger.info(f"Solicitud de finalización enviada - "
                   f"Emails: {resultados['emails_enviados']}, "
                   f"Internas: {resultados['notificaciones_internas']}")
        
        return resultados
        
    except Exception as e:
        logger.error(f"Error enviando solicitud de finalización: {e}")
        return {'errores': [str(e)]}


@receiver(post_save, sender=Ticket)
def ticket_technician_changed_post_save(sender, instance, created, **kwargs):
    """Enviar notificaciones de técnico cambiado después de guardar el ticket."""
    if created:
        return

    prev = getattr(instance, '_previous_tecnico', None)
    try:
        if prev != instance.tecnico:
            logger.info(f"(post_save) Técnico del ticket #{instance.pk} cambió de "
                       f"{prev.email if prev else 'Ninguno'} "
                       f"a {instance.tecnico.email if instance.tecnico else 'Ninguno'}")

            resultados = NotificationService.enviar_tecnico_cambiado(instance, prev)
            logger.info(f"Notificaciones de cambio de técnico enviadas - "
                       f"Emails: {resultados.get('emails_enviados', 0)}, "
                       f"Internas: {resultados.get('notificaciones_internas', 0)}")
    except Exception as e:
        logger.error(f"Error en post_save enviando notificaciones de cambio de técnico: {e}")

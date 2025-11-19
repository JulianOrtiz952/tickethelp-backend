from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import json

class Estado(models.Model):
    # Identifica el estado por clave corta y nombre legible
    codigo    = models.SlugField(max_length=32, unique=True)  
    nombre    = models.CharField(max_length=60, unique=True)
    es_activo = models.BooleanField(default=True)  
    es_final  = models.BooleanField(default=False) 

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Ticket(models.Model):
    # Relaciones según tu MER
    administrador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name="tickets_administrados",
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name="tickets_asignados",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name="tickets_de_cliente",
    )

    estado = models.ForeignKey(
        Estado,
        on_delete=models.PROTECT,   # evita borrar estados usados
        related_name="tickets",
    )

    # Campos propios del ticket
    titulo       = models.CharField(max_length=200)
    descripcion  = models.TextField(blank=True)
    equipo       = models.CharField(max_length=120, blank=True)    
    fecha        = models.DateTimeField(default=timezone.now)     
    creado_en    = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["creado_en"]),
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return f"[#{self.pk}] {self.titulo} · {self.estado.nombre}"

    @property
    def es_activo(self) -> bool:
        return bool(getattr(self.estado, "es_activo", False))


class StateChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='state_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='state_requests_made')
    from_state = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='requests_from')
    to_state = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='requests_to')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='state_requests_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Solicitud de Cambio de Estado"
        verbose_name_plural = "Solicitudes de Cambio de Estado"

    def __str__(self):
        return f"Solicitud #{self.pk} - Ticket #{self.ticket.pk}: {self.from_state.nombre} → {self.to_state.nombre}"

# =============================================================================
# HU13B - Historial: Modelo para el historial de cambios de estado del ticket
# =============================================================================
# Este modelo almacena el historial de cambios de estado de un ticket   
# Esto cubre tus criterios de aceptación:
# - guarda el estado, el técnico, quién hizo el cambio y cuándo;
# - se borra si se borra el ticket (on_delete=models.CASCADE);
# - es independiente del ticket principal (para poder consultarlo).
# =============================================================================

class TicketHistory(models.Model):
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='historial')
    estado = models.CharField(max_length=50)
    estado_anterior = models.CharField(max_length=50, null=True, blank=True)
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='historiales_como_tecnico')
    tecnico_anterior = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='historiales_como_tecnico_anterior')
    accion = models.CharField(max_length=200)
    fecha = models.DateTimeField(auto_now_add=True)
    realizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='acciones_realizadas')
    # Campos para guardar datos de creación del ticket
    datos_ticket = models.JSONField(null=True, blank=True, help_text="Datos del ticket al momento de la acción")

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Historial de Ticket"
        verbose_name_plural = "Historiales de Tickets"
        indexes = [
            models.Index(fields=['ticket', '-fecha']),
        ]

    def __str__(self):
        return f"Historial #{self.id} - Ticket #{self.ticket.id} - {self.accion} ({self.fecha})"
    
    @staticmethod
    def crear_entrada_historial(ticket, accion, realizado_por, estado_anterior=None, tecnico_anterior=None, datos_ticket=None):
        """
        Método helper para crear entradas en el historial.
        """
        # Preparar datos del ticket si se proporcionan
        if datos_ticket is None:
            datos_ticket = {
                'titulo': ticket.titulo,
                'descripcion': ticket.descripcion,
                'equipo': ticket.equipo,
                'administrador': ticket.administrador.document if ticket.administrador else None,
                'cliente': ticket.cliente.document if ticket.cliente else None,
            }
        
        return TicketHistory.objects.create(
            ticket=ticket,
            estado=ticket.estado.nombre if ticket.estado else 'Sin estado',
            estado_anterior=estado_anterior,
            tecnico=ticket.tecnico,
            tecnico_anterior=tecnico_anterior,
            accion=accion,
            realizado_por=realizado_por,
            datos_ticket=datos_ticket
        )


# =============================================================================
# HU13B - Historial: Signal para rastrear cambios previos
# =============================================================================
# Este signal almacena el estado anterior antes de un cambio para poder
# comparar en post_save si hubo cambios reales
# =============================================================================

@receiver(pre_save, sender=Ticket)
def store_previous_values(sender, instance, **kwargs):
    """Almacena valores anteriores antes de guardar para comparar cambios"""
    if instance.pk:
        try:
            old_instance = Ticket.objects.get(pk=instance.pk)
            instance._old_estado = old_instance.estado
            instance._old_tecnico = old_instance.tecnico
        except Ticket.DoesNotExist:
            instance._old_estado = None
            instance._old_tecnico = None
    else:
        instance._old_estado = None
        instance._old_tecnico = None

    
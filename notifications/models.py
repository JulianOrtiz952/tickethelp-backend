from django.db import models
from django.conf import settings
from django.utils import timezone


class NotificationType(models.Model):
    """
    Tipos de notificaciones del sistema.
    Define los diferentes tipos de eventos que pueden generar notificaciones.
    """
    codigo = models.SlugField(max_length=50, unique=True, help_text="Código único del tipo de notificación")
    nombre = models.CharField(max_length=100, help_text="Nombre descriptivo del tipo")
    descripcion = models.TextField(blank=True, help_text="Descripción detallada del tipo de notificación")
    es_activo = models.BooleanField(default=True, help_text="Indica si este tipo está activo")
    
    # Configuración de destinatarios
    enviar_a_cliente = models.BooleanField(default=False, help_text="Se envía al cliente del ticket")
    enviar_a_tecnico = models.BooleanField(default=False, help_text="Se envía al técnico asignado")
    enviar_a_admin = models.BooleanField(default=False, help_text="Se envía al administrador")
    
    class Meta:
        verbose_name = "Tipo de Notificación"
        verbose_name_plural = "Tipos de Notificaciones"
        ordering = ["nombre"]
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Notification(models.Model):
    """
    Modelo principal para almacenar las notificaciones del sistema.
    Cada notificación está asociada a un usuario y un ticket específico.
    """
    
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADA = 'ENVIADA', 'Enviada'
        LEIDA = 'LEIDA', 'Leída'
        FALLIDA = 'FALLIDA', 'Fallida'
    
    # Relaciones principales
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        help_text="Usuario destinatario de la notificación"
    )
    
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name="notificaciones",
        null=True,
        blank=True,
        help_text="Ticket relacionado con la notificación"
    )
    
    tipo = models.ForeignKey(
        NotificationType,
        on_delete=models.PROTECT,
        related_name="notificaciones",
        help_text="Tipo de notificación"
    )
    
    # Contenido de la notificación
    titulo = models.CharField(max_length=200, help_text="Título de la notificación")
    mensaje = models.TextField(help_text="Contenido del mensaje")
    
    # Metadatos
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        help_text="Estado actual de la notificación"
    )
    
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de creación de la notificación"
    )
    
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de envío de la notificación"
    )
    
    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de lectura de la notificación"
    )
    
    # Campos adicionales para contexto
    datos_adicionales = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos adicionales en formato JSON para contexto"
    )
    
    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["usuario", "estado"]),
            models.Index(fields=["fecha_creacion"]),
            models.Index(fields=["ticket", "tipo"]),
        ]
    
    def __str__(self):
        return f"[{self.tipo.codigo}] {self.titulo} - {self.usuario.email}"
    
    def marcar_como_enviada(self):
        """Marca la notificación como enviada y registra la fecha de envío."""
        self.estado = self.Estado.ENVIADA
        self.fecha_envio = timezone.now()
        self.save(update_fields=['estado', 'fecha_envio'])
    
    def marcar_como_leida(self):
        """Marca la notificación como leída y registra la fecha de lectura."""
        self.estado = self.Estado.LEIDA
        self.fecha_lectura = timezone.now()
        self.save(update_fields=['estado', 'fecha_lectura'])
    
    def marcar_como_fallida(self):
        """Marca la notificación como fallida."""
        self.estado = self.Estado.FALLIDA
        self.save(update_fields=['estado'])
    
    @property
    def es_leida(self):
        """Indica si la notificación ha sido leída."""
        return self.estado == self.Estado.LEIDA
    
    @property
    def es_pendiente(self):
        """Indica si la notificación está pendiente de envío."""
        return self.estado == self.Estado.PENDIENTE
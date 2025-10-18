from django.db import models
from django.conf import settings
from django.utils import timezone


class NotificationType(models.Model):
    codigo = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    es_activo = models.BooleanField(default=True)

    enviar_a_cliente = models.BooleanField(default=False)
    enviar_a_tecnico = models.BooleanField(default=False)
    enviar_a_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tipo de Notificación"
        verbose_name_plural = "Tipos de Notificaciones"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Notification(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENVIADA = 'ENVIADA', 'Enviada'
        LEIDA = 'LEIDA', 'Leída'
        FALLIDA = 'FALLIDA', 'Fallida'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    destinatarios = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='notificaciones_recibidas', blank=True)
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name="notificaciones", null=True, blank=True)
    tipo = models.ForeignKey(NotificationType, on_delete=models.PROTECT, related_name="notificaciones")

    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    descripcion = models.TextField(blank=True)

    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='notificaciones_enviadas')
    enviado_por_role = models.CharField(max_length=20, blank=True, null=True)

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    datos_adicionales = models.JSONField(default=dict, blank=True)

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
        self.estado = self.Estado.ENVIADA
        self.fecha_envio = timezone.now()
        self.save(update_fields=['estado', 'fecha_envio'])

    def marcar_como_leida(self):
        self.estado = self.Estado.LEIDA
        self.fecha_lectura = timezone.now()
        self.save(update_fields=['estado', 'fecha_lectura'])

    def marcar_como_fallida(self):
        self.estado = self.Estado.FALLIDA
        self.save(update_fields=['estado'])

    @property
    def es_leida(self):
        return self.estado == self.Estado.LEIDA

    @property
    def es_pendiente(self):
        return self.estado == self.Estado.PENDIENTE

    def save(self, *args, **kwargs):
        try:
            if self.enviado_por and not self.enviado_por_role:
                self.enviado_por_role = getattr(self.enviado_por, 'role', '') or ''
        except Exception:
            pass
        return super().save(*args, **kwargs)
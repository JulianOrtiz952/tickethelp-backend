from django.db import models
from django.conf import settings
from django.utils import timezone

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
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_administrados",
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_asignados",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
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

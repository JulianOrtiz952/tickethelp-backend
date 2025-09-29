from django.db import models
from django.conf import settings

class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN          = "OPEN", "Abierto"
        DIAGNOSIS     = "DIAGNOSIS", "En diagnóstico"
        IN_REPAIR     = "IN_REPAIR", "En reparación"
        CLOSED        = "CLOSED", "Finalizado"
        CANCELED      = "CANCELED", "Cancelado"

    # Estados considerados "activos"
    ACTIVE_STATES = (Status.OPEN, Status.DIAGNOSIS, Status.IN_REPAIR)

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status      = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    # relacion con users
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_created",
    )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        indexes  = [models.Index(fields=["status"]), models.Index(fields=["created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"[#{self.pk}] {self.title} · {self.status}"

    @property
    def is_active(self) -> bool:
        return self.status in {s.value for s in self.ACTIVE_STATES}

    @classmethod
    def actives(cls):
        return cls.objects.filter(status__in=[s.value for s in cls.ACTIVE_STATES])

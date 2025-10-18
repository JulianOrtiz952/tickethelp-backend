from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN  = 'ADMIN',  'Administrador'
        TECH   = 'TECH',   'Técnico'
        CLIENT = 'CLIENT', 'Cliente'
    
    username = None
    email = models.EmailField(unique=True)
    document = models.CharField(max_length=10, unique=True, primary_key=True)
    number    = models.CharField(max_length=15, blank=True, null=True)
    role      = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    is_active = models.BooleanField(default=True)
    profile_picture = models.URLField(blank=True, null=True, max_length=500)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def has_active_tickets(self):
        from tickets.models import Ticket
        return Ticket.objects.filter(
            models.Q(tecnico=self) | models.Q(cliente=self) | models.Q(administrador=self)
        ).exclude(estado__codigo__in=['closed', 'canceled']).exists()

# Maneja los managers para cada rol
class _RoleQS(models.Manager):
    ROLE = None
    def get_queryset(self):
        return super().get_queryset().filter(role=self.ROLE)

class AdminManager(_RoleQS):   ROLE = User.Role.ADMIN
class TechManager(_RoleQS):    ROLE = User.Role.TECH
class ClientManager(_RoleQS):  ROLE = User.Role.CLIENT

class Admin(User):
    objects = AdminManager()
    class Meta:
        proxy = True
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"
    def save(self, *args, **kwargs):
        self.role = User.Role.ADMIN
        return super().save(*args, **kwargs)

class Technician(User):
    objects = TechManager()
    class Meta:
        proxy = True
        verbose_name = "Técnico"
        verbose_name_plural = "Técnicos"
    def save(self, *args, **kwargs):
        self.role = User.Role.TECH
        return super().save(*args, **kwargs)

class Client(User):
    objects = ClientManager()
    class Meta:
        proxy = True
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
    def save(self, *args, **kwargs):
        self.role = User.Role.CLIENT
        return super().save(*args, **kwargs)
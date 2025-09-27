from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
class CustomUserManager(DjangoUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    class Role(models.TextChoices):
        ADMIN  = 'ADMIN',  'Administrador'
        TECH   = 'TECH',   'Técnico'
        CLIENT = 'CLIENT', 'Cliente'

    number    = models.CharField(max_length=15, blank=True, null=True)
    role      = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    #def has_active_tickets(self) -> bool:
        #from django.db.models import Q
        #from tickets.models import Ticket
        #return Ticket.objects.filter(
            #Q(assigned_to=self) | Q(created_by=self)
        #).exclude(status=Ticket.Status.CLOSED).exists()

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
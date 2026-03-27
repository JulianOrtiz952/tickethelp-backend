import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickethelp.settings')
django.setup()

from users.models import User, Admin, Technician, Client
from django.db import transaction

def create_users():
    with transaction.atomic():
        print("Forzando actualización de usuarios...")
        
        # Administrador
        admin, _ = Admin.objects.get_or_create(document="9000000001")
        admin.email = "admin@test.com"
        admin.first_name = "Admin"
        admin.last_name = "Prueba"
        admin.is_active = True
        admin.must_change_password = False
        admin.set_password("Admin123*")
        admin.save()
        print("Administrador actualizado: admin@test.com / Admin123*")
            
        # Técnico
        tech, _ = Technician.objects.get_or_create(document="9000000002")
        tech.email = "tecnico@test.com"
        tech.first_name = "Técnico"
        tech.last_name = "Prueba"
        tech.is_active = True
        tech.must_change_password = False
        tech.set_password("Tecnico123*")
        tech.save()
        print("Técnico actualizado: tecnico@test.com / Tecnico123*")
            
        # Cliente
        client, _ = Client.objects.get_or_create(document="9000000003")
        client.email = "cliente@test.com"
        client.first_name = "Cliente"
        client.last_name = "Prueba"
        client.is_active = True
        client.must_change_password = False
        client.set_password("Cliente123*")
        client.save()
        print("Cliente actualizado: cliente@test.com / Cliente123*")
            
if __name__ == "__main__":
    create_users()

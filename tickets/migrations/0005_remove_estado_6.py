# Generated manually to remove estado 6 (trial_pending_approval)

from django.db import migrations


def migrate_tickets_from_estado_6_to_4(apps, schema_editor):
    """
    Migra tickets que están en estado 6 (trial_pending_approval) al estado 4 (trial).
    También actualiza las StateChangeRequest que referencian al estado 6.
    """
    Estado = apps.get_model('tickets', 'Estado')
    Ticket = apps.get_model('tickets', 'Ticket')
    StateChangeRequest = apps.get_model('tickets', 'StateChangeRequest')
    
    try:
        estado_6 = Estado.objects.get(pk=6, codigo='trial_pending_approval')
        estado_4 = Estado.objects.get(pk=4, codigo='trial')
        
        # Migrar tickets del estado 6 al estado 4
        tickets_afectados = Ticket.objects.filter(estado=estado_6)
        count = tickets_afectados.update(estado=estado_4)
        print(f"Migrados {count} tickets del estado 6 al estado 4")
        
        # Actualizar StateChangeRequest que referencian al estado 6 como from_state
        requests_from = StateChangeRequest.objects.filter(from_state=estado_6)
        count_from = requests_from.update(from_state=estado_4)
        print(f"Actualizadas {count_from} StateChangeRequest con from_state=6")
        
        # Actualizar StateChangeRequest que referencian al estado 6 como to_state
        requests_to = StateChangeRequest.objects.filter(to_state=estado_6)
        count_to = requests_to.update(to_state=estado_4)
        print(f"Actualizadas {count_to} StateChangeRequest con to_state=6")
        
    except Estado.DoesNotExist:
        # Si el estado 6 no existe, no hay nada que migrar
        print("El estado 6 no existe, no hay nada que migrar")


def reverse_migration(apps, schema_editor):
    """
    Función de reversión (no se puede revertir completamente porque el estado 6 se elimina).
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_statechangerequest'),
    ]

    operations = [
        migrations.RunPython(
            migrate_tickets_from_estado_6_to_4,
            reverse_migration
        ),
        migrations.RunSQL(
            # Eliminar el estado 6 de la base de datos
            sql="DELETE FROM tickets_estado WHERE id = 6 AND codigo = 'trial_pending_approval';",
            reverse_sql="-- No se puede revertir la eliminación del estado 6"
        ),
    ]


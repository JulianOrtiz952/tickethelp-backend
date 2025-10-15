"""
Comando de Django para inicializar los tipos de notificaciones.
Ejecutar: python manage.py init_notification_types
"""
from django.core.management.base import BaseCommand
from notifications.models import NotificationType
from notifications.config import NotificationConfig


class Command(BaseCommand):
    help = 'Inicializa los tipos de notificaciones en la base de datos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la actualización de tipos existentes',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        created_count = 0
        updated_count = 0
        
        self.stdout.write('Inicializando tipos de notificaciones...')
        
        for codigo, config in NotificationConfig.NOTIFICATION_TYPES.items():
            notification_type, created = NotificationType.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': config['nombre'],
                    'descripcion': config['descripcion'],
                    'enviar_a_cliente': config['enviar_a_cliente'],
                    'enviar_a_tecnico': config['enviar_a_tecnico'],
                    'enviar_a_admin': config['enviar_a_admin'],
                    'es_activo': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'[OK] Creado: {notification_type.nombre}')
                )
            elif force:
                # Actualizar configuración existente
                notification_type.nombre = config['nombre']
                notification_type.descripcion = config['descripcion']
                notification_type.enviar_a_cliente = config['enviar_a_cliente']
                notification_type.enviar_a_tecnico = config['enviar_a_tecnico']
                notification_type.enviar_a_admin = config['enviar_a_admin']
                notification_type.es_activo = True
                notification_type.save()
                
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'[UPD] Actualizado: {notification_type.nombre}')
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(f'[EXISTS] Ya existe: {notification_type.nombre}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nResumen: {created_count} creados, {updated_count} actualizados'
            )
        )

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'Sistema de Notificaciones'
    
    def ready(self):
        """
        Método que se ejecuta cuando la aplicación está lista.
        Aquí se pueden registrar signals y otras configuraciones.
        """
        # Importar signals para que se registren automáticamente
        try:
            import notifications.signals
        except ImportError:
            pass
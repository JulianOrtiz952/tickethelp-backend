"""
Backend personalizado de email para manejar problemas de certificado SSL en desarrollo.
En producción, se debe usar el backend estándar de Django.
"""
import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.conf import settings


class CustomSMTPEmailBackend(SMTPEmailBackend):
    """
    Backend SMTP personalizado que desactiva la verificación SSL en desarrollo.
    
    Solo usar en desarrollo. En producción, usar el backend estándar de Django.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Desactivar verificación SSL solo si estamos en modo DEBUG
        if getattr(settings, 'DEBUG', False):
            # Crear un contexto SSL que no verifica el certificado
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def open(self):
        """
        Abre la conexión SMTP con el contexto SSL personalizado si estamos en DEBUG.
        """
        if self.connection:
            return False
        
        # Obtener timeout de settings si está configurado, sino usar el default
        timeout = getattr(settings, 'EMAIL_TIMEOUT', self.timeout or 30)
        
        try:
            # Si estamos en DEBUG y hay un contexto SSL personalizado
            if getattr(settings, 'DEBUG', False) and hasattr(self, 'ssl_context'):
                self.connection = self.connection_class(
                    self.host, self.port, timeout=timeout
                )
                if self.use_tls:
                    self.connection.starttls(context=self.ssl_context)
                if self.username and self.password:
                    self.connection.login(self.username, self.password)
            else:
                # Comportamiento estándar para producción
                self.connection = self.connection_class(
                    self.host, self.port, timeout=timeout
                )
                if self.use_tls:
                    self.connection.starttls()
                if self.username and self.password:
                    self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise


# Guía de Despliegue en Coolify

Este documento explica cómo configurar Coolify para desplegar correctamente el backend de **TicketHelp** usando Dockerfile.

## Configuración del Servicio en Coolify

Cuando crees el recurso en Coolify, configúralo con los siguientes valores:

- **Build Pack**: `Dockerfile`
- **Base Directory**: `/`
- **Dockerfile Location**: `/Dockerfile`
- **Ports Exposes**: `8000`
- **Install Command**: *(Vacío)*
- **Build Command**: *(Vacío)*
- **Start Command**: *(Vacío)*

> [!NOTE]
> No necesitas configurar un start command porque el comando de inicio, las migraciones de base de datos y la recolección de archivos estáticos son manejados automáticamente por las instrucciones del `Dockerfile`.

## Variables de Entorno en Coolify

Configura las siguientes variables de entorno en la sección **Environment Variables** de Coolify:

```env
SECRET_KEY=clave_segura_generada
DEBUG=False
ALLOWED_HOSTS=rjhuiksgeeoo6z1is7adxnyp.5.78.212.12.sslip.io,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://nnuraz9tktih4odeu6r09ysn.5.78.212.12.sslip.io
CSRF_TRUSTED_ORIGINS=http://nnuraz9tktih4odeu6r09ysn.5.78.212.12.sslip.io,http://rjhuiksgeeoo6z1is7adxnyp.5.78.212.12.sslip.io
```

### Base de Datos PostgreSQL (Opcional)

Si utilizas PostgreSQL para producción, añade la siguiente variable:

```env
DATABASE_URL=postgresql://usuario:password@host:puerto/base_de_datos
```

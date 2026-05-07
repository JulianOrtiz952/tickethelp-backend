# Ticket-Help - Backend (Django REST Framework)

Este es el repositorio del backend para **Ticket-Help**, un sistema de gestión de requerimientos y soporte técnico diseñado para digitalizar y optimizar la atención de equipos. La API está construida con Django REST Framework y proporciona una base sólida, segura y escalable para las operaciones del sistema.

## Propósito

Servir como el núcleo de lógica de negocio y persistencia de datos para la aplicación Ticket-Help. Facilita la gestión de usuarios, la trazabilidad de tickets, la gestión de estados y la generación de notificaciones, asegurando que la información sea íntegra y accesible solo para los usuarios autorizados.

## Características Principales

- **API RESTful:** Endpoints estructurados para todas las operaciones de la entidad.
- **Autenticación JWT:** Seguridad robusta utilizando JSON Web Tokens.
- **Gestión de Roles:** Lógica de permisos basada en roles (Administrador, Técnico, Cliente).
- **Historial Automatizado:** Seguimiento detallado de cada cambio en los tickets.
- **Sistema de Notificaciones:** Integración para alertas en tiempo real.
- **Validación de Datos:** Capa de serialización estricta para asegurar la calidad de la información.

## Arquitectura del Sistema

El backend utiliza el siguiente stack:

- **Framework:** Django 5.0.6
- **API Framework:** Django REST Framework 3.15.1
- **Base de Datos:** PostgreSQL (psycopg 3)
- **Autenticación:** Simple JWT 5.5.1
- **Servicios Externos:** SendGrid (Emails), AWS S3 (Almacenamiento de adjuntos)

### Estructura de Aplicaciones (Apps)

- `users/`: Manejo de usuarios personalizados, autenticación y perfiles por rol.
- `tickets/`: Lógica central de tickets, estados, historial y adjuntos.
- `notifications/`: Gestión de alertas y mensajes del sistema.
- `reports/`: Generación de métricas y reportes de desempeño.

## Estructura del Proyecto

```
tickethelp-backend/
├── tickethelp/          # Configuración principal del proyecto
│   ├── settings.py      # Ajustes de Django
│   ├── urls.py          # Enrutamiento global
│   └── wsgi.py/asgi.py
├── users/               # App de gestión de usuarios
│   ├── models.py        # Modelo de Usuario con Roles
│   ├── serializers.py
│   └── views.py
├── tickets/             # App de gestión de tickets
│   ├── models.py        # Ticket, Estado, Historial, Adjuntos
│   ├── signals.py       # Automatización de historial y notificaciones
│   └── views.py
├── notifications/       # App de notificaciones
├── reports/             # App de reportes
├── requirements.txt     # Dependencias del proyecto
├── manage.py            # Utilidad de administración de Django
├── .env                 # Variables de entorno (No incluido en Git)
└── procfile             # Configuración para despliegue
```

## Instalación y Configuración

### Prerrequisitos:
- Python 3.10 o superior
- PostgreSQL
- Git

### Pasos de Instalación:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/JulianOrtiz952/tickethelp-backend.git
   cd tickethelp-backend
   ```

2. **Crear y activar entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Linux/macOS
   # venv\Scripts\activate  # En Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Crear un archivo `.env` en la raíz del proyecto y configurar las siguientes variables:
   ```env
   SECRET_KEY=tu_secret_key_aqui
   DEBUG=True
   DATABASE_URL=postgres://usuario:password@localhost:5432/tickethelp
   ```

5. **Ejecutar migraciones:**
   ```bash
   python manage.py migrate
   ```

6. **(Opcional) Crear superusuario o usuarios de prueba:**
   ```bash
   python manage.py createsuperuser
   # O usar el script de prueba si está disponible:
   python manage.py shell < create_test_users.py
   ```

7. **Iniciar servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```
   La API estará disponible en `http://localhost:8000`

## Modelos de Datos Principales

- **User:** Extiende `AbstractUser` para incluir `document`, `role` (Admin, Tech, Client) y `profile_picture`.
- **Ticket:** Almacena la información del servicio, vinculando a los tres roles y un `Estado`.
- **Estado:** Catálogo dinámico de los estados por los que puede pasar un ticket.
- **TicketHistory:** Registro inmutable de cada acción realizada sobre un ticket.
- **TicketAttachment:** Archivos adjuntos vinculados a las reparaciones.

## Equipo de Desarrollo

| Nombre | Código | Rol |
| :--- | :--- | :--- |
| Andrés Julián Ortiz Jaimes | 1152249 | Líder de Proyecto |
| Maria Jose López Reyes | 1152268 | Desarrollador |
| Daniela Alejandra Barreto Ibarra | 1152269 | Desarrollador |
| Anyela Jhohana Herrera Lobo | 1152256 | Desarrollador |
| Laura Isabella Correa Nieto | 1152265 | Desarrollador |
| Josué Daniel Perez Guerrero | 1152273 | Desarrollador |
| David Santiago Peñaranda Parada | 1151943 | Desarrollador |

**Universidad Francisco de Paula Santander**  
Programa de Ingeniería de Sistemas  
San José de Cúcuta - 2025

## Versionamiento

- **Repositorio Frontend:** [https://github.com/JulianOrtiz952/tickethelp-frontend](https://github.com/JulianOrtiz952/tickethelp-frontend)
- **Repositorio Backend:** [https://github.com/JulianOrtiz952/tickethelp-backend](https://github.com/JulianOrtiz952/tickethelp-backend)

**Versión Actual:** 1.0.0-alpha

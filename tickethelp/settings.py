import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# -----------------------------
# BASE CONFIG
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")  # En prod usar env
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

# Para CSRF en producción (Render, Railway, etc.)
CSRF_TRUSTED_ORIGINS = [
    os.getenv("CSRF_TRUSTED_ORIGIN", "https://tickethelp-frontend.onrender.com",)
]

AUTH_USER_MODEL = "users.User"

# -----------------------------
# APLICACIONES
# -----------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "whitenoise.runserver_nostatic",

    # Apps locales
    "tickets",
    "users",
    "notifications.apps.NotificationsConfig",
    "reports",
]

# -----------------------------
# MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -----------------------------
# URLS / WSGI
# -----------------------------
ROOT_URLCONF = "tickethelp.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "notifications" / "templates",
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tickethelp.wsgi.application"

# -----------------------------
# BASE DE DATOS
# -----------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# -----------------------------
# PASSWORDS
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------
# INTERNACIONALIZACIÓN
# -----------------------------
LANGUAGE_CODE = "es-es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# -----------------------------
# ESTÁTICOS
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
}

# -----------------------------
# DEFAULT AUTO FIELD
# -----------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------
# REST FRAMEWORK
# -----------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# -----------------------------
# CORS
# -----------------------------
FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "https://tickethelp-frontend.onrender.com",  # valor por defecto en prod
)
CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# -----------------------------
# CONFIGURACIÓN DE CORREO ELECTRÓNICO
# -----------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@tickethelp.com")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "30"))

# Integración SendGrid (opcional, vía API HTTP)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", DEFAULT_FROM_EMAIL)

# Configuración de notificaciones
NOTIFICATIONS_EMAIL_ENABLED = os.getenv("NOTIFICATIONS_EMAIL_ENABLED", "True") == "True"

# -----------------------------
# SIMPLE JWT CONFIGURATION
# -----------------------------
from datetime import timedelta
from rest_framework_simplejwt.settings import api_settings

# Configurar SimpleJWT para usar 'document' en lugar de 'id'
api_settings.USER_ID_FIELD = 'document'

# Configuración de expiración de tokens JWT
# Valores configurados:
# - ACCESS_TOKEN_LIFETIME: 20 minutos (token de acceso válido por 20 minutos)
# - REFRESH_TOKEN_LIFETIME: 7 días (permite mantener sesión activa por una semana)
# 
# Estos valores equilibran seguridad y usabilidad:
# - El token de acceso expira cada 20 minutos, limitando el riesgo si es comprometido
# - El refresh token permite renovar el acceso sin reautenticarse por 7 días

# Aplicar configuración directamente a api_settings para asegurar que se use
api_settings.ACCESS_TOKEN_LIFETIME = timedelta(minutes=20)  # Token de acceso válido por 20 minutos
api_settings.REFRESH_TOKEN_LIFETIME = timedelta(days=7)  # Token de refresco válido por 7 días
api_settings.ROTATE_REFRESH_TOKENS = True  # Genera nuevo refresh token en cada renovación
api_settings.BLACKLIST_AFTER_ROTATION = True  # Invalida el refresh token anterior tras rotación
api_settings.UPDATE_LAST_LOGIN = True  # Actualiza el último login del usuario
api_settings.ALGORITHM = 'HS256'  # Algoritmo de encriptación
api_settings.SIGNING_KEY = SECRET_KEY  # Usa la SECRET_KEY del proyecto
api_settings.AUTH_HEADER_TYPES = ('Bearer',)  # Tipo de header: "Bearer <token>"
api_settings.AUTH_HEADER_NAME = 'HTTP_AUTHORIZATION'  # Nombre del header HTTP
api_settings.USER_ID_CLAIM = 'document'  # Claim del JWT que contiene el document

# También definir SIMPLE_JWT para compatibilidad con otras partes del código
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=20),  # Token de acceso válido por 20 minutos
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # Token de refresco válido por 7 días
    'ROTATE_REFRESH_TOKENS': True,  # Genera nuevo refresh token en cada renovación
    'BLACKLIST_AFTER_ROTATION': True,  # Invalida el refresh token anterior tras rotación
    'UPDATE_LAST_LOGIN': True,  # Actualiza el último login del usuario
    'ALGORITHM': 'HS256',  # Algoritmo de encriptación
    'SIGNING_KEY': SECRET_KEY,  # Usa la SECRET_KEY del proyecto
    'AUTH_HEADER_TYPES': ('Bearer',),  # Tipo de header: "Bearer <token>"
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',  # Nombre del header HTTP
    'USER_ID_FIELD': 'document',  # Campo usado como identificador de usuario
    'USER_ID_CLAIM': 'document',  # Claim del JWT que contiene el document
}

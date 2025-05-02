import os  # Importa el módulo os para interactuar con el sistema operativo
from pathlib import Path  # Importa Path para manejar rutas de archivos de manera más sencilla

# Define la ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta para la configuración de Django (debe ser única y segura en producción)
SECRET_KEY = 'your-secret-key'  # Cambia esto por una clave segura

# Activa o desactiva el modo de depuración (True para desarrollo, False para producción)
DEBUG = True

# Lista de hosts permitidos para acceder a la aplicación
ALLOWED_HOSTS = []

# Aplicaciones instaladas en el proyecto
INSTALLED_APPS = [
    'django.contrib.admin',  # Interfaz de administración de Django
    'django.contrib.auth',  # Sistema de autenticación y autorización
    'django.contrib.contenttypes',  # Framework para tipos de contenido
    'django.contrib.sessions',  # Manejo de sesiones
    'django.contrib.messages',  # Sistema de mensajes
    'django.contrib.staticfiles',  # Manejo de archivos estáticos
    'myapp',    # Proyecto principal
    'dte_app',  # Aplicación adicional
]

# Middleware que se ejecuta en cada solicitud/respuesta
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Seguridad general
    'django.contrib.sessions.middleware.SessionMiddleware',  # Manejo de sesiones
    'django.middleware.common.CommonMiddleware',  # Funcionalidades comunes
    'django.middleware.csrf.CsrfViewMiddleware',  # Protección contra CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Manejo de autenticación
    'django.contrib.messages.middleware.MessageMiddleware',  # Manejo de mensajes
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Protección contra clickjacking
]

# Configuración de las URLs principales del proyecto
ROOT_URLCONF = 'myapp.urls'

# Configuración de las plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # Motor de plantillas de Django
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Directorio de plantillas personalizadas
        'APP_DIRS': True,  # Busca plantillas en las carpetas de las aplicaciones instaladas
        'OPTIONS': {
            'context_processors': [  # Procesadores de contexto para las plantillas
                'django.template.context_processors.debug',  # Información de depuración
                'django.template.context_processors.request',  # Agrega la solicitud al contexto
                'django.contrib.auth.context_processors.auth',  # Agrega el usuario autenticado al contexto
                'django.contrib.messages.context_processors.messages',  # Agrega mensajes al contexto
            ],
        },
    },
]

# Configuración de la aplicación WSGI
WSGI_APPLICATION = 'myapp.wsgi.application'

# Configuración de la base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Motor de base de datos SQLite
        'NAME': BASE_DIR / 'db.sqlite3',  # Ruta al archivo de la base de datos
    }
}

# URL para acceder a los archivos estáticos
STATIC_URL = '/static/'
# Directorios adicionales donde buscar archivos estáticos
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
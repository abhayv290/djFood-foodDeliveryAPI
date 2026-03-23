from pathlib import Path
from datetime import timedelta
import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent


#setting up Env
env = environ.Env(DEBUG=(bool,False))
environ.Env.read_env(BASE_DIR/'.env')



SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS') if env('ALLOWED_HOSTS') else ['localhost']

ROOT_URLCONF = 'config.urls'

ASGI_APPLICATION = 'config.asgi.application'  

AUTH_USER_MODEL='users.User'


# Application definition -----------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #third party services 
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',    
    'django_filters',


    #my apps 
    'apps.users',
    'apps.restaurants',
    'apps.orders',

]
#middleware configurations -----------------------------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

#database configuration--------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env.str('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60 #reuse db connection for 60 section for reducing overhead
    }
}


 
# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Default: require login for everything — opt out per view with AllowAny
        "rest_framework.permissions.IsAuthenticated",
    ],

     "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],

    "DEFAULT_PAGINATION_CLASS" : "core.pagination.StandardResultsPagination",
    "PAGE_SIZE" : 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}



# Web frontend origins that are allowed to call this API
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
) if env('CORS_ALLOWED_ORIGINS') else ['http://localhost:5173']
CORS_ALLOW_CREDENTIALS = True

# ── API Docs ──────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "Zwigato-Food Delivery API",
    "DESCRIPTION": "Backend for a  Zwigato(Swiggy/Zomato-style)  food delivery platform.",
    "VERSION":     "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
 
# ── JWT Config ────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=10),
    # Rotation: every time you use a refresh token, you get a new one.
    # The old one is blacklisted. This limits the damage of a stolen refresh token.
    "ROTATE_REFRESH_TOKENS":     True,
    "BLACKLIST_AFTER_ROTATION":  True,
    "AUTH_HEADER_TYPES":         ("Bearer",),
    "UPDATE_LAST_LOGIN":         False,  # We handle last_login ourselves in LoginView
}



# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD  = 'django.db.models.BigAutoField'


STATIC_URL = 'static/'
STATIC_ROOT = 'staticFiles/'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'



# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
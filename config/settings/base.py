from pathlib import Path
from datetime import timedelta
import environ
import ssl

BASE_DIR = Path(__file__).resolve().parent.parent.parent


#setting up Env
env = environ.Env(DEBUG=(bool,False))
# environ.Env.read_env(BASE_DIR/'.env')



SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS') if env('ALLOWED_HOSTS') else ['localhost']

ROOT_URLCONF = 'config.urls'

ASGI_APPLICATION = 'config.asgi.application'  

AUTH_USER_MODEL='users.User'

RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET')
# Application definition -----------------------------------------------
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #third party services 
    'channels',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',    
    'django_filters',
    'anymail',
    'django_celery_beat',

    #my apps 
    'apps.users',
    'apps.restaurants',
    'apps.orders',
    'apps.payments',
    'apps.tracking',
    'apps.reviews',
    'apps.search',

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


#Channel Layers with Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG":  {"hosts": [{
            'address':env('REDIS_URL'),
              "ssl_cert_reqs": ssl.CERT_NONE,
        }]},
    }
}

CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

CELERY_BROKER_USE_SSL = {
    "ssl_cert_reqs": ssl.CERT_NONE,
}
CELERY_REDIS_BACKEND_USE_SSL = {
    "ssl_cert_reqs": ssl.CERT_NONE,
}

CELERY_BEAT_SCHEDULE = {
    'cancel-unpaid-orders' :{
        'task' : 'apps.orders.tasks.cancel_unpaid_orders',
        'schedule' : 300   # pol every 5 minutes
    }
}


#Caches Setup
CACHES = {
    'default' : {
        'BACKEND' : 'django.core.cache.backends.redis.RedisCache',
        'LOCATION' : env('REDIS_URL'),
        'OPTIONS'  : {
             "ssl_cert_reqs": ssl.CERT_NONE,
        }
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
    "TITLE":       "FoodRevolut-FoodDeliveryAPI",
    "DESCRIPTION": "Backend for a FoodRevolut (Swiggy/Zomato-style)  food delivery platform.",
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

#email configurations 
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL',default='noreply@foodrevolut.com')
FRONTEND_URL = env('FRONTEND_URL')
ANYMAIL = {
    "MAILGUN_API_KEY":       env("MAILGUN_API_KEY"),
    "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN"),
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
# MEDIA_URL = 'media/'
# MEDIA_ROOT = BASE_DIR / 'media'



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



USE_S3 = env.bool('USE_S3', default=True)

if USE_S3:
    INSTALLED_APPS += ["storages"]

    AWS_ACCESS_KEY_ID        = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY    = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME  = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME       = env.str("AWS_S3_REGION_NAME", default="ap-south-1")
    AWS_S3_FILE_OVERWRITE    = False
    AWS_DEFAULT_ACL          = None
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE  = "virtual"
    AWS_QUERYSTRING_AUTH     = False

    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.ap-south-1.amazonaws.com"

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "location": "media",
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            "OPTIONS": {
                "location": "static",
            },
        },
    }

    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    MEDIA_URL  = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

else:
    STATIC_URL  = "/static/"
    STATIC_ROOT = BASE_DIR / "staticfiles"
    MEDIA_URL   = "/media/"
    MEDIA_ROOT  = BASE_DIR / "media"
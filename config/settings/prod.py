from .base import * 

DEBUG=False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
 
DEBUG = False

# ── HTTPS / Security ───────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Enable HSTS — tells browsers to always use HTTPS
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Trust the X-Forwarded-Proto header from nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
 
# ── Static and media — both from S3 ──────────────────────────────────────────
# Nginx no longer serves static or media files directly.
# Browser fetches them from S3 URLs.
# collectstatic on container start uploads to S3.
USE_S3 = True
 
# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level":    "INFO",
    },
    "loggers": {
        "django": {
            "handlers":  ["console"],
            "level":     "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers":  ["console"],
            "level":     "ERROR",
            "propagate": False,
        },
    },
}
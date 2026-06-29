import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    if os.getenv('DEBUG', 'False') == 'True':
        # Local dev only — never reaches production because DEBUG is False there
        _secret_key = 'django-insecure-local-dev-only-do-not-use-in-production'  # noqa: S105
    else:
        raise RuntimeError(
            'SECRET_KEY environment variable is not set. Set it before starting the server in production.'
        )
SECRET_KEY = _secret_key

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'ananimeclip',
    'django_ratelimit',
    'cloudinary',
    'cloudinary_storage',
    'analytics',
    'django_celery_beat',
    'axes',
    'csp',
    # Feature-pack additions
    'channels',                              # WebSockets (Django Channels) — for live support chat
    'ananimeclip.editorial',                 # Editorial / merchandising tools
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Sets the Content-Security-Policy header on every response. Must come
    # early (right after SecurityMiddleware) per django-csp's docs so it can
    # see/modify the final response on the way back out.
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # axes must come after AuthenticationMiddleware
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Feature-pack additions
    'ananimeclip.session_manager.SessionManagerMiddleware',  # device/session registry
    'ananimeclip.totp.TwoFactorMiddleware',                  # 2FA second-step enforcement
    'ananimeclip.geo_block.GeoBlockMiddleware',              # geo-blocking (requires GEOIP2_DB_PATH)
]

ROOT_URLCONF = 'Hello.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ananimeclip.context_processors.notification_count',
                'ananimeclip.context_processors.active_subprofile',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'Hello.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'CONN_MAX_AGE': 60,
        # Django 4.1+: test the connection before reuse so stale sockets
        # (e.g. after a DB restart or Gunicorn --preload fork) don't surface
        # as 500 errors on the first request to a worker.
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 5,
            'options': '-c statement_timeout=5000',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('hi', 'हिन्दी'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

# ============================================================
# STATIC FILES
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Opt into Django 6.0's forms.URLField default now (assume https, not http,
# when a submitted URL has no scheme) — every URLField here (trailer_url,
# video_url, file_url) is always an https Cloudinary/YouTube URL anyway, and
# this silences a RemovedInDjango60Warning ahead of that upgrade.
FORMS_URLFIELD_ASSUME_HTTPS = True

# Email — set EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in production
if os.getenv('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
else:
    # Fallback: prints to console — only for local dev
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# PASSWORD_RESET_TIMEOUT was previously 300 (5 minutes) — far too short for an
# email-based flow: the user has to receive the email, open it, and click the
# link before it expires. Django's own default is 259200 (3 days); we use that.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3  # 3 days
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

# ============================================================
# VIDEO CONTENT PROTECTION
# ============================================================
# CLOUDINARY_AUTH_TOKEN_KEY enables CDN-edge URL expiry so that even a
# captured raw Cloudinary URL can't be replayed after the signed Django
# redirect expires.  In production this MUST be set — without it video
# URLs are effectively public and permanent once shared.
#
# To enable:
#   1. Cloudinary dashboard → Security → Token-based access control → Enable
#   2. Change video delivery type to "authenticated"
#   3. Copy the hex signing key below
CLOUDINARY_AUTH_TOKEN_KEY = os.getenv('CLOUDINARY_AUTH_TOKEN_KEY', '').strip() or None

if not DEBUG and not CLOUDINARY_AUTH_TOKEN_KEY and 'test' not in sys.argv:
    raise RuntimeError(
        'CLOUDINARY_AUTH_TOKEN_KEY is not set. '
        'Without it, video URLs are public and permanent. '
        'Enable token auth in your Cloudinary dashboard and set this variable before starting in production.'
    )

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
            'SOCKET_CONNECT_TIMEOUT': 2,
            'SOCKET_TIMEOUT': 2,
        },
        'TIMEOUT': 300,
    }
}

# django-ratelimit fails *closed* by default: if it can't read/write a
# counter in the cache (e.g. Redis is down or unreachable), it treats the
# request as rate-limited rather than as "unknown". Combined with
# IGNORE_EXCEPTIONS above, that means a Redis outage would silently block
# every login and signup attempt — a cache problem turning into a site-wide
# auth outage. Fail open instead: if the cache can't be reached, skip rate
# limiting rather than lock everyone out.
RATELIMIT_FAIL_OPEN = True

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    # Belt-and-suspenders: cookies must be HttpOnly and SameSite=Lax so they
    # can't be read by JS and are not sent on cross-site top-level navigations.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_HTTPONLY = False  # Django default; keep False so JS can read it for AJAX
    CSRF_COOKIE_SAMESITE = 'Lax'
    # Tell Django we're behind an SSL-terminating nginx proxy.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================
# CONTENT SECURITY POLICY (django-csp)
# ============================================================
# Restricts which origins the browser will load scripts/styles/media/etc.
# from, which meaningfully shrinks the blast radius of any future XSS even
# though our SecurityMiddleware/cookie settings already cover a lot of
# ground. Kept on in dev too so CSP violations are caught locally rather
# than discovered for the first time in production.
#
# 'unsafe-inline' is still needed for script-src/style-src because several
# templates use inline <script> blocks and inline style="" attributes
# (see streaming.html, the analytics dashboard, etc.). Migrating those to
# nonces (request.csp_nonce) would let us drop 'unsafe-inline' entirely —
# worth doing as a follow-up, but out of scope here since it touches every
# template with an inline <script> tag.
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            'blob:',  # hls.js creates blob: worker URLs for segment fetching
            'https://cdn.jsdelivr.net',
            'https://upload-widget.cloudinary.com',
            'https://www.gstatic.com',  # Chromecast sender SDK (cast_airplay.js)
        ],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https://res.cloudinary.com'],
        'media-src': [
            "'self'",
            'blob:',  # hls.js feeds segments to <video> via a MediaSource blob: URL
            'https://res.cloudinary.com',
        ],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'", 'https://res.cloudinary.com', 'https://api.cloudinary.com'],
        'frame-src': [
            "'self'",
            'https://www.youtube.com',
            'https://www.youtube-nocookie.com',
            'https://upload-widget.cloudinary.com',
        ],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        # Matches X_FRAME_OPTIONS = 'DENY' above — belt and suspenders.
        'frame-ancestors': ["'none'"],
    }
}


if 'test' in sys.argv:
    STORAGES['staticfiles'] = {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }

# ============================================================
# AXES — brute-force login protection
# ============================================================
# Lock out an IP after 5 failed attempts within a 1-hour window.
# On lockout, axes raises PermissionDenied so Django returns 403.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours until lockout is lifted automatically
AXES_LOCKOUT_PARAMETERS = ['ip_address']  # lock by IP (add 'username' for extra strictness)
AXES_RESET_ON_SUCCESS = True  # clear failure count on successful login
AXES_HANDLER = 'axes.handlers.cache.AxesCacheHandler'  # use Redis for fast counter storage

# ============================================================
# LOGGING
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'ananimeclip': {
            'handlers': ['console'],
            'level': os.getenv('APP_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# ============================================================
# SENTRY (error monitoring) — set SENTRY_DSN in production
# ============================================================
_sentry_dsn = os.getenv('SENTRY_DSN')
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration(), RedisIntegration()],
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        send_default_pii=False,
        environment='production' if not DEBUG else 'development',
    )

# ============================================================
# CELERY — async task queue + periodic scheduler
# ============================================================
# The cache uses REDIS_URL (DB 1 by default in .env.example).
# Celery broker lives on DB 0 and results on DB 2 to avoid cross-eviction.
# We derive broker/result URLs from REDIS_URL by replacing the DB number,
# so password, host, and port are always consistent with the main URL.
import re as _re

_redis_base_url = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
_redis_url_no_db = _re.sub(r'/\d+$', '', _redis_base_url)

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', _redis_url_no_db + '/0')
_redis_result_url = os.getenv('REDIS_RESULT_URL', _redis_url_no_db + '/2')
CELERY_RESULT_BACKEND = _redis_result_url

del _re, _redis_base_url, _redis_url_no_db
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


# Periodic jobs — the `crontab` import is deferred inside the dict so
# `settings.py` doesn't hard-import Celery at startup (which would fail if
# Celery isn't installed in a lightweight test environment).
def _celery_beat_schedule():
    from celery.schedules import crontab  # noqa: PLC0415

    return {
        # Warm collaborative-filtering recommendations at 3 AM every day.
        'warm-recommendations-daily': {
            'task': 'ananimeclip.tasks.warm_recommendations',
            'schedule': crontab(hour=3, minute=0),
        },
        # Notify movie-release followers daily at 8 AM.
        'notify-movie-releases-daily': {
            'task': 'ananimeclip.tasks.notify_movie_releases',
            'schedule': crontab(hour=8, minute=0),
        },
        # Warm trending cache every 5 minutes.
        'warm-trending-cache': {
            'task': 'ananimeclip.tasks.warm_trending_cache',
            'schedule': crontab(minute='*/5'),
        },
    }


CELERY_BEAT_SCHEDULE = _celery_beat_schedule()

# ── Feature Pack: Session / Stream limits ──────────────────────────────────
MAX_CONCURRENT_STREAMS = int(os.getenv("MAX_CONCURRENT_STREAMS", "2"))

# ── Feature Pack: 2FA ─────────────────────────────────────────────────────
# No extra settings required; pyotp is self-contained.

# ── Feature Pack: Geo-blocking ────────────────────────────────────────────
GEOIP2_DB_PATH = os.getenv("GEOIP2_DB_PATH", "")
# e.g. GEOBLOCK_DENIED_COUNTRIES = ['CN', 'RU']
GEOBLOCK_DENIED_COUNTRIES = [c for c in os.getenv("GEOBLOCK_DENIED_COUNTRIES", "").split(",") if c]
# e.g. GEOBLOCK_ALLOWED_COUNTRIES = ['US', 'JP', 'GB']
GEOBLOCK_ALLOWED_COUNTRIES = [c for c in os.getenv("GEOBLOCK_ALLOWED_COUNTRIES", "").split(",") if c]

# ── Feature Pack: Web Push (VAPID) ────────────────────────────────────────
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS_SUB = os.getenv("VAPID_CLAIMS_SUB", "mailto:admin@example.com")

# ── Feature Pack: Django Channels (WebSockets for support chat) ────────────
ASGI_APPLICATION = "Hello.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1")],
        },
    },
}

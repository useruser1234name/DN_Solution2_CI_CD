"""
운영 환경 설정 - DN_SOLUTION2
보안 강화 및 성능 최적화
"""

from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Debug 모드 비활성화
DEBUG = False

# 허용 호스트 (운영 도메인만)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# 데이터베이스 설정 (운영용)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # 연결 풀링
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30초 타임아웃
        }
    },
    # 읽기 전용 복제본 (선택사항)
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_REPLICA_USER', default=config('DB_USER')),
        'PASSWORD': config('DB_REPLICA_PASSWORD', default=config('DB_PASSWORD')),
        'HOST': config('DB_REPLICA_HOST', default=config('DB_HOST')),
        'PORT': config('DB_REPLICA_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    }
}

# 데이터베이스 라우터 (읽기/쓰기 분리)
DATABASE_ROUTERS = ['dn_solution.routers.ReadWriteRouter']

# 보안 설정 강화
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# 세션 보안
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 3600  # 1시간

# CSRF 보안
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='').split(',')

# CORS 설정 (운영)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# 정적 파일 및 미디어 설정 (AWS S3)
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-northeast-2')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'private'
AWS_S3_SECURE_URLS = True

# 정적 파일 스토리지
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

# 미디어 파일 스토리지
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# 캐시 설정 (Redis Cluster)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': [
            config('REDIS_URL_1', default='redis://127.0.0.1:6379/1'),
            config('REDIS_URL_2', default='redis://127.0.0.1:6379/1'),
            config('REDIS_URL_3', default='redis://127.0.0.1:6379/1'),
        ],
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.ShardClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
        },
        'KEY_PREFIX': 'dn_prod',
        'VERSION': 1,
        'TIMEOUT': 300,
    }
}

# 로깅 설정 (운영)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                     '"logger": "%(name)s", "module": "%(module)s", '
                     '"function": "%(funcName)s", "line": %(lineno)d, '
                     '"message": "%(message)s"}',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/dn_solution/django.log',
            'formatter': 'json',
            'maxBytes': 1024 * 1024 * 100,  # 100MB
            'backupCount': 10,
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.SentryHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'sentry'],
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'sentry'],
            'level': 'WARNING',
            'propagate': False,
        },
        'companies': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'policies': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Sentry 에러 모니터링
sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment='production',
    before_send=lambda event, hint: event if not DEBUG else None,
)

# 이메일 설정 (운영)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# API Rate Limiting
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'burst': '60/minute',
}

# JWT 설정 (운영환경 - 더 짧은 토큰 수명)
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(minutes=5)
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=1)

# 파일 업로드 제한
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100

# 보안 미들웨어 추가
MIDDLEWARE.insert(0, 'django.middleware.security.SecurityMiddleware')
MIDDLEWARE.append('dn_solution.middleware.security.RateLimitMiddleware')
MIDDLEWARE.append('dn_solution.middleware.security.IPWhitelistMiddleware')

# IP 화이트리스트 (선택사항)
IP_WHITELIST = config('IP_WHITELIST', default='').split(',') if config('IP_WHITELIST', default='') else []

print("🔒 운영 환경으로 실행 중...")

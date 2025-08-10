"""
운영 환경용 Django 설정
HB Admin - B2B 플랫폼 백엔드
"""

import os
from pathlib import Path
from decouple import config
from .settings import *

# =============================================================================
# 보안 설정 (운영 환경 필수)
# =============================================================================

# 디버그 모드 비활성화
DEBUG = False

# 허용된 호스트 설정 (실제 도메인으로 변경 필요)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', 
                      cast=lambda v: [s.strip() for s in v.split(',')])

# HTTPS 강제 리다이렉트
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 보안 헤더 설정
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 세션 보안 설정
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# =============================================================================
# 데이터베이스 설정 (PostgreSQL 권장)
# =============================================================================

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='dn_solution'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 600,  # 10분 연결 유지
    }
}

# =============================================================================
# 정적 파일 설정 (WhiteNoise 사용)
# =============================================================================

# 정적 파일 수집 디렉토리
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise 미들웨어 추가 (SecurityMiddleware 다음에)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# WhiteNoise 설정
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# 캐싱 설정 (Redis 사용)
# =============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 세션 백엔드를 Redis로 설정
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# =============================================================================
# 로깅 설정 (운영 환경)
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'api.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'api': {
            'handlers': ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'companies': {
            'handlers': ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'policies': {
            'handlers': ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# 이메일 설정
# =============================================================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# =============================================================================
# CORS 설정 (운영 환경)
# =============================================================================

# 실제 프론트엔드 도메인으로 변경 필요
CORS_ALLOWED_ORIGINS = [
    config('FRONTEND_URL', default='https://yourdomain.com'),
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # 운영 환경에서는 False

# CSRF 신뢰할 수 있는 오리진
CSRF_TRUSTED_ORIGINS = [
    config('FRONTEND_URL', default='https://yourdomain.com'),
]

# =============================================================================
# 성능 최적화
# =============================================================================

# 데이터베이스 연결 풀링
DATABASES['default']['CONN_MAX_AGE'] = 600

# 템플릿 캐싱
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# =============================================================================
# 보안 강화 (django-axes)
# =============================================================================

INSTALLED_APPS += ['axes']

MIDDLEWARE += ['axes.middleware.AxesMiddleware']

# 로그인 시도 제한 설정
AXES_FAILURE_LIMIT = 5  # 5회 실패 시 잠금
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_COOLOFF_TIME = 1  # 1시간 후 잠금 해제
AXES_LOCKOUT_TEMPLATE = 'admin/login.html'

# =============================================================================
# 파일 업로드 설정
# =============================================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# =============================================================================
# 환경별 설정
# =============================================================================

# 환경 변수로 설정 가능한 옵션들
SECRET_KEY = config('SECRET_KEY')
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL)

# Sentry 설정 (선택사항)
SENTRY_DSN = config('SENTRY_DSN', default=None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    ) 
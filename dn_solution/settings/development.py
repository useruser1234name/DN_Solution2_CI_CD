# -*- coding: utf-8 -*-
"""
개발 환경 설정
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']

# 개발 환경용 데이터베이스 (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 개발 환경용 캐시 설정 - Redis 대신 로컬 메모리 캐시 사용
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'session-store',
    },
    'api_cache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'api-cache-store',
    },
    'long_term': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'long-term-store',
    },
}

# 개발 환경용 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
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
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',  # DEBUG에서 INFO로 변경하여 성능 개선
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # SQL 쿼리 로그 비활성화
            'propagate': False,
        },
        'companies': {
            'handlers': ['console'],
            'level': 'INFO',  # DEBUG에서 INFO로 변경
            'propagate': False,
        },
        'policies': {
            'handlers': ['console'],
            'level': 'INFO',  # DEBUG에서 INFO로 변경
            'propagate': False,
        },
        'orders': {
            'handlers': ['console'],
            'level': 'INFO',  # DEBUG에서 INFO로 변경
            'propagate': False,
        },
        'auth_views': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'cache_middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# CORS 설정 (개발 환경)
CORS_ALLOW_ALL_ORIGINS = True  # 개발 환경에서만 사용

# CSRF 설정 (개발 환경)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
]

# Celery 비활성화 (개발 환경에서 Redis 없이 실행)
CELERY_TASK_ALWAYS_EAGER = True  # 태스크를 동기적으로 실행
CELERY_TASK_EAGER_PROPAGATES = True  # 에러 전파

# 세션 엔진을 DB로 설정 (Redis 대신)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# 캐시 미들웨어 설정 오버라이드
CACHE_MIDDLEWARE_SECONDS = 60  # 1분으로 단축
CACHE_MIDDLEWARE_KEY_PREFIX = 'dev_cache'
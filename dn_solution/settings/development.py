"""
개발 환경 설정 - DN_SOLUTION2
"""

from .base import *

# Debug 모드
DEBUG = True

# 허용 호스트
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

# 데이터베이스 설정 (개발용)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='dn_solution2_dev'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'OPTIONS': '-c default_transaction_isolation=serializable'
        }
    }
}

# SQLite 백업 (개발시 편의)
if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# CORS 설정 (개발용 - 관대함)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000", 
    "http://127.0.0.1:8000",
    "http://0.0.0.0:3000",
    "http://0.0.0.0:8000",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# CSRF 설정 (개발용)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

# Cache 설정 (개발용)
CACHES['default']['LOCATION'] = config('REDIS_URL', default='redis://127.0.0.1:6379/1')

# 로깅 설정 (개발용)
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
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django_dev.log',
            'formatter': 'json',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
        'api_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'api_dev.log',
            'formatter': 'json',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if config('DEBUG_SQL', default=False, cast=bool) else 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'api_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'companies': {
            'handlers': ['console', 'api_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'policies': {
            'handlers': ['console', 'api_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'api_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'rebates': {
            'handlers': ['console', 'api_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# 개발용 추가 앱
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

# Debug Toolbar 설정
if DEBUG:
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ]
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    }
    
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]

# 개발용 이메일 백엔드
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 개발용 성능 설정
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/hour',
    'user': '10000/hour'
}

# 개발용 JWT 설정 (더 긴 토큰 수명)
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=2)
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=30)

print("🚀 개발 환경으로 실행 중...")
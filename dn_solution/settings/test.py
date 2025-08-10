"""
테스트 환경 설정 - DN_SOLUTION2
"""

from .base import *

# 테스트 모드
DEBUG = False
TESTING = True

# 테스트 데이터베이스
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # 메모리 내 데이터베이스
    }
}

# 캐시 비활성화 (테스트 속도 향상)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# 비밀번호 해싱 간소화 (테스트 속도 향상)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 이메일 백엔드 (메모리)
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 미디어 파일 설정
MEDIA_ROOT = BASE_DIR / 'test_media'

# Celery 설정 (동기 실행)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 로깅 간소화
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# CORS 설정
CORS_ALLOW_ALL_ORIGINS = True

# CSRF 비활성화 (테스트용)
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# 파일 업로드 제한 완화
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

print("🧪 테스트 환경으로 실행 중...")

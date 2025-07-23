# hb_admin/wsgi.py
"""
WSGI config for hb_admin project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hb_admin.settings')

try:
    application = get_wsgi_application()
    logger.info("WSGI 애플리케이션이 성공적으로 로드되었습니다")
except Exception as e:
    logger.error(f"WSGI 애플리케이션 로드 중 오류 발생: {str(e)}")
    raise

# 각 앱의 migrations/__init__.py 파일들
# companies/migrations/__init__.py
"""
Companies 앱 데이터베이스 마이그레이션 패키지
"""

# policies/migrations/__init__.py
"""
Policies 앱 데이터베이스 마이그레이션 패키지
"""

# orders/migrations/__init__.py
"""
Orders 앱 데이터베이스 마이그레이션 패키지
"""
# hb_admin/asgi.py
"""
ASGI config for hb_admin project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import logging

from django.core.asgi import get_asgi_application

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hb_admin.settings')

try:
    application = get_asgi_application()
    logger.info("ASGI 애플리케이션이 성공적으로 로드되었습니다")
except Exception as e:
    logger.error(f"ASGI 애플리케이션 로드 중 오류 발생: {str(e)}")
    raise
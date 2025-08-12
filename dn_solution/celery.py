# -*- coding: utf-8 -*-
"""
Celery Configuration - DN_SOLUTION2
비동기 작업 처리 설정
"""

import os
from celery import Celery
from django.conf import settings

# Django 설정 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dn_solution.settings.development')

# Celery 앱 생성
app = Celery('dn_solution')

# Django 설정에서 Celery 설정 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 모든 Django 앱에서 작업 자동 발견
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Redis를 브로커로 사용
app.conf.update(
    broker_url=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@app.task(bind=True)
def debug_task(self):
    """디버그용 테스트 작업"""
    print(f'Request: {self.request!r}')
    return 'Debug task completed successfully'

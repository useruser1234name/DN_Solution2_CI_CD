"""
데이터베이스 라우터 - 읽기/쓰기 분리
운영 환경에서 성능 최적화를 위한 마스터/복제본 분리
"""

import random


class ReadWriteRouter:
    """
    마스터/복제본 데이터베이스 라우팅
    - 쓰기 작업: 마스터 DB
    - 읽기 작업: 복제본 DB (가능한 경우)
    """
    
    def db_for_read(self, model, **hints):
        """
        읽기 작업을 위한 데이터베이스 선택
        복제본이 설정되어 있으면 복제본 사용
        """
        # 특정 모델은 항상 마스터에서 읽기 (일관성 중요)
        if model._meta.app_label in ['auth', 'contenttypes', 'sessions']:
            return 'default'
        
        # 복제본이 설정되어 있으면 사용
        from django.conf import settings
        if 'replica' in settings.DATABASES:
            return 'replica'
        
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        쓰기 작업은 항상 마스터 데이터베이스 사용
        """
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        같은 앱의 모델간 관계는 허용
        """
        db_set = {'default', 'replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        마이그레이션은 마스터 데이터베이스에서만 실행
        """
        return db == 'default'

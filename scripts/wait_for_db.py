#!/usr/bin/env python3
"""
데이터베이스 연결 대기 스크립트
Django 설정을 사용하여 PostgreSQL 연결을 기다립니다.
"""

import os
import sys
import time
import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import connections
from django.db.utils import OperationalError

# Django 설정 모듈 지정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dn_solution.settings.development')

def wait_for_db():
    """데이터베이스 연결이 가능할 때까지 대기"""
    print("🔄 데이터베이스 연결을 확인하는 중...")
    
    # Django 설정 초기화
    django.setup()
    
    # 기본 데이터베이스 연결 가져오기
    db_conn = connections['default']
    
    max_attempts = int(os.environ.get('DB_WAIT_ATTEMPTS', '60'))
    delay = float(os.environ.get('DB_WAIT_DELAY', '1.0'))
    
    for attempt in range(1, max_attempts + 1):
        try:
            # 데이터베이스 연결 시도
            db_conn.ensure_connection()
            print(f"✅ 데이터베이스 연결 성공! (시도: {attempt}/{max_attempts})")
            return True
            
        except OperationalError as e:
            if attempt == max_attempts:
                print(f"❌ 데이터베이스 연결 실패! 최대 시도 횟수 ({max_attempts})에 도달했습니다.")
                print(f"오류: {e}")
                return False
            
            print(f"⏳ 데이터베이스 연결 대기 중... (시도: {attempt}/{max_attempts}) - {delay}초 후 재시도")
            time.sleep(delay)
        
        except Exception as e:
            print(f"❌ 예상치 못한 오류 발생: {e}")
            return False
    
    return False

if __name__ == '__main__':
    success = wait_for_db()
    if not success:
        sys.exit(1)
    
    print("🚀 데이터베이스 준비 완료!")

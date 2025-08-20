@echo off
echo ==============================================
echo 패키지 설치 문제 해결 스크립트
echo ==============================================
echo.

REM 가상환경 활성화 확인
if not defined VIRTUAL_ENV (
    echo [INFO] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
)

echo [INFO] 현재 Python 버전:
python --version

echo.
echo [INFO] pip 업그레이드...
python -m pip install --upgrade pip

echo.
echo [INFO] 기본 패키지부터 순서대로 설치...

REM 1단계: 기본 패키지들
echo [1/6] Django 및 기본 패키지 설치...
pip install Django==4.2.7
pip install djangorestframework==3.14.0
pip install djangorestframework-simplejwt==5.3.0

REM 2단계: 데이터베이스 관련
echo [2/6] 데이터베이스 패키지 설치...
pip install psycopg2-binary==2.9.10
pip install django-model-utils==4.3.1
pip install dj-database-url==2.1.0

REM 3단계: 캐시 및 성능
echo [3/6] 캐시 및 성능 패키지 설치...
pip install redis==5.0.1
pip install django-redis==5.4.0
pip install django-cachalot==2.6.1
pip install psutil==5.9.6

REM 4단계: 비동기 작업
echo [4/6] 비동기 작업 패키지 설치...
pip install celery==5.3.4
pip install django-celery-beat==2.5.0
pip install django-celery-results==2.5.1
pip install kombu==5.3.4

REM 5단계: 기타 필수 패키지들
echo [5/6] 기타 필수 패키지 설치...
pip install channels==4.0.0
pip install channels-redis==4.1.0
pip install daphne==4.0.0
pip install django-cors-headers==4.3.1
pip install django-ratelimit==4.1.0
pip install python-decouple==3.8
pip install python-dotenv==1.0.0
pip install django-environ==0.11.2
pip install django-filter==23.4
pip install Pillow==10.4.0
pip install requests==2.31.0
pip install openpyxl==3.1.2

REM 6단계: 문제가 되는 pandas - 호환되는 버전으로 설치
echo [6/6] pandas 호환 버전 설치 시도...
echo pandas 설치 중... (여러 버전 시도)

REM 먼저 numpy 설치 (pandas 의존성)
pip install "numpy>=1.21.0,<2.0.0"

REM pandas 호환 버전 시도
pip install "pandas>=2.1.0,<2.2.0" || (
    echo pandas 2.1.x 실패, 다른 버전 시도...
    pip install "pandas>=2.0.0,<2.1.0" || (
        echo pandas 2.0.x 실패, 최신 안정 버전 시도...
        pip install pandas || (
            echo 모든 pandas 설치 실패, pandas 없이 진행...
            echo [WARNING] pandas 설치 실패 - 나중에 수동 설치 필요
        )
    )
)

REM 나머지 패키지들
echo 나머지 패키지 설치 중...
pip install colorlog==6.8.0
pip install structlog==23.2.0
pip install drf-spectacular==0.27.0
pip install pytest==7.4.3
pip install pytest-django==4.7.0
pip install pytest-cov==4.1.0
pip install factory-boy==3.3.0
pip install faker==20.1.0
pip install gunicorn==21.2.0
pip install gevent==23.9.1
pip install whitenoise==6.6.0
pip install django-anymail==10.2
pip install marshmallow==3.20.2
pip install pydantic==2.5.2
pip install pytz==2023.3
pip install python-dateutil==2.8.2
pip install shortuuid==1.0.11
pip install httpx==0.25.2
pip install urllib3==2.1.0
pip install django-extensions==3.2.3
pip install aiohttp==3.9.1
pip install sentry-sdk==1.38.0

echo.
echo ==============================================
echo 설치 완료 확인
echo ==============================================
pip list | findstr -i "django pandas"

echo.
echo [INFO] Django 설치 확인:
python -c "import django; print(f'Django {django.get_version()} 설치 완료')"

echo.
echo [INFO] pandas 설치 확인:
python -c "try: import pandas as pd; print(f'pandas {pd.__version__} 설치 완료'); except ImportError: print('pandas 설치되지 않음 - 옵션 패키지')" 2>nul

echo.
echo ==============================================
echo 설치 스크립트 완료!
echo ==============================================
echo.
echo 다음 단계:
echo 1. python manage.py migrate
echo 2. python manage.py runserver
echo.
pause

@echo off
REM DN_Solution2 개발 서버 실행 스크립트

echo ==============================================
echo DN_SOLUTION2 개발 서버를 시작합니다...
echo ==============================================

REM 가상환경 확인
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] 가상환경이 설정되지 않았습니다.
    echo setup_dev.bat를 먼저 실행해주세요.
    pause
    exit /b 1
)

REM 가상환경 활성화
echo [INFO] 가상환경 활성화 중...
call venv\Scripts\activate.bat

REM 환경변수 파일 확인
if not exist ".env" (
    if exist ".env.dev" (
        echo [INFO] .env.dev를 .env로 복사합니다...
        copy .env.dev .env
    ) else (
        echo [WARNING] .env 파일이 없습니다.
    )
)

REM 마이그레이션 확인
echo [INFO] 데이터베이스 마이그레이션 확인 중...
python manage.py migrate --check 2>nul
if errorlevel 1 (
    echo [INFO] 마이그레이션이 필요합니다. 실행 중...
    python manage.py migrate
)

REM 서버 실행 옵션 선택
echo.
echo 실행할 서버를 선택하세요:
echo   1. Django 개발 서버만 (기본)
echo   2. Django + Celery Worker
echo   3. Django + Celery + Celery Beat
echo   4. 프론트엔드 개발 서버 (React)
echo   5. Docker Compose로 전체 실행
echo.
set /p choice="선택 (1-5, 기본값 1): "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo [INFO] Django 개발 서버를 시작합니다...
    python manage.py runserver 0.0.0.0:8000
) else if "%choice%"=="2" (
    echo [INFO] Django 서버와 Celery Worker를 시작합니다...
    start "Django Server" cmd /k "venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"
    start "Celery Worker" cmd /k "venv\Scripts\activate.bat && celery -A dn_solution worker -l info"
    echo 서버들이 별도 창에서 실행되었습니다.
    pause
) else if "%choice%"=="3" (
    echo [INFO] Django 서버, Celery Worker, Celery Beat를 시작합니다...
    start "Django Server" cmd /k "venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"
    start "Celery Worker" cmd /k "venv\Scripts\activate.bat && celery -A dn_solution worker -l info"
    start "Celery Beat" cmd /k "venv\Scripts\activate.bat && celery -A dn_solution beat -l info"
    echo 서버들이 별도 창에서 실행되었습니다.
    pause
) else if "%choice%"=="4" (
    echo [INFO] React 프론트엔드 개발 서버를 시작합니다...
    cd frontend
    if not exist "node_modules" (
        echo [INFO] Node.js 의존성을 설치합니다...
        npm install
    )
    npm start
) else if "%choice%"=="5" (
    echo [INFO] Docker Compose로 전체 서비스를 시작합니다...
    docker-compose up -d
    echo.
    echo 서비스 상태 확인:
    docker-compose ps
    echo.
    echo 로그 확인: docker-compose logs -f [service_name]
    echo 서비스 중지: docker-compose down
    pause
) else (
    echo [ERROR] 잘못된 선택입니다.
    pause
    exit /b 1
)

@echo off
REM DN_Solution2 가상환경 설정 스크립트 (Windows)

echo ==============================================
echo DN_SOLUTION2 개발환경 설정을 시작합니다...
echo ==============================================

REM 현재 디렉토리 확인
if not exist "manage.py" (
    echo [ERROR] manage.py 파일을 찾을 수 없습니다.
    echo 프로젝트 루트 디렉토리에서 실행해주세요.
    pause
    exit /b 1
)

REM Python 버전 확인
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python이 설치되지 않았거나 PATH에 등록되지 않았습니다.
    echo Python 3.11+ 버전을 설치해주세요.
    pause
    exit /b 1
)

echo [INFO] Python 버전 확인 완료

REM 가상환경 생성
if exist "venv" (
    echo [INFO] 기존 가상환경이 발견되었습니다.
    set /p choice="기존 가상환경을 삭제하고 새로 만드시겠습니까? (y/N): "
    if /i "%choice%"=="y" (
        echo [INFO] 기존 가상환경을 삭제합니다...
        rmdir /s /q venv
    ) else (
        echo [INFO] 기존 가상환경을 사용합니다.
        goto ACTIVATE
    )
)

echo [INFO] 가상환경을 생성합니다...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] 가상환경 생성에 실패했습니다.
    pause
    exit /b 1
)

:ACTIVATE
echo [INFO] 가상환경을 활성화합니다...
call venv\Scripts\activate.bat

REM pip 업그레이드
echo [INFO] pip을 업그레이드합니다...
python -m pip install --upgrade pip

REM 의존성 설치
echo [INFO] Python 패키지를 설치합니다...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] 패키지 설치에 실패했습니다.
    pause
    exit /b 1
)

REM 개발용 의존성 설치
if exist "requirements-dev.txt" (
    echo [INFO] 개발용 패키지를 설치합니다...
    pip install -r requirements-dev.txt
)

REM 환경변수 파일 설정
if not exist ".env" (
    if exist ".env.dev" (
        echo [INFO] 개발용 환경변수 파일을 복사합니다...
        copy .env.dev .env
    ) else (
        echo [WARNING] .env 파일이 없습니다. .env.example을 참고하여 생성해주세요.
    )
)

REM 데이터베이스 마이그레이션 (PostgreSQL이 실행 중인 경우에만)
echo [INFO] 데이터베이스 연결을 확인합니다...
python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('DB 연결 성공')" 2>nul
if not errorlevel 1 (
    echo [INFO] 데이터베이스 마이그레이션을 실행합니다...
    python manage.py migrate
    
    echo [INFO] 슈퍼유저를 생성하시겠습니까?
    set /p create_superuser="슈퍼유저 생성 (y/N): "
    if /i "%create_superuser%"=="y" (
        python manage.py createsuperuser
    )
) else (
    echo [WARNING] 데이터베이스에 연결할 수 없습니다.
    echo PostgreSQL이 실행 중인지 확인하거나 Docker를 사용하세요.
)

echo.
echo ==============================================
echo 가상환경 설정이 완료되었습니다!
echo ==============================================
echo.
echo 다음 명령어로 개발 서버를 시작할 수 있습니다:
echo   1. 가상환경 활성화: venv\Scripts\activate
echo   2. 개발 서버 실행: python manage.py runserver
echo.
echo 또는 Docker를 사용하려면:
echo   docker-compose up -d
echo.
pause

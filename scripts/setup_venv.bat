@echo off
REM 윈도우용 가상환경 설정 스크립트

REM 파이썬 버전 확인
python --version
echo 시스템 파이썬 버전 확인 완료

REM 가상환경 생성
if not exist venv (
    echo 가상환경 생성 중...
    python -m venv venv
) else (
    echo 가상환경이 이미 존재합니다.
)

REM 가상환경 활성화
echo 가상환경 활성화 중...
call venv\Scripts\activate

REM pip 업그레이드
echo pip 업그레이드 중...
pip install --upgrade pip==24.0

REM 의존성 설치
echo 의존성 설치 중...
pip install -r requirements.txt

REM 개발 의존성 설치 (선택적)
if "%1"=="--dev" (
    echo 개발 의존성 설치 중...
    pip install -r requirements-dev.txt
)

echo 가상환경 설정 완료!
echo 활성화 방법: venv\Scripts\activate

#!/bin/bash
# DN_Solution2 가상환경 설정 스크립트 (Linux/Mac)

set -e

echo "=============================================="
echo "DN_SOLUTION2 개발환경 설정을 시작합니다..."
echo "=============================================="

# 현재 디렉토리 확인
if [ ! -f "manage.py" ]; then
    echo "[ERROR] manage.py 파일을 찾을 수 없습니다."
    echo "프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

# Python 버전 확인
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3이 설치되지 않았습니다."
    echo "Python 3.11+ 버전을 설치해주세요."
    exit 1
fi

echo "[INFO] Python 버전: $(python3 --version)"

# 가상환경 생성
if [ -d "venv" ]; then
    echo "[INFO] 기존 가상환경이 발견되었습니다."
    read -p "기존 가상환경을 삭제하고 새로 만드시겠습니까? (y/N): " choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        echo "[INFO] 기존 가상환경을 삭제합니다..."
        rm -rf venv
    else
        echo "[INFO] 기존 가상환경을 사용합니다."
        source venv/bin/activate
        echo "[INFO] 가상환경이 활성화되었습니다."
        echo "현재 Python: $(which python)"
        exit 0
    fi
fi

echo "[INFO] 가상환경을 생성합니다..."
python3 -m venv venv

echo "[INFO] 가상환경을 활성화합니다..."
source venv/bin/activate

# pip 업그레이드
echo "[INFO] pip을 업그레이드합니다..."
pip install --upgrade pip

# 의존성 설치
echo "[INFO] Python 패키지를 설치합니다..."
pip install -r requirements.txt

# 개발용 의존성 설치
if [ -f "requirements-dev.txt" ]; then
    echo "[INFO] 개발용 패키지를 설치합니다..."
    pip install -r requirements-dev.txt
fi

# 환경변수 파일 설정
if [ ! -f ".env" ]; then
    if [ -f ".env.dev" ]; then
        echo "[INFO] 개발용 환경변수 파일을 복사합니다..."
        cp .env.dev .env
    else
        echo "[WARNING] .env 파일이 없습니다. .env.example을 참고하여 생성해주세요."
    fi
fi

# 로그 디렉토리 생성
mkdir -p logs

# 데이터베이스 마이그레이션 (PostgreSQL이 실행 중인 경우에만)
echo "[INFO] 데이터베이스 연결을 확인합니다..."
if python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection(); print('DB 연결 성공')" 2>/dev/null; then
    echo "[INFO] 데이터베이스 마이그레이션을 실행합니다..."
    python manage.py migrate
    
    read -p "슈퍼유저를 생성하시겠습니까? (y/N): " create_superuser
    if [[ "$create_superuser" =~ ^[Yy]$ ]]; then
        python manage.py createsuperuser
    fi
else
    echo "[WARNING] 데이터베이스에 연결할 수 없습니다."
    echo "PostgreSQL이 실행 중인지 확인하거나 Docker를 사용하세요."
fi

echo
echo "=============================================="
echo "가상환경 설정이 완료되었습니다!"
echo "=============================================="
echo
echo "다음 명령어로 개발 서버를 시작할 수 있습니다:"
echo "  1. 가상환경 활성화: source venv/bin/activate"
echo "  2. 개발 서버 실행: python manage.py runserver"
echo
echo "또는 Docker를 사용하려면:"
echo "  docker-compose up -d"
echo
echo "현재 가상환경이 활성화되어 있습니다."
echo "현재 Python: $(which python)"

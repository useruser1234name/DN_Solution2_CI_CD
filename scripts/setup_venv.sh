#!/bin/bash
# 가상환경 설정 스크립트

# 파이썬 버전 확인
PYTHON_VERSION=$(python --version 2>&1)
echo "시스템 파이썬 버전: $PYTHON_VERSION"

# 가상환경 생성
if [ ! -d "venv" ]; then
    echo "가상환경 생성 중..."
    python -m venv venv
else
    echo "가상환경이 이미 존재합니다."
fi

# 가상환경 활성화
echo "가상환경 활성화 중..."
source venv/bin/activate || source venv/Scripts/activate

# pip 업그레이드
echo "pip 업그레이드 중..."
pip install --upgrade pip==24.0

# 의존성 설치
echo "의존성 설치 중..."
pip install -r requirements.txt

# 개발 의존성 설치 (선택적)
if [ "$1" = "--dev" ]; then
    echo "개발 의존성 설치 중..."
    pip install -r requirements-dev.txt
fi

echo "가상환경 설정 완료!"
echo "활성화 방법: source venv/bin/activate (Linux/Mac) 또는 venv\\Scripts\\activate (Windows)"

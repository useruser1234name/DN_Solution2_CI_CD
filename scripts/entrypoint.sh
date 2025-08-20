#!/bin/bash
set -e

echo "🚀 DN_SOLUTION2 백엔드 컨테이너 시작 중..."

# 환경 변수 출력 (보안상 중요한 정보는 제외)
echo "📊 환경 정보:"
echo "  - Django Settings: ${DJANGO_SETTINGS_MODULE:-기본값}"
echo "  - Debug Mode: ${DEBUG:-False}"
echo "  - Python Version: $(python --version)"
echo "  - Working Directory: $(pwd)"

# 로그 디렉토리 생성
mkdir -p /app/logs
echo "📁 로그 디렉토리 생성 완료"

# Static files 디렉토리 생성
mkdir -p /app/staticfiles
echo "📁 Static files 디렉토리 생성 완료"

# Media files 디렉토리 생성
mkdir -p /app/media
echo "📁 Media files 디렉토리 생성 완료"

# 권한 설정 (non-root 사용자인 경우)
if [ "$(id -u)" != "0" ]; then
    echo "👤 Non-root 사용자로 실행 중"
fi

# Health check 엔드포인트를 위한 더미 파일 생성 (필요한 경우)
# echo "OK" > /app/health.txt

echo "✅ 초기화 완료! 메인 명령어 실행 중..."
echo "🔄 명령어: $@"

# 전달받은 명령어 실행
exec "$@"

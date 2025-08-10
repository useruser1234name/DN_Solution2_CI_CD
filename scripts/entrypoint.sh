#!/bin/bash
# Django Backend Entrypoint Script - DN_SOLUTION2

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 DN_SOLUTION2 Backend Starting...${NC}"

# 환경 변수 확인
echo -e "${YELLOW}📋 환경 설정 확인${NC}"
echo "DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-dn_solution.settings.development}"
echo "DATABASE_URL: ${DATABASE_URL:-Not set}"
echo "REDIS_URL: ${REDIS_URL:-Not set}"
echo "DEBUG: ${DEBUG:-True}"

# 데이터베이스 연결 대기
echo -e "${YELLOW}⏳ 데이터베이스 연결 대기 중...${NC}"
while ! python manage.py dbshell --command="SELECT 1;" >/dev/null 2>&1; do
    echo "데이터베이스 연결 대기 중..."
    sleep 2
done
echo -e "${GREEN}✅ 데이터베이스 연결 성공${NC}"

# Redis 연결 확인
if [ ! -z "$REDIS_URL" ]; then
    echo -e "${YELLOW}⏳ Redis 연결 확인 중...${NC}"
    python -c "
import redis
import os
from urllib.parse import urlparse

try:
    redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379')
    url = urlparse(redis_url)
    r = redis.Redis(host=url.hostname, port=url.port, db=url.path[1:] if url.path else 0)
    r.ping()
    print('✅ Redis 연결 성공')
except Exception as e:
    print(f'❌ Redis 연결 실패: {e}')
    exit(1)
"
fi

# 마이그레이션 실행
echo -e "${YELLOW}🔄 데이터베이스 마이그레이션 실행${NC}"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# 스태틱 파일 수집 (운영환경)
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ]; then
    echo -e "${YELLOW}📦 정적 파일 수집${NC}"
    python manage.py collectstatic --noinput --clear
fi

# 슈퍼유저 생성 (개발환경)
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo -e "${YELLOW}👤 개발용 슈퍼유저 생성${NC}"
    python manage.py shell -c "
from django.contrib.auth import get_user_model
from companies.models import Company, CompanyUser

User = get_user_model()

# 슈퍼유저가 없으면 생성
if not User.objects.filter(is_superuser=True).exists():
    print('슈퍼유저 생성 중...')
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@dn-solution.com',
        password='admin123'
    )
    
    # HQ 회사 생성
    hq_company, created = Company.objects.get_or_create(
        code='HQ20240810000000INIT',
        defaults={
            'name': 'DN Solution HQ',
            'type': 'headquarters',
            'business_number': '123-45-67890',
            'address': '서울특별시 강남구 테헤란로 123',
            'contact_number': '02-1234-5678',
            'status': True,
        }
    )
    
    # CompanyUser 생성
    company_user, created = CompanyUser.objects.get_or_create(
        django_user=superuser,
        defaults={
            'company': hq_company,
            'username': 'admin',
            'role': 'admin',
            'status': 'approved',
            'is_approved': True,
            'is_primary_admin': True,
        }
    )
    
    print('✅ 개발용 계정 생성 완료')
    print('   Username: admin')
    print('   Password: admin123')
    print('   Company: DN Solution HQ')
else:
    print('✅ 슈퍼유저가 이미 존재합니다')
"
fi

# 초기 데이터 로드 (개발환경)
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo -e "${YELLOW}📊 초기 데이터 로드${NC}"
    python manage.py shell -c "
from companies.models import Company
from policies.models import TelecomProvider, Plan

# 통신사 데이터 생성
providers_data = [
    {'name': 'SKT', 'code': 'SKT', 'is_active': True},
    {'name': 'KT', 'code': 'KT', 'is_active': True},
    {'name': 'LG유플러스', 'code': 'LGU', 'is_active': True},
]

for data in providers_data:
    provider, created = TelecomProvider.objects.get_or_create(
        code=data['code'],
        defaults=data
    )
    if created:
        print(f'통신사 생성: {provider.name}')

# 요금제 데이터 생성
plans_data = [
    {'name': '5G 프리미엄 10K', 'code': '5G_PREMIUM_10K', 'monthly_fee': 100000, 'category': '10K+', 'provider_code': 'SKT'},
    {'name': '5G 프리미엄 8K', 'code': '5G_PREMIUM_8K', 'monthly_fee': 80000, 'category': '8K', 'provider_code': 'SKT'},
    {'name': '5G 슈퍼플랜 10K', 'code': '5G_SUPER_10K', 'monthly_fee': 100000, 'category': '10K+', 'provider_code': 'KT'},
    {'name': '5G 슈퍼플랜 8K', 'code': '5G_SUPER_8K', 'monthly_fee': 80000, 'category': '8K', 'provider_code': 'KT'},
    {'name': '5G 플러스 10K', 'code': '5G_PLUS_10K', 'monthly_fee': 100000, 'category': '10K+', 'provider_code': 'LGU'},
    {'name': '5G 플러스 8K', 'code': '5G_PLUS_8K', 'monthly_fee': 80000, 'category': '8K', 'provider_code': 'LGU'},
]

for data in plans_data:
    provider = TelecomProvider.objects.get(code=data['provider_code'])
    plan, created = Plan.objects.get_or_create(
        code=data['code'],
        defaults={
            'name': data['name'],
            'monthly_fee': data['monthly_fee'],
            'category': data['category'],
            'telecom_provider': provider,
            'is_active': True,
        }
    )
    if created:
        print(f'요금제 생성: {plan.name}')

print('✅ 초기 데이터 로드 완료')
"
fi

# Health check 엔드포인트 확인
echo -e "${YELLOW}🏥 Health check 준비${NC}"
python -c "
from django.core.management.utils import get_random_secret_key
print('Django 준비 완료')
"

echo -e "${GREEN}✅ DN_SOLUTION2 Backend 초기화 완료!${NC}"
echo -e "${BLUE}🌐 서버 시작...${NC}"

# 명령어 실행
exec "$@"
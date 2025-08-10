#!/bin/bash
# DN_SOLUTION2 시스템 테스트 스크립트

echo "🚀 DN_SOLUTION2 시스템 테스트 시작"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본 설정
BASE_URL="http://localhost:8000"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

echo -e "${BLUE}📋 테스트 대상: ${BASE_URL}${NC}"

# 1. 서비스 상태 확인
echo -e "\n${YELLOW}1. 서비스 상태 확인${NC}"
docker-compose ps

# 2. 기본 헬스체크
echo -e "\n${YELLOW}2. 기본 헬스체크${NC}"
curl -s "${BASE_URL}/api/health/cache/" | jq '.' || echo "❌ 캐시 헬스체크 실패"

# 3. 로그인 테스트
echo -e "\n${YELLOW}3. 인증 시스템 테스트${NC}"
TOKEN=$(curl -s -X POST "${BASE_URL}/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USER}\",\"password\":\"${ADMIN_PASS}\"}" \
  | jq -r '.access // empty')

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✅ 로그인 성공${NC}"
    
    # 토큰 정보 확인
    curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/auth/token-info/" \
      | jq '.username, .company_type, .permissions' || echo "❌ 토큰 정보 조회 실패"
else
    echo -e "${RED}❌ 로그인 실패${NC}"
    exit 1
fi

# 4. 캐시 시스템 테스트
echo -e "\n${YELLOW}4. 캐시 시스템 테스트${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/admin/cache/status/" \
  | jq '.health.status, .stats.hit_rate' || echo "❌ 캐시 상태 조회 실패"

# 5. 대시보드 API 테스트
echo -e "\n${YELLOW}5. 대시보드 API 테스트${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/dashboard/stats/" \
  | jq '.total_companies, .total_users' || echo "❌ 대시보드 통계 조회 실패"

# 6. 권한 시스템 테스트
echo -e "\n${YELLOW}6. 권한 시스템 테스트${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "${BASE_URL}/api/permissions/user/" \
  | jq '.company_type, .hierarchy_level, .combined_permissions | keys' || echo "❌ 권한 조회 실패"

# 7. 성능 간단 테스트 (Python 스크립트 사용)
echo -e "\n${YELLOW}7. 성능 테스트 (간단)${NC}"
if command -v python3 &> /dev/null; then
    python3 scripts/load_test.py --test-type cache --users 5 --requests 3
else
    echo "Python3이 설치되지 않아 성능 테스트를 건너뜁니다."
fi

# 8. 로그 확인
echo -e "\n${YELLOW}8. 최근 로그 확인${NC}"
docker-compose logs --tail=10 backend | tail -5

echo -e "\n${GREEN}🎉 시스템 테스트 완료!${NC}"
echo -e "\n${BLUE}📊 추가 테스트 명령어:${NC}"
echo "  - 전체 부하 테스트: python3 scripts/load_test.py --test-type full --users 50"
echo "  - 스트레스 테스트: python3 scripts/load_test.py --test-type stress"
echo "  - 캐시 관리: docker-compose exec backend python manage.py cache_management status"
echo "  - 로그 모니터링: docker-compose logs -f backend"
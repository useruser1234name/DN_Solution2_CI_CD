# Redis 캐시 시스템 가이드 - DN_SOLUTION2

## 개요

DN_SOLUTION2 프로젝트의 성능 최적화를 위한 다층 Redis 캐시 시스템 구현 가이드입니다.

## 시스템 구성

### 1. Multi-layer 캐싱 구조

```
┌─────────────┬─────────────┬──────────────────────┬─────────────────┐
│ Cache Level │ Backend     │ Purpose              │ Timeout         │
├─────────────┼─────────────┼──────────────────────┼─────────────────┤
│ L1          │ Local       │ 로컬 메모리 캐시     │ 5분             │
│ L2          │ Redis DB 1  │ 일반 데이터 캐시     │ 5분 (기본)      │
│ L2          │ Redis DB 2  │ 세션 데이터          │ 1시간           │
│ L2          │ Redis DB 3  │ API 응답 캐시        │ 30분            │
│ L2          │ Redis DB 4  │ 장기 보관 캐시       │ 24시간          │
│ L3          │ Database    │ ORM 쿼리 캐시        │ 변동            │
└─────────────┴─────────────┴──────────────────────┴─────────────────┘
```

### 2. 캐시 키 접두사 시스템

```python
CACHE_PREFIXES = {
    'user': 'user:',           # 사용자 데이터
    'company': 'company:',     # 회사 데이터  
    'policy': 'policy:',       # 정책 데이터
    'order': 'order:',         # 주문 데이터
    'rebate': 'rebate:',       # 리베이트 데이터
    'report': 'report:',       # 리포트 데이터
    'api': 'api:',             # API 응답
    'session': 'session:',     # 세션 데이터
    'permission': 'perm:',     # 권한 데이터
}
```

## 사용법

### 1. 기본 캐시 사용

```python
from dn_solution.cache_manager import cache_manager

# 데이터 저장
cache_manager.set('my_key', {'data': 'value'}, timeout=300)

# 데이터 조회
data = cache_manager.get('my_key', default={})

# 데이터 삭제
cache_manager.delete('my_key')

# 패턴 매칭 삭제
count = cache_manager.delete_pattern('user:*')
```

### 2. 데코레이터 사용

#### API 응답 캐싱

```python
from dn_solution.cache_manager import cached_api_response

@cached_api_response(timeout=600, key_prefix='company_list')
def company_list_view(request):
    companies = Company.objects.filter(status=True)
    return JsonResponse({'companies': list(companies.values())})
```

#### QuerySet 결과 캐싱

```python
from dn_solution.cache_manager import cached_queryset

@cached_queryset(timeout=1800, key_prefix='active_policies')
def get_active_policies():
    return Policy.objects.filter(is_active=True).select_related('telecom_provider')
```

#### 캐시 무효화

```python
from dn_solution.cache_manager import invalidate_cache_pattern

@invalidate_cache_pattern('company:*')
def update_company(request, company_id):
    # 회사 정보 업데이트 로직
    pass
```

### 3. 유틸리티 함수 사용

```python
from dn_solution.cache_utils import (
    cache_user_data, cache_company_hierarchy, 
    cache_policy_rules, cache_dashboard_data
)

# 사용자 데이터 캐싱
user_data = cache_user_data(user_id=1, data_type='profile')

# 회사 계층 구조 캐싱  
hierarchy = cache_company_hierarchy(company_id=1)

# 정책 규칙 캐싱
all_policies = cache_policy_rules()
specific_policy = cache_policy_rules(policy_id=1)

# 대시보드 데이터 캐싱
dashboard = cache_dashboard_data(user_id=1, company_id=1)
```

### 4. 모델 메소드 캐싱

```python
from dn_solution.cache_utils import cache_model_method

class Company(models.Model):
    @cache_model_method(timeout=3600)
    def get_subordinates(self):
        return Company.objects.filter(parent_company=self)
    
    @cache_model_method(timeout=1800)
    def calculate_total_orders(self, month=None):
        # 계산 집약적인 작업
        return self.orders.filter(created_at__month=month).count()
```

### 5. 캐시 무효화 자동화

```python
from dn_solution.cache_utils import invalidate_on_save

class Company(models.Model):
    @invalidate_on_save(['company:{pk}', 'company_hierarchy:*', 'api:*companies*'])
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
```

## 관리 명령어

### 1. 캐시 상태 확인

```bash
python manage.py cache_management status
python manage.py cache_management health_check
python manage.py cache_management stats --json
```

### 2. 캐시 관리

```bash
# 전체 캐시 삭제
python manage.py cache_management clear

# 패턴 매칭 캐시 삭제
python manage.py cache_management invalidate --pattern "user:*"

# 캐시 워밍업
python manage.py cache_management warm_up
```

### 3. 성능 테스트

```bash
python manage.py cache_management test_performance --iterations 1000
```

## 관리자 API

### 1. 캐시 모니터링

```bash
# 캐시 상태 조회
GET /api/admin/cache/status/

# 캐시 대시보드
GET /api/admin/cache/dashboard/

# 헬스체크 (인증 불필요)
GET /api/health/cache/
```

### 2. 캐시 조작

```bash
# 캐시 삭제
POST /api/admin/cache/clear/
{
    "pattern": "user:*"  // 선택적, 없으면 전체 삭제
}

# 캐시 워밍업
POST /api/admin/cache/warm-up/

# 성능 테스트
GET /api/admin/cache/performance/?iterations=100
```

### 3. 개발용 도구

```bash
# 캐시 키 목록 조회
GET /api/admin/cache/keys/?pattern=user:*&limit=50

# 캐시 패턴 무효화
POST /api/admin/cache/invalidate/
{
    "patterns": ["user:*", "company:*"]
}
```

## 성능 최적화 설정

### 1. Redis 설정 최적화

```python
# settings/production.py
CACHES = {
    'default': {
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,    # 연결 풀 크기 증가
                'retry_on_timeout': True,
                'health_check_interval': 30,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Redis 장애 시 우아한 처리
        },
    }
}
```

### 2. 캐시 미들웨어 순서

```python
MIDDLEWARE = [
    # ... 기본 미들웨어들 ...
    'dn_solution.middleware.cache_middleware.PerformanceCacheMiddleware',  # 첫 번째
    'dn_solution.middleware.cache_middleware.UserPermissionCacheMiddleware',
    'dn_solution.middleware.cache_middleware.CacheInvalidationMiddleware',
    'dn_solution.middleware.cache_middleware.CacheMetricsMiddleware',      # 마지막
    # ... 다른 미들웨어들 ...
]
```

### 3. 캐시 전략별 타임아웃 설정

```python
CACHE_TIMEOUTS = {
    'realtime': 60,        # 1분 - 실시간 데이터
    'short': 300,          # 5분 - 자주 변경되는 데이터
    'medium': 1800,        # 30분 - 일반 데이터
    'long': 3600,          # 1시간 - 안정적인 데이터
    'daily': 86400,        # 24시간 - 정적 데이터
    'weekly': 604800,      # 7일 - 매우 안정적인 데이터
}
```

## 모니터링

### 1. 캐시 히트율 모니터링

```python
# 예상 성능 지표
Target Metrics:
- Cache Hit Rate: > 85%
- Average Response Time: < 50ms
- Redis Memory Usage: < 80%
- Connection Pool Usage: < 70%
```

### 2. 로그 모니터링

```python
# 캐시 관련 로그 설정
LOGGING = {
    'loggers': {
        'dn_solution.cache_manager': {
            'handlers': ['cache_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'dn_solution.middleware.cache_middleware': {
            'handlers': ['cache_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 3. 성능 측정

```bash
# Redis 성능 모니터링
redis-cli --latency-history -i 1

# Django 캐시 통계
python manage.py cache_management stats

# 성능 테스트
python manage.py cache_management test_performance --iterations 10000
```

## 트러블슈팅

### 1. 일반적인 문제

**Redis 연결 실패**
```bash
# Redis 서버 상태 확인
docker exec -it dn_solution_redis redis-cli ping

# 연결 설정 확인
python manage.py shell
>>> from django.core.cache import cache
>>> cache.get('test')
```

**캐시 히트율 낮음**
```python
# 캐시 키 패턴 분석
python manage.py cache_management status

# 키 충돌 확인
GET /api/admin/cache/keys/?pattern=*
```

**메모리 사용량 증가**
```bash
# Redis 메모리 사용량 확인
redis-cli info memory

# 불필요한 키 정리
python manage.py cache_management clear --pattern "old_*"
```

### 2. 성능 최적화

**캐시 히트율 개선**
- 적절한 타임아웃 설정
- 캐시 키 설계 최적화
- 사용자별/회사별 캐시 분리

**메모리 효율성 개선**
- 데이터 압축 활용
- 불필요한 데이터 제거
- 캐시 만료 정책 최적화

**네트워크 최적화**
- 연결 풀 크기 조정
- 배치 연산 활용
- 파이프라이닝 적용

## 보안 고려사항

### 1. 데이터 보호

```python
# 민감한 데이터 캐싱 금지
SENSITIVE_CACHE_EXCLUSIONS = [
    'password', 'ssn', 'credit_card', 'token', 'secret'
]

# 캐시 키 암호화 (필요시)
import hashlib
cache_key = hashlib.sha256(f"user:{user_id}".encode()).hexdigest()
```

### 2. 접근 제어

```python
# 관리자 API 인증
@permission_classes([IsAdminUser])
def cache_admin_view(request):
    pass

# Redis 연결 보안
REDIS_URL = "redis://:password@localhost:6379/1"
```

### 3. 데이터 만료

```python
# 자동 만료 설정
cache_manager.set('sensitive_data', data, timeout=300)  # 5분 후 자동 삭제

# 명시적 삭제
cache_manager.delete_pattern('session:expired_*')
```

## 결론

이 Redis 캐시 시스템은 DN_SOLUTION2 프로젝트의 성능을 대폭 개선할 것으로 예상됩니다:

- **응답 시간**: 50-80% 단축
- **데이터베이스 부하**: 60-70% 감소  
- **동시 사용자**: 1,500명까지 안정적 처리
- **처리량**: 1,000 RPS 목표 달성

정기적인 모니터링과 최적화를 통해 지속적인 성능 향상을 이룰 수 있습니다.
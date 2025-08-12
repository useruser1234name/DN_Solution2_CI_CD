# DN_SOLUTION2 프로젝트 분석 및 리팩토링 가이드

## 📌 프로젝트 개요

### 비즈니스 모델
휴대폰 도매업 계층 구조를 관리하는 SaaS 플랫폼

```
본사(HQ) - 휴대폰 도매업 운영사
  ├── 협력사 A (Agency) - 지역 총판
  │     ├── 판매점 A-1 (Retail) - 휴대폰 매장
  │     └── 판매점 A-2 (Retail) - 휴대폰 매장
  └── 협력사 B (Agency) - 지역 총판
        ├── 판매점 B-1 (Retail) - 휴대폰 매장
        └── 판매점 B-2 (Retail) - 휴대폰 매장
```

## 🛠 기술 스택

- **Backend**: Django 4.2.7 + Django REST Framework
- **Frontend**: React 19.1.1 + Ant Design
- **Database**: PostgreSQL (개발 환경에서는 SQLite 가능)
- **Cache**: Redis (다중 레이어 캐싱)
- **Task Queue**: Celery + Redis
- **Container**: Docker Compose
- **인증**: JWT (Simple JWT)

## 📁 프로젝트 구조

```
DN_Solution2/
├── companies/         # 업체 관리 (구현됨)
├── policies/          # 정책 관리 (구현됨)
├── orders/           # 주문 관리 (구현됨)
├── inventory/        # 재고 관리 (제거 예정)
├── messaging/        # 메시징 (제거 예정)
├── frontend/         # React 프론트엔드
├── dn_solution/      # Django 설정 및 공통 모듈
├── templates/        # Django 템플릿
├── static/          # 정적 파일
├── media/           # 미디어 파일
├── scripts/         # 유틸리티 스크립트
└── docker-compose.yml
```

## 🚨 명세서와 실제 구현의 차이점

### 1. 민감정보 처리 시스템 ❌ 미구현

#### 명세 요구사항
- Redis 임시 저장 (TTL 24시간)
- 본사 승인 후 해시화하여 DB 영구 저장
- 로그에는 마스킹 처리

#### 현재 상태
- 민감정보 처리 로직 없음
- 평문으로 DB에 직접 저장

#### 구현 필요
```python
# core/sensitive_data.py 생성 필요
class SensitiveDataManager:
    def store_temporary(self, data, key, ttl=86400)
    def retrieve_temporary(self, key)
    def hash_and_store(self, data)
    def mask_for_logging(self, data)
```

### 2. 주문서 양식 설계 시스템 ❌ 미구현

#### 명세 요구사항
- 본사가 정책별 주문서 양식 동적 설계
- JSON 형식으로 필드 정의
- 필수/선택 필드 구분
- 유효성 검증 규칙

#### 현재 상태
- OrderFormTemplate, OrderFormField 모델만 존재
- 실제 양식 빌더 미구현
- 동적 렌더링 시스템 없음

#### 구현 필요
```python
# policies/form_builder.py 생성 필요
class FormBuilder:
    def create_template(self, policy, fields)
    def validate_submission(self, template, data)
    def render_form(self, template)
```

### 3. 리베이트 매트릭스 ❌ 미구현

#### 명세 요구사항
```
요금제/기간  │ 3개월  │ 6개월  │ 9개월  │ 12개월
─────────────┼────────┼────────┼────────┼────────
3만원대      │ 50,000 │ 60,000 │ 70,000 │ 80,000
5만원대      │ 70,000 │ 85,000 │100,000 │120,000
```

#### 현재 상태
- 단순 필드만 존재 (rebate_agency, rebate_retail)
- 매트릭스 구조 없음

#### 구현 필요
```python
# policies/models.py에 추가
class RebateMatrix(models.Model):
    policy = models.ForeignKey(Policy)
    plan_type = models.CharField()  # 3만원대, 5만원대 등
    period = models.IntegerField()  # 3, 6, 9, 12개월
    rebate_amount = models.DecimalField()
```

### 4. 정산 시스템 ❌ 미구현

#### 명세 요구사항
- 주문 완료 시 자동 정산
- 계층별 정산 대시보드
- 정산 승인 워크플로우

#### 현재 상태
- 정산 관련 모델/뷰 없음

#### 구현 필요
```python
# settlements/models.py 생성 필요
class Settlement(models.Model):
    order = models.ForeignKey(Order)
    company = models.ForeignKey(Company)
    rebate_amount = models.DecimalField()
    status = models.CharField()  # pending, approved, paid
```

## ✅ 구현된 기능

### 1. 회원가입 및 업체 관리
- ✅ 관리자 회원가입 시 업체 자동 생성
- ✅ 업체 코드 자동 생성 (A-YYMMDD-01 형식)
- ✅ 계층 구조 검증
- ✅ 승인 시스템 (상위 업체 관리자가 승인)

### 2. 정책 관리
- ✅ 정책 CRUD
- ✅ 정책 노출 설정
- ✅ 협력사별 정책 배정

### 3. 주문 관리
- ✅ 주문 CRUD
- ✅ 주문 상태 관리
- ✅ 송장 등록

## 🔧 리팩토링 작업 목록

### Phase 1: 핵심 기능 구현 (우선순위: 높음)

#### 1.1 민감정보 처리 시스템
```python
# core/sensitive_data.py
- Redis 임시 저장 매니저 구현
- 해시화 유틸리티 구현
- 로그 마스킹 미들웨어 구현
```

#### 1.2 리베이트 매트릭스
```python
# policies/models.py
- RebateMatrix 모델 추가
- 매트릭스 기반 리베이트 계산 로직
```

#### 1.3 주문서 양식 빌더
```python
# policies/form_builder.py
- 동적 양식 생성기
- 양식 검증 엔진
- Frontend 양식 렌더러
```

#### 1.4 정산 시스템
```python
# settlements/ (새 앱 생성)
- Settlement 모델
- 자동 정산 트리거
- 정산 대시보드 API
```

### Phase 2: 코드 품질 개선

#### 2.1 공통 Base 클래스
```python
# core/models.py
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

#### 2.2 권한 시스템 중앙화
```python
# core/permissions.py
class HierarchyPermission:
    def has_object_permission(self, request, view, obj)
```

#### 2.3 API 응답 표준화
```python
# core/serializers.py
class StandardResponseSerializer:
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField()
```

### Phase 3: 성능 최적화

#### 3.1 쿼리 최적화
```python
# N+1 문제 해결
PolicyAssignment.objects.select_related('policy', 'company')
Order.objects.prefetch_related('memos', 'requests')
```

#### 3.2 캐시 전략
```python
# 캐시 태그 기반 무효화
CACHE_TAGS = {
    'policy': ['policy_list', 'policy_detail'],
    'order': ['order_list', 'order_stats'],
}
```

### Phase 4: 제거 작업

#### 4.1 불필요한 앱 제거
```python
# settings/base.py
LOCAL_APPS = [
    'companies',
    'policies', 
    'orders',
    # 'inventory',  # 제거
    # 'messaging',  # 제거
]
```

#### 4.2 URL 정리
```python
# urls.py
# path('api/inventory/', include('inventory.urls')),  # 제거
# path('api/messaging/', include('messaging.urls')),  # 제거
```

### Phase 5: Frontend 리팩토링

#### 5.1 메뉴 정리
- 재고 메뉴 제거
- 메시징 메뉴 제거
- 직원 가입 옵션 제거

#### 5.2 상태 관리 도입
- Redux Toolkit 또는 Zustand 도입
- API 서비스 레이어 구축

### Phase 6: CI/CD 구축

#### 6.1 GitHub Actions 설정
```yaml
# .github/workflows/ci.yml
- 테스트 자동화
- 코드 품질 체크
- 보안 스캔
```

#### 6.2 환경별 Docker Compose
```yaml
# docker-compose.production.yml
# docker-compose.staging.yml
# docker-compose.development.yml
```

## 🎯 즉시 수정 필요 사항

1. **보안**: 민감정보 평문 저장 문제
2. **데이터 무결성**: 트랜잭션 처리 부재
3. **권한**: 계층 구조 무시 가능한 취약점
4. **성능**: N+1 쿼리 문제

## 📝 특별 참고사항

### 최초 본사 생성 문제
- 본사 관리자는 승인할 상위가 없음
- 해결방안:
  1. 본사 타입 가입 시 자동 승인
  2. Django 슈퍼유저가 승인
  3. 초기 설정 스크립트 제공

### 데이터베이스 마이그레이션 주의
```bash
# 리팩토링 시 마이그레이션 순서
1. python manage.py makemigrations
2. python manage.py migrate --fake  # 기존 데이터 보존
3. python manage.py migrate
```

## 🚀 리팩토링 시작 명령

```bash
# 1. 가상환경 활성화
source venv/Scripts/activate  # Windows
source venv/bin/activate      # Linux/Mac

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일 수정

# 4. 데이터베이스 초기화
python manage.py migrate

# 5. 슈퍼유저 생성
python manage.py createsuperuser

# 6. 개발 서버 실행
python manage.py runserver

# 7. Docker로 실행 (선택사항)
docker-compose up -d
```

## 📚 참고 문서

- [DN_SOLUTION 1차 MVP.txt](./DN_SOLUTION%201차%20MVP.txt) - 원본 명세서
- [리팩토링_완료_보고서.md](./리팩토링_완료_보고서.md) - 이전 리팩토링 기록
- [ISSUES.md](./ISSUES.md) - 알려진 이슈 목록

---

**작성일**: 2024-12-24
**작성자**: Claude AI Assistant
**용도**: 클로드코드(Claude Code)를 통한 전체 리팩토링 작업 가이드

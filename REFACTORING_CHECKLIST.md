# DN_SOLUTION2 리팩토링 체크리스트

## 📋 리팩토링 작업 순서

### Phase 1: 기초 설정 (Day 1)
- [ ] **1.1 개발 환경 점검**
  ```bash
  # Python 버전 확인 (3.11+)
  python --version
  
  # 가상환경 활성화
  venv\Scripts\activate
  
  # 패키지 업데이트
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

- [ ] **1.2 백업 수행**
  ```bash
  # 데이터베이스 백업
  python manage.py dumpdata > backup_20241224.json
  
  # 코드 백업 (새 브랜치)
  git checkout -b backup/before-refactoring
  git push origin backup/before-refactoring
  
  # 리팩토링 브랜치 생성
  git checkout -b refactor/main
  ```

- [ ] **1.3 불필요한 앱 제거**
  ```python
  # settings/base.py에서 제거
  LOCAL_APPS = [
      'companies',
      'policies', 
      'orders',
      # 'inventory',  # 제거
      # 'messaging',  # 제거
  ]
  ```
  ```bash
  # 물리적 삭제
  rm -rf inventory/
  rm -rf messaging/
  ```

### Phase 2: Core 앱 생성 (Day 1-2)

- [ ] **2.1 Core 앱 생성**
  ```bash
  python manage.py startapp core
  ```

- [ ] **2.2 Core 모델 구현**
  - [ ] core/models.py - AbstractBaseModel
  - [ ] core/permissions.py - HierarchyPermission
  - [ ] core/sensitive_data.py - SensitiveDataManager
  - [ ] core/cache_manager.py - CacheStrategy
  - [ ] core/exceptions.py - CustomExceptions

- [ ] **2.3 민감정보 처리 구현**
  ```python
  # core/sensitive_data.py
  class SensitiveDataManager:
      - store_temporary()
      - retrieve_temporary()
      - hash_and_store()
      - mask_for_logging()
  ```

### Phase 3: Policies 앱 리팩토링 (Day 2-3)

- [ ] **3.1 리베이트 매트릭스 모델 추가**
  ```python
  # policies/models.py
  class RebateMatrix(models.Model):
      policy = ForeignKey(Policy)
      carrier = CharField()
      plan_range = IntegerField()
      contract_period = IntegerField()
      rebate_amount = DecimalField()
  ```

- [ ] **3.2 주문서 양식 빌더 구현**
  - [ ] policies/form_builder.py 생성
  - [ ] OrderFormTemplate 모델 수정
  - [ ] 동적 양식 검증 로직

- [ ] **3.3 마이그레이션 생성 및 실행**
  ```bash
  python manage.py makemigrations policies
  python manage.py migrate policies
  ```

### Phase 4: Orders 앱 리팩토링 (Day 3-4)

- [ ] **4.1 민감정보 필드 추가**
  ```python
  # orders/models.py
  class Order:
      + sensitive_data_key = CharField()
      + is_sensitive_data_processed = BooleanField()
  
  class OrderSensitiveData(models.Model):  # 새 모델
      order = OneToOneField(Order)
      customer_name_hash = CharField()
      customer_phone_hash = CharField()
  ```

- [ ] **4.2 주문 승인 프로세스 수정**
  - [ ] 승인 시 민감정보 처리 로직 추가
  - [ ] Redis → PostgreSQL 이동 구현

### Phase 5: Settlements 앱 생성 (Day 4-5)

- [ ] **5.1 Settlements 앱 생성**
  ```bash
  python manage.py startapp settlements
  ```

- [ ] **5.2 정산 모델 구현**
  - [ ] Settlement 모델
  - [ ] SettlementBatch 모델
  - [ ] 자동 정산 로직

- [ ] **5.3 정산 API 구현**
  - [ ] 정산 계산 API
  - [ ] 정산 승인 API
  - [ ] 정산 대시보드 API

### Phase 6: API 최적화 (Day 5-6)

- [ ] **6.1 쿼리 최적화**
  ```python
  # N+1 문제 해결
  - PolicyAssignment select_related 추가
  - Order prefetch_related 추가
  ```

- [ ] **6.2 캐시 전략 구현**
  - [ ] 캐시 키 패턴 정의
  - [ ] 캐시 무효화 로직
  - [ ] 캐시 워밍업

- [ ] **6.3 페이지네이션 개선**
  - [ ] CursorPagination 적용
  - [ ] 필터링 최적화

### Phase 7: Frontend 리팩토링 (Day 6-7)

- [ ] **7.1 API 서비스 레이어 구축**
  ```javascript
  // src/services/
  - api.js (axios 인스턴스)
  - policyService.js
  - orderService.js
  - settlementService.js
  ```

- [ ] **7.2 상태 관리 도입**
  ```bash
  npm install @reduxjs/toolkit react-redux
  # 또는
  npm install zustand
  ```

- [ ] **7.3 컴포넌트 정리**
  - [ ] 재고 관련 컴포넌트 제거
  - [ ] 메시징 관련 컴포넌트 제거
  - [ ] FormBuilder 컴포넌트 추가
  - [ ] 정산 대시보드 추가

### Phase 8: 테스트 (Day 7-8)

- [ ] **8.1 단위 테스트 작성**
  ```bash
  # Django 테스트
  python manage.py test companies
  python manage.py test policies
  python manage.py test orders
  python manage.py test settlements
  ```

- [ ] **8.2 통합 테스트**
  - [ ] 민감정보 플로우 테스트
  - [ ] 리베이트 계산 테스트
  - [ ] 권한 체계 테스트

- [ ] **8.3 Frontend 테스트**
  ```bash
  npm test
  ```

### Phase 9: 문서화 (Day 8)

- [ ] **9.1 API 문서 업데이트**
  - [ ] Swagger/OpenAPI 스펙 생성
  - [ ] Postman Collection 생성

- [ ] **9.2 README 업데이트**
  - [ ] 설치 가이드
  - [ ] 환경 설정
  - [ ] API 사용법

- [ ] **9.3 변경사항 문서화**
  - [ ] CHANGELOG.md 작성
  - [ ] 마이그레이션 가이드

### Phase 10: 배포 준비 (Day 9)

- [ ] **10.1 환경별 설정 분리**
  ```python
  # settings/
  - development.py
  - staging.py
  - production.py
  ```

- [ ] **10.2 Docker 설정 정리**
  ```yaml
  # docker-compose 파일 분리
  - docker-compose.yml (개발)
  - docker-compose.staging.yml
  - docker-compose.production.yml
  ```

- [ ] **10.3 CI/CD 파이프라인 구축**
  ```yaml
  # .github/workflows/ci.yml
  - 테스트 자동화
  - 빌드 및 배포
  ```

## 🔍 검증 체크리스트

### 기능 검증
- [ ] 회원가입 및 로그인 정상 작동
- [ ] 정책 CRUD 정상 작동
- [ ] 주문서 작성 및 승인 정상 작동
- [ ] 민감정보 마스킹 확인
- [ ] 리베이트 계산 정확성
- [ ] 정산 기능 정상 작동
- [ ] 권한 체계 정상 작동

### 성능 검증
- [ ] API 응답 시간 < 100ms
- [ ] 페이지 로딩 시간 < 2초
- [ ] 메모리 사용량 정상
- [ ] 데이터베이스 쿼리 최적화 확인

### 보안 검증
- [ ] 민감정보 암호화 확인
- [ ] SQL Injection 테스트
- [ ] XSS 테스트
- [ ] 권한 우회 테스트
- [ ] Rate Limiting 동작 확인

## 🚨 롤백 시나리오

### 긴급 롤백 절차
1. **서비스 중단**
   ```bash
   docker-compose down
   ```

2. **이전 버전 체크아웃**
   ```bash
   git checkout backup/before-refactoring
   ```

3. **데이터베이스 복원**
   ```bash
   python manage.py flush
   python manage.py loaddata backup_20241224.json
   ```

4. **서비스 재시작**
   ```bash
   docker-compose up -d
   ```

## 📅 일정 관리

| 단계 | 작업 내용 | 예상 소요 시간 | 완료 여부 |
|------|----------|---------------|----------|
| Phase 1 | 기초 설정 | 0.5일 | [ ] |
| Phase 2 | Core 앱 생성 | 1.5일 | [ ] |
| Phase 3 | Policies 리팩토링 | 1.5일 | [ ] |
| Phase 4 | Orders 리팩토링 | 1.5일 | [ ] |
| Phase 5 | Settlements 생성 | 1.5일 | [ ] |
| Phase 6 | API 최적화 | 1일 | [ ] |
| Phase 7 | Frontend 리팩토링 | 1.5일 | [ ] |
| Phase 8 | 테스트 | 1일 | [ ] |
| Phase 9 | 문서화 | 0.5일 | [ ] |
| Phase 10 | 배포 준비 | 0.5일 | [ ] |
| **총계** | | **10일** | |

## 📞 문제 발생 시 대응

### 주요 이슈별 해결 방법

#### 1. 마이그레이션 실패
```bash
# 마이그레이션 롤백
python manage.py migrate <app_name> <previous_migration_number>

# 마이그레이션 파일 삭제 후 재생성
rm <app>/migrations/00XX_*.py
python manage.py makemigrations
```

#### 2. Redis 연결 실패
```bash
# Redis 상태 확인
docker ps | grep redis
docker logs dn_solution_redis

# Redis 재시작
docker-compose restart redis
```

#### 3. Frontend 빌드 실패
```bash
# 캐시 삭제 후 재설치
rm -rf node_modules
rm package-lock.json
npm install
npm start
```

---

**문서 버전**: 1.0
**작성일**: 2024-12-24
**예상 완료일**: 2025-01-03
**담당**: Claude Code Assistant

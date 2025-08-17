# DN Solution 2 - 통합 테스트 가이드

이 디렉토리는 DN Solution 2 프로젝트의 모든 테스트 파일을 통합 관리합니다.

## 디렉토리 구조

### `/unit/` - 단위 테스트
- `test_api.py` - Companies API 테스트
- `test_cache.py` - 캐시 시스템 테스트 
- `test_models.py` - 모델 테스트
- `test_security.py` - 보안 테스트
- `test_services.py` - 서비스 로직 테스트

### `/e2e/` - End-to-End 테스트 (Playwright)
- `api-health.spec.js` - API 상태 확인 테스트
- `auth.spec.js` - 인증 기능 테스트
- `security.spec.js` - 보안 테스트
- `workflow.spec.js` - 업무 흐름 테스트
- `test-data.js` - 테스트 데이터 설정

### `/api/` - API 테스트
- 각 앱별 API 테스트 파일들

### `/system/` - 시스템 테스트
- `test_system_features.py` - 시스템 기능 통합 테스트
- `load_test.py` - 성능 및 부하 테스트
- `test_system.sh` - 시스템 테스트 스크립트
- `manage_test_data.py` - 테스트 데이터 관리

## 테스트 실행 방법

### 단위 테스트 실행
```bash
python manage.py test companies.tests
python manage.py test policies.tests
```

### E2E 테스트 실행 (Playwright)
```bash
npx playwright test
```

### 시스템 테스트 실행
```bash
python test_system_features.py
python manage_test_data.py
```

## 테스트 설정

- `pytest.ini` - pytest 설정
- `playwright.config.js` - Playwright 설정

## 주의사항

1. 테스트 실행 전 테스트 데이터베이스 설정 필요
2. E2E 테스트는 프론트엔드와 백엔드가 모두 실행 중이어야 함
3. 성능 테스트는 별도 환경에서 실행 권장


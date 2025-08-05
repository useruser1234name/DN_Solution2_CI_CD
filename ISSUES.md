# 현재 발생 중인 문제들

## ✅ 해결된 문제들

### 1. 데이터베이스 스키마 불일치 오류
**오류 메시지**: `table policies_policy has no column named form_type`

**상태**: ✅ 해결됨  
**해결일**: 2025-08-04  
**해결 방법**: 데이터베이스 재생성 및 마이그레이션 적용

**문제**: 정책 생성 시 `form_type` 컬럼이 없다는 데이터베이스 오류 발생

---

### 2. API 경로 중복 문제
**상태**: ✅ 해결됨  
**해결일**: 2025-08-04  
**해결 방법**: URL 구조 재설계

**문제**: 
- 프론트엔드에서 `get('api/list/')` 호출
- `api.js`에서 `API_BASE_URL = 'http://localhost:8001/api'` 설정
- Django URL 설정: `path('api/', include('policies.urls'))`
- `policies/urls.py`에서: `path('api/list/', views.policy_api_list)`
- 결과적으로 `/api/api/list/`로 요청이 가게 됨

**해결 내용**:
- 메인 URL 설정을 `path('api/policies/', include('policies.urls'))`로 변경
- policies 앱 내부 URL에서 중복된 `api/` 경로 제거
- orders 앱의 중복 URL 경로도 수정

---

### 3. CORS 설정 문제
**상태**: ✅ 해결됨  
**해결일**: 2025-08-04  
**해결 방법**: CORS 설정 개선

**문제**: `Forbidden (Origin checking failed - http://localhost:3000 does not match any trusted origins.)`

**해결 내용**:
- CORS_ALLOWED_ORIGINS에 localhost:8000 추가
- CORS 설정 주석 개선
- 미들웨어 순서 확인 (올바른 순서로 설정됨)

---

### 4. Dashboard API 경로 문제
**상태**: ✅ 해결됨  
**해결일**: 2025-08-05  
**해결 방법**: URL 패턴 직접 정의

**문제**: 
- 프론트엔드에서 `/api/dashboard/stats/`와 `/api/dashboard/activities/` 요청
- 기존 URL 설정에서는 `/api/companies/dashboard/stats/`로 매핑됨
- 404 오류 발생

**해결 내용**:
- companies 앱의 URL에서 dashboard 경로 제거
- 메인 URL 설정에서 dashboard 경로 직접 정의
- `/api/dashboard/stats/`와 `/api/dashboard/activities/` 경로 정상 작동 확인

---

### 5. CSRF 인증 문제
**상태**: ✅ 해결됨  
**해결일**: 2025-08-05  
**해결 방법**: CSRF 설정 개선 및 로그인 뷰 수정

**문제**: 
- 로그인 시 `CSRF Failed: Origin checking failed` 오류 발생
- `CSRF Failed: CSRF token missing` 오류 발생
- 서버 크래시: `ViewDoesNotExist: 'None' is not a callable or a dot-notation path`

**해결 내용**:
- `CSRF_TRUSTED_ORIGINS` 설정 추가
- `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_HTTPONLY`, `CSRF_USE_SESSIONS`를 `False`로 설정
- `LoginView`에 `@csrf_exempt` 데코레이터 추가
- 문제가 되는 `CSRF_FAILURE_VIEW = None` 및 `CSRF_COOKIE_SAMESITE = None` 설정 제거
- `bon_admin` 계정으로 로그인 테스트 성공 확인

---

## 📋 추가 개선 사항

### 향후 고려사항:

1. **프로덕션 환경 설정**
   - CORS_ALLOW_ALL_ORIGINS를 False로 설정
   - 보안 강화

2. **API 문서화**
   - Swagger/OpenAPI 문서 추가

3. **테스트 코드 작성**
   - 단위 테스트 및 통합 테스트 추가

---

**문서 작성일**: 2025-08-04  
**마지막 업데이트**: 2025-08-05 (모든 주요 문제 해결됨, CSRF 문제 포함) 
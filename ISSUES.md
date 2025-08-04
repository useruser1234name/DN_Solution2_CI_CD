# 현재 발생 중인 문제들

## 🔴 긴급 문제

### 1. 데이터베이스 스키마 불일치 오류
**오류 메시지**: `table policies_policy has no column named form_type`

**상태**: ❌ 해결되지 않음  
**영향도**: 정책 생성 기능 완전 불가

**문제**: 정책 생성 시 `form_type` 컬럼이 없다는 데이터베이스 오류 발생

---

## 🟡 중간 문제

### 2. API 경로 중복 문제
**상태**: ⚠️ 부분적 해결  
**영향도**: API 호출 시 404 오류

**문제**: 
- 프론트엔드에서 `get('api/list/')` 호출
- `api.js`에서 `API_BASE_URL = 'http://localhost:8001/api'` 설정
- Django URL 설정: `path('api/', include('policies.urls'))`
- `policies/urls.py`에서: `path('api/list/', views.policy_api_list)`
- 결과적으로 `/api/api/list/`로 요청이 가게 됨

---

### 3. CORS 설정 문제
**상태**: ⚠️ 부분적 해결  
**영향도**: 브라우저에서 API 호출 시 403 오류

**문제**: `Forbidden (Origin checking failed - http://localhost:3000 does not match any trusted origins.)`

---

## 📋 해결 계획

### 내일 해결할 작업들:

1. **데이터베이스 스키마 문제 해결** (최우선)
   - SQLite 데이터베이스 파일 직접 확인
   - 필요시 데이터베이스 재생성

2. **API 경로 구조 정리**
   - Django URL 구조 재설계

3. **CORS 설정 완전 해결**
   - 미들웨어 순서 확인

---

**문서 작성일**: 2025-08-04  
**마지막 업데이트**: 2025-08-04 
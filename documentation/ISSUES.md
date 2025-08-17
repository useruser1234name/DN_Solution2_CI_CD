# DN Solution 2 - 이슈 및 문제해결 기록

## 🚨 해결된 주요 이슈들

### 1. 프론트엔드-백엔드 연결 문제 (2025-08-16)

#### 🔍 문제 상황
- 로그인은 성공하지만 각 페이지에서 API 호출 실패
- 대시보드, 정책, 주문, 정산 페이지에서 404 오류 발생
- 새로고침 시 로그아웃되는 문제

#### 📋 발견된 세부 문제들

**1. API 엔드포인트 경로 문제**
```
❌ 문제: 프론트엔드에서 '/api/' 접두사 누락
- /dashboard/stats/ → 404 오류
- /companies/ → 404 오류
- /policies/ → 404 오류

✅ 해결: 모든 API 호출에 '/api/' 접두사 추가
- /api/dashboard/stats/ ✓
- /api/companies/ ✓
- /api/policies/ ✓
```

**2. 로그인 엔드포인트 불일치**
```
❌ 문제: /api/auth/token/ 엔드포인트 404 오류
✅ 해결: /api/auth/login/ 엔드포인트로 변경
```

**3. 새로고침 시 로그아웃 문제**
```
❌ 문제: /api/auth/user/ 엔드포인트 존재하지 않음
✅ 해결: /api/auth/token-info/ 엔드포인트 사용
- 백엔드 TokenInfoView에 사용자 정보 추가
- 프론트엔드 AuthContext에서 토큰 정보 파싱 로직 개선
```

**4. API 응답 데이터 구조 문제**
```
❌ 문제: policies.map is not a function
❌ 문제: orders.filter is not a function
❌ 문제: settlements.filter is not a function

✅ 해결: 페이지네이션된 응답 구조 대응
- response.data.results || response.data || []
```

**5. 정책 생성 시 validation 오류**
```
❌ 문제: "SKT"이 유효하지 않은 선택(choice)입니다.
✅ 해결: 프론트엔드에서 'SKT' → 'skt' 소문자로 변경
```

#### 🔧 수정된 파일들 (총 20+ 파일)

**프론트엔드 API 경로 수정:**
- `frontend/src/services/api.js` - getUserInfo 엔드포인트 수정
- `frontend/src/pages/DashboardPage.js` - 대시보드 API 경로
- `frontend/src/pages/PolicyListPage.js` - 정책 API 경로
- `frontend/src/pages/OrderListPage.js` - 주문 API 경로
- `frontend/src/pages/SettlementListPage.js` - 정산 API 경로
- `frontend/src/pages/UserCreatePage.js` - 사용자 API 경로
- `frontend/src/pages/CompanyListPage.js` - 회사 API 경로
- `frontend/src/pages/PolicyCreatePage.js` - 정책 생성 carrier 값 수정
- `frontend/src/components/PolicyExposureModal.js` - 정책 노출 API 경로
- `frontend/src/pages/AdminSignupPage.js` - 관리자 가입 API 경로
- `frontend/src/pages/StaffSignupPage.js` - 직원 가입 API 경로
- `frontend/src/components/AgencyRebateModal.js` - 리베이트 API 경로
- `frontend/src/contexts/AuthContext.js` - 인증 초기화 로직 개선

**백엔드 수정:**
- `dn_solution/auth_views.py` - TokenInfoView에 사용자 정보 추가

#### 📊 결과
- ✅ 로그인 정상 작동
- ✅ 대시보드 API 호출 성공  
- ✅ 모든 페이지 API 연결 정상
- ✅ 새로고침 시 로그인 상태 유지
- ✅ 정책 생성 오류 해결
- ✅ 권한별 UI 제어 작동

---

### 2. 업체 계층 구조 및 권한 시스템 문제 (2025-08-17)

#### 🔍 문제 상황
- 업체 목록 데이터 구조가 예상과 다름
- 본사 사용자가 타 업체 정보까지 볼 수 있는 권한 오류
- 정책 노출 기능이 실제로 작동하지 않음
- 협력사 리베이트 시스템 인증 오류

#### 📋 발견된 세부 문제들

**1. 프론트엔드 API 응답 파싱 문제**
```
❌ 문제: API 응답 이중 래핑으로 데이터 파싱 실패
- 백엔드: {success: true, data: {results: [...]}}
- 프론트엔드: response.results 직접 접근 시도

✅ 해결: 이중 래핑 구조 대응 로직 추가
- response.success && response.data 확인 후 데이터 추출
```

**2. 권한 시스템 보안 취약점**
```
❌ 문제: 본사 사용자가 모든 업체 정보 접근 가능
- get_accessible_company_ids에서 Company.objects.all() 반환

✅ 해결: 계층별 접근 권한 엄격 제한
- 본사: 자신 + 직접/간접 하위 업체만
- 협력사: 자신 + 직접 하위 판매점만
- 판매점: 자신만
```

**3. 정책 노출 기능 미구현**
```
❌ 문제: 정책 노출 모달에서 모의 처리만 수행
- handleSave에서 setTimeout으로 가짜 저장

✅ 해결: 실제 API 연동 및 하위 업체 자동 노출
- 실제 POST 요청으로 정책 노출 저장
- 협력사 선택 시 하위 판매점 자동 노출
```

**4. 업체 계층 구조 시각화 부족**
```
❌ 문제: 계층 구조가 명확하지 않음
- CompanyTreeView 컴포넌트의 한계

✅ 해결: 커스텀 계층 렌더링 구현
- buildHierarchy: 평면 데이터를 트리 구조로 변환
- 레벨별 색상 구분, 들여쓰기, 연결선 추가
```

#### 🔧 수정된 파일들 (총 10개 파일)

**프론트엔드 수정:**
- `frontend/src/components/PolicyExposureModal.js` - 정책 노출 API 연동
- `frontend/src/pages/CompanyListPage.js` - 계층 구조 렌더링
- `frontend/src/pages/CompanyListPage.css` - 계층 구조 스타일링
- `frontend/src/pages/PolicyDetailPage.js` - 노출 업체 표시, 권한별 UI
- `frontend/src/pages/PolicyDetailPage.css` - 노출 업체 스타일링

**백엔드 수정:**
- `companies/utils.py` - 권한 시스템 수정 (핵심)
- `policies/viewsets_exposure.py` - 하위 업체 자동 노출
- `policies/views.py` - 리베이트 인증 오류 수정

#### 📊 결과
- ✅ 권한 시스템 보안 강화 (타 업체 정보 노출 차단)
- ✅ 업체 계층 구조 시각화 개선
- ✅ 정책 노출 기능 정상 작동
- ✅ 협력사 리베이트 시스템 인증 해결
- ✅ 사용자별 적절한 UI 표시

---

### 3. 이전 알려진 이슈들

#### Django Admin 접근 문제
- **문제**: Django admin 페이지 접근 시 500 오류
- **해결**: 슈퍼유저 생성 및 admin 설정 수정

#### JWT 토큰 만료 문제
- **문제**: 토큰 만료 시 자동 갱신 실패
- **해결**: Refresh token 로직 개선

#### 캐시 성능 문제
- **문제**: Redis 대신 Local Memory Cache 사용으로 성능 저하
- **해결**: 캐시 설정 최적화

---

## 🔄 지속적인 모니터링 필요 사항

### 1. 성능 모니터링
- API 응답 시간 < 2초 유지
- 메모리 사용량 모니터링
- 데이터베이스 쿼리 최적화

### 2. 보안 검토
- JWT 토큰 보안 설정
- API 접근 로그 모니터링
- 사용자 권한 검증

### 3. 확장성 고려사항
- 사용자 증가 시 성능 대응
- 데이터베이스 확장성
- 캐시 전략 개선

---

## 📝 이슈 보고 가이드

### 새로운 이슈 발견 시
1. **문제 재현 단계** 명확히 기록
2. **오류 메시지** 전체 복사
3. **브라우저/환경 정보** 포함
4. **예상 동작**과 **실제 동작** 비교
5. **스크린샷** 첨부 (UI 문제의 경우)

### 이슈 우선순위
- **Critical**: 시스템 전체 다운, 보안 문제
- **High**: 주요 기능 동작 불가
- **Medium**: 특정 기능 오류
- **Low**: UI 개선, 편의성 문제

---

## 🛠️ 디버깅 도구 및 팁

### 로그 확인 위치
- **Django 로그**: `logs/django.log`
- **API 로그**: `logs/api.log`  
- **브라우저 개발자 도구**: Network, Console 탭

### 자주 사용하는 디버깅 명령어
```bash
# Django 로그 실시간 확인
tail -f logs/django.log

# 데이터베이스 마이그레이션 확인
python manage.py showmigrations

# 테스트 실행
python manage.py test
npx playwright test
```

### 환경별 설정 확인
- **개발환경**: `dn_solution/settings/development.py`
- **프로덕션**: `dn_solution/settings/production.py`
- **테스트**: `dn_solution/settings/test.py`
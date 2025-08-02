# 프론트엔드 설계 (Frontend Design)

이 문서는 `DN_solution` 프로젝트의 프론트엔드 시스템에 대한 상세 설계를 다룹니다. React 기반의 SPA(Single Page Application) 아키텍처, 컴포넌트 구조, 상태 관리, 그리고 백엔드와의 통신 방식을 중심으로 설명합니다.

## 1. 아키텍처 및 기술 스택

*   **프레임워크:** React 18.x
*   **라우팅:** React Router v6
*   **상태 관리:** React Context API
*   **HTTP 클라이언트:** Fetch API (기본) 또는 Axios
*   **스타일링:** CSS Modules 또는 Styled Components
*   **빌드 도구:** Create React App (CRA)
*   **개발 서버:** React Development Server (포트 3000)

## 2. 프로젝트 구조

```
frontend/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├── src/
│   ├── components/          # 재사용 가능한 UI 컴포넌트
│   │   ├── Sidebar.js
│   │   └── Sidebar.css
│   ├── contexts/            # React Context (상태 관리)
│   │   └── AuthContext.js
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── LoginPage.js
│   │   ├── SignUpPage.js
│   │   ├── CompanyManagementPage.js
│   │   ├── UserApprovalPage.js
│   │   ├── DebugPage.js
│   │   ├── MainLayout.js
│   │   └── MainLayout.css
│   ├── services/            # API 통신 로직
│   │   ├── api.js
│   │   ├── authService.js
│   │   ├── companyService.js
│   │   └── userService.js
│   ├── hooks/               # 커스텀 React Hooks
│   ├── utils/               # 유틸리티 함수
│   ├── App.js               # 메인 App 컴포넌트
│   ├── App.css
│   ├── index.js             # 애플리케이션 진입점
│   └── index.css
├── package.json
└── README.md
```

## 3. 핵심 컴포넌트 설계

### 3.1. 인증 시스템 (`AuthContext.js`)

*   **목적:** 사용자 인증 상태를 전역적으로 관리하고, 로그인/로그아웃 기능을 제공합니다.
*   **주요 기능:**
    *   사용자 정보 저장 및 관리
    *   로그인/로그아웃 처리
    *   인증 상태 확인
    *   자동 로그인 체크

```javascript
// AuthContext.js 예시
const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const login = async (username, password) => {
        // 로그인 로직
    };

    const logout = async () => {
        // 로그아웃 로직
    };

    const checkAuth = async () => {
        // 인증 상태 확인
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};
```

### 3.2. 라우팅 시스템 (`App.js`)

*   **목적:** 페이지 간 네비게이션을 관리하고, 인증 상태에 따른 접근 제어를 수행합니다.
*   **주요 기능:**
    *   공개 라우트 (로그인, 회원가입)
    *   보호된 라우트 (인증 필요)
    *   인증 상태에 따른 리다이렉션

```javascript
// App.js 라우팅 예시
<Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/signup" element={<SignUpPage />} />
    <Route path="/debug" element={<DebugPage />} />
    <Route path="/" element={
        <ProtectedRoute>
            <MainLayout />
        </ProtectedRoute>
    } />
    <Route path="/company-management" element={
        <ProtectedRoute>
            <MainLayout>
                <CompanyManagementPage />
            </MainLayout>
        </ProtectedRoute>
    } />
    <Route path="/user-approval" element={
        <ProtectedRoute>
            <MainLayout>
                <UserApprovalPage />
            </MainLayout>
        </ProtectedRoute>
    } />
</Routes>
```

### 3.3. API 통신 (`services/`)

*   **목적:** 백엔드 API와의 통신을 담당하고, 에러 처리와 응답 변환을 수행합니다.
*   **주요 기능:**
    *   HTTP 요청 처리
    *   에러 핸들링
    *   응답 데이터 변환
    *   인증 토큰 관리

```javascript
// api.js 예시
const apiRequest = async (url, options = {}) => {
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'include',
    };

    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            let errorMessage = `HTTP error! status: ${response.status}`;
            try {
                const errorData = await response.json();
                if (errorData.error) {
                    errorMessage = errorData.error;
                } else if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (e) {
                // JSON 파싱 실패 시 기본 메시지 사용
            }
            const error = new Error(errorMessage);
            error.status = response.status;
            throw error;
        }

        const data = await response.json();
        return data;
    } catch (error) {
        throw error;
    }
};
```

## 4. 계층별 승인 시스템 UI

### 4.1. 회원가입 페이지 (`SignUpPage.js`)

*   **목적:** 계층별 회원가입을 위한 직관적인 UI를 제공합니다.
*   **주요 기능:**
    *   업체 유형 선택 (본사/협력사/판매점)
    *   상위 업체 코드 입력 (동적 필드)
    *   실시간 유효성 검증
    *   사용자 친화적인 에러 메시지

```javascript
// SignUpPage.js 핵심 로직
const getParentCompanyLabel = () => {
    switch (formData.company_type) {
        case 'headquarters':
            return '본사는 상위 업체가 없습니다';
        case 'agency':
            return '본사 코드';
        case 'retail':
            return '협력사 코드';
        default:
            return '상위 업체 코드';
    }
};

const isParentCodeRequired = () => {
    return formData.company_type !== 'headquarters';
};
```

### 4.2. 사용자 승인 페이지 (`UserApprovalPage.js`)

*   **목적:** 승인 대기 중인 사용자 목록을 표시하고 승인/거절 기능을 제공합니다.
*   **주요 기능:**
    *   승인 대기 사용자 목록 조회
    *   승인/거절 버튼
    *   사용자 상세 정보 표시
    *   실시간 상태 업데이트

### 4.3. 디버그 페이지 (`DebugPage.js`)

*   **목적:** API 연결 상태를 테스트하고 문제 진단을 돕습니다.
*   **주요 기능:**
    *   API 엔드포인트 테스트
    *   응답/에러 로그 표시
    *   연결 상태 확인

## 5. 상태 관리 전략

### 5.1. React Context API 활용

*   **인증 상태:** `AuthContext`를 통해 전역적으로 관리
*   **사용자 정보:** 로그인한 사용자의 정보를 전역 상태로 관리
*   **로딩 상태:** API 요청 중 로딩 상태를 관리

### 5.2. 로컬 상태 관리

*   **폼 데이터:** 각 페이지의 폼 입력값을 로컬 상태로 관리
*   **UI 상태:** 모달, 드롭다운 등의 UI 상태를 로컬 상태로 관리
*   **에러 상태:** 각 컴포넌트의 에러 메시지를 로컬 상태로 관리

## 6. UI/UX 설계 원칙

### 6.1. 반응형 디자인

*   **모바일 우선:** 모바일 디바이스에서 최적화된 경험 제공
*   **데스크톱 호환:** 데스크톱에서도 최적화된 레이아웃 제공
*   **접근성:** 키보드 네비게이션, 스크린 리더 지원

### 6.2. 사용자 경험 (UX)

*   **직관적 네비게이션:** 사용자가 쉽게 원하는 기능을 찾을 수 있도록 설계
*   **피드백 제공:** 모든 사용자 액션에 대한 적절한 피드백 제공
*   **에러 처리:** 사용자 친화적인 에러 메시지와 복구 방법 제시

### 6.3. 시각적 디자인

*   **일관된 디자인 시스템:** 색상, 타이포그래피, 간격의 일관성 유지
*   **계층적 정보 구조:** 중요도에 따른 정보의 시각적 계층화
*   **로딩 상태:** API 요청 중 적절한 로딩 인디케이터 제공

## 7. 보안 고려사항

### 7.1. 인증 및 권한

*   **세션 관리:** 백엔드 세션과 연동하여 인증 상태 관리
*   **라우트 보호:** 인증되지 않은 사용자의 보호된 페이지 접근 차단
*   **권한 기반 UI:** 사용자 권한에 따른 UI 요소 표시/숨김

### 7.2. 데이터 보안

*   **민감 정보 보호:** 비밀번호 등 민감한 정보의 안전한 처리
*   **입력 검증:** 클라이언트 측 입력 검증 (서버 검증과 병행)
*   **XSS 방지:** 사용자 입력의 안전한 렌더링

## 8. 성능 최적화

### 8.1. 코드 분할 (Code Splitting)

*   **라우트 기반 분할:** 각 페이지를 별도 청크로 분할하여 초기 로딩 시간 단축
*   **컴포넌트 지연 로딩:** 필요 시에만 컴포넌트 로딩

### 8.2. 캐싱 전략

*   **API 응답 캐싱:** 자주 조회되는 데이터의 캐싱
*   **정적 자원 캐싱:** CSS, JS 파일의 브라우저 캐싱 활용

### 8.3. 번들 최적화

*   **트리 쉐이킹:** 사용하지 않는 코드 제거
*   **압축:** JavaScript, CSS 파일 압축
*   **이미지 최적화:** WebP 등 최신 이미지 포맷 활용

## 9. 테스트 전략

### 9.1. 단위 테스트

*   **컴포넌트 테스트:** 각 React 컴포넌트의 독립적 테스트
*   **유틸리티 함수 테스트:** 순수 함수들의 테스트
*   **훅 테스트:** 커스텀 React 훅의 테스트

### 9.2. 통합 테스트

*   **API 통신 테스트:** 백엔드와의 통신 테스트
*   **사용자 플로우 테스트:** 전체 사용자 여정 테스트
*   **인증 플로우 테스트:** 로그인/로그아웃 과정 테스트

### 9.3. E2E 테스트

*   **실제 브라우저 테스트:** 실제 사용자 시나리오 테스트
*   **크로스 브라우저 테스트:** 다양한 브라우저에서의 호환성 테스트

## 10. 배포 및 운영

### 10.1. 빌드 프로세스

*   **개발 빌드:** 개발 환경을 위한 최적화된 빌드
*   **프로덕션 빌드:** 운영 환경을 위한 최적화된 빌드
*   **환경 변수:** 개발/운영 환경별 설정 분리

### 10.2. 배포 전략

*   **정적 파일 호스팅:** Nginx, Apache 등을 통한 정적 파일 서빙
*   **CDN 활용:** 글로벌 사용자를 위한 CDN 활용
*   **무중단 배포:** Blue-Green 배포 등 무중단 배포 전략

이 문서는 `DN_solution` 프론트엔드 시스템의 설계와 구현 방식을 이해하는 데 필요한 모든 정보를 제공합니다.

'''
# 프론트엔드 개발 문서 (Frontend Development)

이 문서는 `DN_solution` 프로젝트의 프론트엔드 애플리케이션 개발에 대한 상세 내용을 다룹니다. 프로젝트 설정, 아키텍처, 주요 컴포넌트 및 실행 방법에 대해 설명합니다.

## 1. 프로젝트 설정 및 실행

### 1.1. 위치

프론트엔드 프로젝트는 `DN_solution` 루트 디렉토리의 `frontend` 폴더에 위치합니다.

### 1.2. 기술 스택

- **프레임워크:** React
- **라우팅:** `react-router-dom`
- **API 통신:** `axios`
- **스타일링:** CSS (모바일 반응형 포함)

### 1.3. 실행 방법

1.  `frontend` 디렉토리로 이동합니다.
    ```bash
    cd C:\Users\kci01\DN_solution\frontend
    ```
2.  필요한 패키지를 설치합니다. (이미 `npm install`을 실행했다면 생략 가능)
    ```bash
    npm install
    ```
3.  개발 서버를 시작합니다.
    ```bash
    npm start
    ```
    이제 웹 브라우저에서 `http://localhost:3000`으로 접속하여 애플리케이션을 확인할 수 있습니다.

## 2. 아키텍처 및 구조

프로젝트는 기능별로 코드를 분리하여 유지보수성을 높이는 모듈식 구조를 따릅니다.

```
frontend/
├── public/               # 정적 파일
├── src/
│   ├── components/         # 재사용 가능한 UI 컴포넌트 (Sidebar 등)
│   ├── pages/              # 페이지 단위 컴포넌트 (LoginPage, MainLayout 등)
│   ├── contexts/           # 전역 상태 관리 (인증 등)
│   ├── services/           # API 연동 로직
│   ├── hooks/              # 커스텀 훅
│   ├── App.js              # 메인 라우터
│   └── index.css           # 전역 스타일
└── package.json
```

- **`pages`**: 각 URL 경로에 해당하는 메인 페이지 컴포넌트들이 위치합니다.
- **`components`**: 여러 페이지에서 공통으로 사용되는 작은 UI 조각들(버튼, 사이드바 등)이 위치합니다.
- **`services`**: 백엔드 API와의 통신을 담당하는 함수들이 위치합니다.
- **`contexts`**: 사용자 인증 정보와 같이 애플리케이션 전반에서 공유되어야 할 상태를 관리합니다.

## 3. 주요 기능 및 컴포넌트

### 3.1. 인증 (로그인/회원가입)

- **`LoginPage.js`**: 사용자 로그인을 위한 UI와 로직을 포함합니다.
- **`SignUpPage.js`**: 신규 사용자 등록을 위한 UI와 로직을 포함합니다.
- **`Form.css`**: 로그인과 회원가입 폼의 공통 스타일을 정의합니다.

### 3.2. 메인 레이아웃

- **`MainLayout.js`**: 로그인 후 표시되는 모든 페이지의 공통적인 구조(사이드바, 상단 바)를 정의합니다.
- **`Sidebar.js`**: 좌측 내비게이션 메뉴를 담당합니다. 메뉴는 요청사항에 따라 계층 구조로 구현되었으며, 반응형으로 동작합니다.
- **`CompanyManagementPage.js`**: 로그인 후 처음으로 보여지는 기본 페이지입니다.

### 3.3. 라우팅

- **`App.js`**: `react-router-dom`을 사용하여 전체 페이지 라우팅을 관리합니다. 현재는 임시로 `isAuthenticated` 값을 `true`로 설정하여 로그인된 상태를 가정하고 있으나, 추후 `AuthContext`와 연동하여 실제 인증 상태에 따라 동적으로 라우팅을 제어해야 합니다.

## 4. 백엔드 테이블 구조 제안

프론트엔드의 메뉴 구조를 지원하기 위해 다음과 같은 백엔드 모델 확장을 제안합니다.

- **`orders` 앱 확장**: `Order` 모델의 `status` 필드를 세분화하여 주문의 다양한 상태를 관리합니다.
  - `pending`, `processing`, `completed`, `cancellation_requested`, `cancelled`, `customer_request`
- **`settlements` 앱 (신규)**: 정산 관리를 위한 `Settlement` 모델을 추가합니다.
- **`devices` 앱 (신규)**: 기기 관리를 위한 `Device` 및 `DeviceLog` 모델을 추가합니다.

이 제안은 `docs/`에 있는 기존 백엔드 설계를 존중하고 확장성을 고려하여 설계되었습니다.
''
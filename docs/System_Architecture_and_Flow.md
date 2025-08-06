# 시스템 아키텍처 및 흐름 (System Architecture and Flow)

이 문서는 `DN_solution` 프로젝트의 전체적인 시스템 아키텍처와 주요 컴포넌트 간의 데이터 및 로직 흐름을 상세하게 설명합니다. 최상위 설계부터 각 앱의 역할까지 포괄하여 시스템의 전반적인 동작 방식을 이해할 수 있도록 돕습니다.

## 1. 전체 시스템 아키텍처

`DN_solution`은 Django 기반의 백엔드 RESTful API 서버와 Django 템플릿 기반의 프론트엔드 웹 인터페이스로 구성된 클라이언트-서버 아키텍처를 따릅니다.

```
+-----------------------+     +------------------------+
|   Frontend Web UI     |     |   Future SPA Frontend  |
| (Django Templates)    |     | (React/Vue/Angular)    |
+-----------+-----------+     +-----------+------------+
            |                               |
            | HTTP/HTTPS (RESTful API Calls)|
            |                               |
+-----------v-----------+     +-----------v------------+
|     Backend Server    |     |     Backend Server     |
|     (Django/DRF)      |     |     (Django/DRF)       |
| +-------------------+ |     | +-------------------+ |
| |  Authentication   | |     | |  Authentication   | |
| |  & Authorization  | |     | |  & Authorization  | |
| +-------------------+ |     | +-------------------+ |
| |  API Endpoints    | |     | |  API Endpoints    | |
| |  (companies, orders, policies) | |  (companies, orders, policies) |
| +-------------------+ |     | +-------------------+ |
| |  Business Logic   | |     | |  Business Logic   | |
| +-------------------+ |     | +-------------------+ |
| |  ORM (Django)     | |     | |  ORM (Django)     | |
| +-------------------+ |     | +-------------------+ |
+-----------+-----------+     +-----------+------------+
            |                               |
            | SQL Queries                   | SQL Queries
            |                               |
+-----------v-----------+     +-----------v------------+
|      Database         |     |      Database         |
| (PostgreSQL/MySQL/SQLite) | | (PostgreSQL/MySQL/SQLite) |
+-----------------------+     +------------------------+
```

*   **프론트엔드 웹 UI:** Django 템플릿 기반의 사용자 인터페이스를 제공하고, 백엔드 API를 호출하여 데이터를 주고받습니다.
*   **향후 SPA 프론트엔드:** React, Vue.js, Angular 등 SPA 프레임워크를 사용한 클라이언트 사이드 애플리케이션 (계획 중).
*   **백엔드 서버 (Django/DRF):**
    *   사용자 인증 및 권한 부여를 처리합니다.
    *   RESTful API 엔드포인트를 통해 클라이언트의 요청을 받습니다.
    *   핵심 비즈니스 로직을 수행합니다.
    *   Django ORM을 통해 데이터베이스와 상호작용합니다.
*   **데이터베이스:** 모든 애플리케이션 데이터가 저장되는 영구 저장소입니다.

## 2. 프로젝트 구조 상세

`DN_solution` 프로젝트는 모듈화된 개발을 지향하며, 각 앱이 특정 비즈니스 도메인을 담당하도록 설계되었습니다.

```
DN_solution/
├── .git/                   # Git 버전 관리
├── companies/              # Django 앱: 업체 및 사용자 관리
│   ├── __init__.py
│   ├── admin.py            # Django 관리자 페이지 설정
│   ├── apps.py             # Django 앱 설정
│   ├── models.py           # Company, CompanyUser, CompanyMessage 모델 정의
│   ├── serializers.py      # DRF Serializer (직렬화/역직렬화)
│   ├── tests.py            # 단위 및 통합 테스트
│   ├── urls.py             # 앱별 URL 라우팅
│   ├── views.py            # DRF ViewSet (API 뷰 로직)
│   └── templates/          # HTML 템플릿 (예: model_test.html)
├── dn_solution/               # Django 프로젝트 메인 설정
│   ├── __init__.py
│   ├── asgi.py             # ASGI 설정
│   ├── settings.py         # 프로젝트 설정 (DB, 앱 등록, 미들웨어 등)
│   ├── urls.py             # 프로젝트 전체 URL 라우팅
│   └── wsgi.py             # WSGI 설정
├── logs/                   # 애플리케이션 로그 파일
├── orders/                 # Django 앱: 주문 관리
│   ├── models.py           # Order, OrderMemo, Invoice, OrderRequest 모델
│   ├── serializers.py      # 주문 관련 시리얼라이저
│   ├── urls.py             # 주문 관련 URL 라우팅
│   └── views.py            # 주문 관련 뷰
├── policies/               # Django 앱: 스마트기기 판매 정책 관리
│   ├── models.py           # Policy, PolicyNotice, PolicyAssignment 모델
│   ├── serializers.py      # 정책 관련 시리얼라이저
│   ├── urls.py             # 정책 관련 URL 라우팅
│   ├── views.py            # 정책 관련 뷰 (CRUD, API 엔드포인트)
│   ├── admin.py            # 정책 관리 Admin 인터페이스
│   └── templates/          # 정책 관리 HTML 템플릿
│       └── policies/
│           ├── policy_list.html      # 정책 목록 페이지
│           └── policy_form.html      # 정책 생성/수정 폼
├── venv/                   # Python 가상 환경
├── Docs/                   # 프로젝트 문서 (현재 이 디렉토리)
│   ├── Legacy_Docs/        # 이전 문서 보관
│   ├── Company_Creation_Policy.md
│   ├── UI_Access_Control_Strategy.md
│   ├── Development_Practices.md
│   ├── System_Architecture_and_Flow.md (현재 문서)
│   ├── Backend_Design.md
│   ├── Frontend_Design.md
│   ├── Extensibility_and_Future_Directions.md
│   └── Project_Summary.md
├── .env                    # 환경 변수
├── .gitignore              # Git 무시 파일
├── db.sqlite3              # 개발 DB
├── manage.py               # Django 관리 명령어
└── requirements.txt        # Python 의존성
```

## 3. 주요 앱 간의 데이터 및 로직 흐름

### 3.1. `companies` 앱 (업체 및 사용자 관리)

*   **역할:** 시스템의 핵심 엔티티인 `Company`와 `CompanyUser`를 관리합니다. 다른 앱들이 `Company` 및 `CompanyUser` 정보를 참조하고 활용합니다.
*   **주요 흐름:**
    1.  **프론트엔드 요청:** 사용자(예: 본사 관리자)가 새로운 협력사를 생성하기 위해 `POST /api/companies/companies/` 엔드포인트로 요청을 보냅니다.
    2.  **`CompanyViewSet` (`views.py`):** 요청을 받아 `CompanySerializer`를 통해 데이터를 역직렬화하고 유효성을 검증합니다.
    3.  **`Company` 모델 (`models.py`):**
        *   `clean()` 메서드가 호출되어 업체 유형(`type`)과 상위 업체(`parent_company`) 간의 계층적 규칙(예: 협력사는 본사 하위에만 가능)을 검증합니다.
        *   `save()` 메서드가 호출되어 데이터베이스에 저장되고, 이 과정이 로깅됩니다.
    4.  **데이터베이스:** 새로운 `Company` 레코드가 생성됩니다.
    5.  **응답:** `CompanySerializer`를 통해 생성된 `Company` 객체가 직렬화되어 프론트엔드로 `201 Created` 응답과 함께 반환됩니다.

### 3.2. `orders` 앱 (주문 관리)

*   **역할:** 고객 주문 정보를 관리하며, 특정 `Company` (주로 판매점)에 귀속됩니다.
*   **`companies` 앱과의 연동:**
    *   `Order` 모델은 `company` 필드를 통해 `Company` 모델을 외래 키로 참조합니다.
    *   주문 생성 시, 해당 주문이 어느 판매점에서 발생했는지 `Company` 정보를 연결합니다.
    *   주문 관련 API(예: `OrderViewSet`)는 `Company` 모델의 정보를 활용하여 특정 업체의 주문만 조회하거나 관리할 수 있도록 필터링 로직을 가질 수 있습니다.
*   **`policies` 앱과의 연동:**
    *   `Order` 모델은 `policy` 필드를 통해 `Policy` 모델을 외래 키로 참조합니다.
    *   주문 생성 시 적용된 정책 정보를 저장하고, 리베이트 계산에 활용합니다.
    *   `Order.calculate_rebate()` 메서드에서 정책의 리베이트 정보를 사용하여 계산을 수행합니다.

### 3.3. `policies` 앱 (스마트기기 판매 정책 관리)

*   **역할:** 스마트기기 판매 정책을 정의하고, 이를 특정 `Company`에 배정하며, 리베이트 계산 등의 비즈니스 로직을 처리합니다.
*   **`companies` 앱과의 연동:**
    *   `PolicyAssignment` 모델은 `company` 필드를 통해 `Company` 모델을 외래 키로 참조합니다.
    *   특정 정책이 어떤 업체에 적용되는지 `Company` 정보를 연결합니다.
    *   정책 관련 API(예: `PolicyViewSet`)는 `Company` 모델의 정보를 활용하여 특정 업체의 정책만 조회하거나 관리할 수 있도록 필터링 로직을 가질 수 있습니다.
*   **주요 데이터 흐름:**
    1.  **정책 생성:** 관리자가 새로운 정책을 생성합니다.
        *   기본 정보 (제목, 설명, 신청서 타입) 입력
        *   필터링 설정 (통신사, 가입기간) 선택
        *   리베이트 설정 (대리점/판매점 리베이트) 입력
        *   노출 설정 (프론트엔드/프리미엄 마켓 노출) 선택
    2.  **정책 배정:** 생성된 정책을 특정 업체에 배정합니다.
        *   `PolicyAssignment` 모델을 통해 정책과 업체 연결
        *   업체별 커스텀 리베이트 설정 가능
        *   하위 업체 노출 여부 설정
    3.  **정책 활용:** 주문 생성 시 정책 정보를 활용합니다.
        *   `Order` 모델에서 `policy` 필드를 통해 정책 참조
        *   `Order.calculate_rebate()`에서 정책의 리베이트 정보 사용
        *   업체 유형에 따라 대리점/판매점 리베이트 적용
    4.  **웹 노출:** 정책을 웹사이트에 노출합니다.
        *   `Policy.expose` 필드로 프론트엔드 노출 제어
        *   `Policy.premium_market_expose` 필드로 프리미엄 마켓 노출 제어
        *   `Policy.generate_html_content()`로 정책 상세페이지 HTML 자동 생성

## 4. JWT 기반 인증 및 권한 흐름

시스템은 JWT (JSON Web Token) 기반의 상태 비저장 인증을 사용하여 클라우드 환경에 최적화된 보안 체계를 제공합니다.

### 4.1. JWT 인증 흐름

1.  **사용자 로그인:** React 프론트엔드에서 사용자(Django User)가 `/api/companies/auth/jwt/login/` 엔드포인트로 로그인 요청을 보냅니다.
2.  **커스텀 JWT 인증 처리:** `CustomTokenObtainPairSerializer`가 다음 과정을 수행합니다:
    *   Django User 자격 증명(username, password) 검증
    *   연결된 `CompanyUser` 존재 여부 확인
    *   `CompanyUser.is_approved` 및 `status='approved'` 상태 검증
    *   소속 `Company.status` 활성화 상태 확인
    *   JWT 토큰에 업체 정보 (company_id, company_name, company_type, role 등) 포함
3.  **토큰 발급:** 검증이 완료되면 Access Token과 Refresh Token을 발급합니다.
4.  **프론트엔드 토큰 저장:** React 앱이 토큰을 `localStorage`에 저장하고 `AuthContext`로 전역 상태를 관리합니다.

### 4.2. API 요청 권한 흐름

1.  **API 요청:** 프론트엔드가 모든 API 요청에 `Authorization: Bearer <access_token>` 헤더를 포함하여 보냅니다.
2.  **JWT 인증 미들웨어:** `rest_framework_simplejwt.authentication.JWTAuthentication`이 토큰을 검증하고 사용자를 인증합니다.
3.  **계층적 권한 필터링:** `companies/utils.py`의 유틸리티 함수들이 사용자의 계층에 따른 접근 제어를 수행합니다:
    *   `get_accessible_company_ids()`: 사용자가 접근 가능한 업체 ID 목록 반환
    *   `get_visible_companies()`: 사용자가 볼 수 있는 업체 쿼리셋 반환
    *   `get_visible_users()`: 사용자가 볼 수 있는 사용자 쿼리셋 반환
4.  **ViewSet 레벨 권한 제어:**
    *   `CompanyViewSet.get_queryset()`: 계층적 업체 필터링
    *   `CompanyUserViewSet.get_queryset()`: 계층적 사용자 필터링
    *   Django Admin의 `get_queryset()`: 동일한 권한 로직 적용
5.  **응답:** 권한이 검증된 데이터만 JSON 형태로 반환됩니다.

### 4.3. 토큰 갱신 흐름

1.  **토큰 만료:** Access Token 만료 시 자동으로 Refresh Token을 사용하여 새로운 Access Token을 요청합니다.
2.  **자동 갱신:** `axios` 인터셉터가 401 오류를 감지하여 자동으로 토큰 갱신을 처리합니다.
3.  **로그아웃:** 토큰 무효화 또는 만료 시 자동으로 로그인 페이지로 리다이렉트됩니다.

## 5. 정책 관리 시스템 상세 흐름

### 5.1. 정책 생성 및 관리 흐름

1.  **정책 생성 요청:** 관리자가 정책 생성 페이지에 접근합니다.
2.  **폼 입력:** 정책의 기본 정보, 필터링 설정, 리베이트 설정, 노출 설정을 입력합니다.
3.  **실시간 중복 체크:** 정책 제목 입력 시 AJAX를 통해 중복 체크를 수행합니다.
4.  **유효성 검증:** 클라이언트 사이드와 서버 사이드에서 모두 유효성 검증을 수행합니다.
5.  **정책 저장:** 검증이 통과되면 정책을 데이터베이스에 저장합니다.
6.  **HTML 생성:** 정책 데이터를 기반으로 상세페이지 HTML을 자동 생성합니다.
7.  **응답:** 생성된 정책 정보와 함께 성공 메시지를 반환합니다.

### 5.2. 정책 목록 조회 및 필터링 흐름

1.  **목록 요청:** 사용자가 정책 목록 페이지에 접근합니다.
2.  **필터 적용:** 검색어, 신청서 타입, 통신사, 가입기간, 노출 상태 등의 필터를 적용합니다.
3.  **쿼리셋 필터링:** 백엔드에서 필터 조건에 따라 정책 쿼리셋을 필터링합니다.
4.  **페이지네이션:** 필터링된 결과에 대해 페이지네이션을 적용합니다.
5.  **템플릿 렌더링:** 필터링된 정책 목록을 템플릿에 렌더링합니다.
6.  **응답:** 정책 목록 페이지를 사용자에게 반환합니다.

### 5.3. 정책 상태 변경 흐름

1.  **토글 요청:** 사용자가 정책 목록에서 토글 스위치를 클릭합니다.
2.  **AJAX 요청:** JavaScript를 통해 AJAX 요청을 백엔드로 전송합니다.
3.  **권한 검증:** 백엔드에서 사용자의 권한을 검증합니다.
4.  **상태 변경:** 정책의 노출 상태를 변경합니다.
5.  **로깅:** 상태 변경을 로그에 기록합니다.
6.  **응답:** 변경된 상태와 함께 JSON 응답을 반환합니다.
7.  **UI 업데이트:** 프론트엔드에서 토글 스위치 상태를 업데이트하고 성공 메시지를 표시합니다.

## 6. 데이터 흐름 및 상호작용

*   **프론트엔드 ↔ 백엔드:** RESTful API를 통한 JSON 데이터 교환 및 Django 템플릿을 통한 HTML 렌더링.
*   **백엔드 ↔ 데이터베이스:** Django ORM을 통한 SQL 쿼리 실행.
*   **앱 간 데이터 참조:** `ForeignKey` 관계를 통해 `orders` 앱과 `policies` 앱이 `companies` 앱의 `Company` 모델을 참조합니다.
*   **실시간 업데이트:** AJAX를 통한 실시간 데이터 업데이트 및 상태 변경.

이 문서는 `DN_solution` 시스템의 복잡한 구조와 다양한 컴포넌트 간의 상호작용을 명확하게 이해하는 데 필요한 청사진을 제공합니다.

# 시스템 아키텍처 및 흐름 (System Architecture and Flow)

이 문서는 `DN_solution` 프로젝트의 전체적인 시스템 아키텍처와 주요 컴포넌트 간의 데이터 및 로직 흐름을 상세하게 설명합니다. 최상위 설계부터 각 앱의 역할까지 포괄하여 시스템의 전반적인 동작 방식을 이해할 수 있도록 돕습니다.

## 1. 전체 시스템 아키텍처

`DN_solution`은 Django 기반의 백엔드 RESTful API 서버와 이를 활용하는 프론트엔드 애플리케이션(별도 개발)으로 구성된 클라이언트-서버 아키텍처를 따릅니다.

```
+-----------------------+
|     Frontend App      |
| (React/Vue/Angular)   |
+-----------+-----------+
            | HTTP/HTTPS (RESTful API Calls)
            |
+-----------v-----------+
|     Backend Server    |
|     (Django/DRF)      |
| +-------------------+ |
| |  Authentication   | |
| |  & Authorization  | |
| +-------------------+ |
| |  API Endpoints    | |
| |  (companies, orders, policies) |
| +-------------------+ |
| |  Business Logic   | |
| +-------------------+ |
| |  ORM (Django)     | |
| +-------------------+ |
+-----------+-----------+
            | SQL Queries
            |
+-----------v-----------+
|      Database         |
| (PostgreSQL/MySQL/SQLite) |
+-----------------------+
```

*   **프론트엔드 앱:** 사용자 인터페이스를 제공하고, 백엔드 API를 호출하여 데이터를 주고받습니다.
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
├── hb_admin/               # Django 프로젝트 메인 설정
│   ├── __init__.py
│   ├── asgi.py             # ASGI 설정
│   ├── settings.py         # 프로젝트 설정 (DB, 앱 등록, 미들웨어 등)
│   ├── urls.py             # 프로젝트 전체 URL 라우팅
│   └── wsgi.py             # WSGI 설정
├── logs/                   # 애플리케이션 로그 파일
├── orders/                 # Django 앱: 주문 관리
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── policies/               # Django 앱: 정책 관리
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── venv/                   # Python 가상 환경
├── docs/                   # 프로젝트 문서 (현재 이 디렉토리)
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

### 3.3. `policies` 앱 (정책 관리)

*   **역할:** 다양한 정책을 정의하고, 이를 특정 `Company`에 배정합니다.
*   **`companies` 앱과의 연동:**
    *   `PolicyAssignment` 모델은 `company` 필드를 통해 `Company` 모델을 외래 키로 참조합니다.
    *   특정 정책이 어떤 업체에 적용되는지 `Company` 정보를 연결합니다.
    *   정책 관련 API(예: `PolicyViewSet`)는 `Company` 모델의 정보를 활용하여 특정 업체의 정책만 조회하거나 관리할 수 있도록 필터링 로직을 가질 수 있습니다.

## 4. 인증 및 권한 흐름

시스템의 모든 API 요청은 인증 및 권한 검증 과정을 거칩니다.

1.  **사용자 로그인:** 프론트엔드에서 사용자(예: `CompanyUser`)가 로그인 요청을 보냅니다.
2.  **인증 처리:** 백엔드에서 사용자 자격 증명(username, password)을 확인하고, 성공 시 인증 토큰(예: JWT)을 발급합니다.
3.  **API 요청:** 프론트엔드는 이후 모든 API 요청에 인증 토큰을 포함하여 보냅니다.
4.  **`IsAuthenticated` 권한 검증:** DRF의 `IsAuthenticated` 권한 클래스가 요청을 가로채어 토큰의 유효성을 검증하고 사용자를 인증합니다.
5.  **`CompanyViewSet.get_queryset()` 권한 필터링:**
    *   인증된 사용자의 `CompanyUser` 정보(소속 `Company`의 `type` 및 `id`)를 기반으로, 해당 사용자가 접근할 수 있는 `Company` 객체들로 쿼리셋을 필터링합니다.
    *   예: 협력사 사용자가 업체 목록을 요청하면, 자신의 협력사와 그 하위 판매점만 포함된 쿼리셋이 반환됩니다.
6.  **객체 레벨 권한:** `get_object()`와 같은 메서드에서 특정 객체에 대한 접근 권한을 추가적으로 확인할 수 있습니다.
7.  **응답:** 필터링된 데이터만 사용자에게 반환됩니다.

## 5. 데이터 흐름 및 상호작용

*   **프론트엔드 ↔ 백엔드:** RESTful API를 통한 JSON 데이터 교환.
*   **백엔드 ↔ 데이터베이스:** Django ORM을 통한 SQL 쿼리 실행.
*   **앱 간 데이터 참조:** `ForeignKey` 관계를 통해 `orders` 앱과 `policies` 앱이 `companies` 앱의 `Company` 모델을 참조합니다.

이 문서는 `DN_solution` 시스템의 복잡한 구조와 다양한 컴포넌트 간의 상호작용을 명확하게 이해하는 데 필요한 청사진을 제공합니다.

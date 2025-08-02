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

## 2. 4계층 구조 및 권한 체계

### 2.1 계층 구조 개요

```
Level 0: DBA (Django Admin)
├── Level 1: 본사 (Headquarters)
│   ├── Level 2: 협력사 (Agency) - 승인 권한 있음
│   │   └── Level 3: 판매점 (Retail)
│   └── Level 2: 대리점 (Dealer) - 승인 권한 없음
│       └── Level 3: 판매점 (Retail)
```

### 2.2 각 계층별 권한

| 계층 | 역할 | 승인 권한 | 조회 권한 | 기능 |
|------|------|-----------|-----------|------|
| **Level 0** | DBA | 모든 사용자 | 모든 데이터 | 시스템 전체 관리 |
| **Level 1** | 본사 관리자 | 모든 사용자 | 모든 업체 | 하위 계층 총괄 관리 |
| **Level 2** | 협력사 관리자 | 하위 판매점만 | 자신 + 하위 판매점 | 판매점 승인 및 관리 |
| **Level 2** | 대리점 관리자 | 없음 | 자신 + 하위 판매점 | 조회만 가능 |
| **Level 3** | 판매점 관리자 | 직원만 | 자신의 업체 | 직원 승인 |

### 2.3 사용자 역할 구분

- **관리자 (`admin`)**: 하위 사용자 승인 권한 보유
- **직원 (`staff`)**: 제한된 데이터 조회만 가능

## 3. 프로젝트 구조 상세

`DN_solution` 프로젝트는 모듈화된 개발을 지향하며, 각 앱이 특정 비즈니스 도메인을 담당하도록 설계되었습니다.

```
DN_solution/
├── .git/                   # Git 버전 관리
├── companies/              # Django 앱: 업체 및 사용자 관리
│   ├── __init__.py
│   ├── admin.py            # Django 관리자 페이지 설정
│   ├── apps.py             # Django 앱 설정
│   ├── models.py           # Company, Dealer, CompanyUser, CompanyMessage 모델 정의
│   ├── serializers.py      # DRF Serializer (직렬화/역직렬화)
│   ├── tests.py            # 단위 및 통합 테스트
│   ├── urls.py             # 앱별 URL 라우팅
│   ├── views.py            # DRF ViewSet (API 뷰 로직)
│   ├── management/         # Django 관리 명령어
│   │   └── commands/
│   │       ├── create_initial_admin.py
│   │       ├── approve_existing_users.py
│   │       ├── approve_specific_user.py
│   │       ├── cleanup_data.py
│   │       ├── force_delete_company.py
│   │       └── wipe_all_data.py
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
├── frontend/               # React 프론트엔드 애플리케이션
│   ├── src/
│   │   ├── components/     # React 컴포넌트
│   │   ├── pages/          # 페이지 컴포넌트
│   │   ├── services/       # API 서비스
│   │   └── contexts/       # React Context
│   └── package.json
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

## 4. 주요 앱 간의 데이터 및 로직 흐름

### 4.1. `companies` 앱 (업체 및 사용자 관리)

#### 모델 구조
*   **`Company` 모델:** 본사-협력사-판매점의 3단계 계층 구조
*   **`Dealer` 모델:** 본사 하위의 대리점 (별도 테이블)
*   **`CompanyUser` 모델:** 업체/대리점 소속 사용자 관리
*   **`CompanyMessage` 모델:** 업체/대리점 간 메시지 관리

#### 주요 흐름
1.  **회원가입 요청:** 사용자가 `POST /api/companies/auth/signup/` 엔드포인트로 회원가입 요청
2.  **데이터 검증:** `CompanyUserSerializer`를 통해 데이터 유효성 검증
3.  **업체/대리점 생성:** 상위 업체 코드를 기반으로 업체 또는 대리점 생성
4.  **사용자 생성:** Django User와 CompanyUser 동시 생성
5.  **승인 대기:** 사용자는 `pending` 상태로 생성되어 승인 대기
6.  **승인 프로세스:** 상위 업체 관리자가 `POST /api/companies/users/{id}/approve/` 엔드포인트로 승인

#### 권한 검증 흐름
1.  **로그인:** 사용자가 로그인하여 인증 토큰 획득
2.  **API 요청:** 인증 토큰과 함께 API 요청
3.  **권한 검증:** `IsAuthenticated` 권한 클래스가 토큰 유효성 검증
4.  **계층별 필터링:** `CompanyViewSet.get_queryset()`에서 사용자 계층에 따른 데이터 필터링
5.  **승인 권한 검증:** `can_be_approved_by()` 메서드로 승인 권한 검증

### 4.2. `orders` 앱 (주문 관리)

*   **역할:** 고객 주문 정보를 관리하며, 특정 `Company` 또는 `Dealer`에 귀속됩니다.
*   **`companies` 앱과의 연동:**
    *   `Order` 모델은 `company` 또는 `dealer` 필드를 통해 외래 키로 참조합니다.
    *   주문 생성 시, 해당 주문이 어느 업체/대리점에서 발생했는지 정보를 연결합니다.
    *   주문 관련 API는 계층별 권한에 따라 필터링된 데이터만 제공합니다.

### 4.3. `policies` 앱 (정책 관리)

*   **역할:** 다양한 정책을 정의하고, 이를 특정 `Company` 또는 `Dealer`에 배정합니다.
*   **`companies` 앱과의 연동:**
    *   `PolicyAssignment` 모델은 `company` 또는 `dealer` 필드를 통해 외래 키로 참조합니다.
    *   특정 정책이 어떤 업체/대리점에 적용되는지 정보를 연결합니다.
    *   정책 관련 API는 계층별 권한에 따라 필터링된 데이터만 제공합니다.

## 5. 인증 및 권한 흐름

시스템의 모든 API 요청은 인증 및 권한 검증 과정을 거칩니다.

### 5.1 기본 인증 흐름

1.  **사용자 로그인:** 프론트엔드에서 사용자(예: `CompanyUser`)가 로그인 요청을 보냅니다.
2.  **인증 처리:** 백엔드에서 사용자 자격 증명(username, password)을 확인하고, 성공 시 인증 토큰(예: JWT)을 발급합니다.
3.  **API 요청:** 프론트엔드는 이후 모든 API 요청에 인증 토큰을 포함하여 보냅니다.
4.  **`IsAuthenticated` 권한 검증:** DRF의 `IsAuthenticated` 권한 클래스가 요청을 가로채어 토큰의 유효성을 검증하고 사용자를 인증합니다.

### 5.2 계층별 권한 필터링

1.  **사용자 정보 조회:** 인증된 사용자의 `CompanyUser` 정보(소속 `Company`/`Dealer`의 `type` 및 `id`)를 조회합니다.
2.  **계층별 쿼리셋 필터링:** `CompanyViewSet.get_queryset()` 메서드에서 사용자 계층에 따라 조회 가능한 데이터를 필터링합니다.
    *   **본사 관리자:** 모든 업체/대리점 조회 가능
    *   **협력사 관리자:** 자신의 협력사와 하위 판매점만 조회 가능
    *   **대리점 관리자:** 자신의 대리점과 하위 판매점만 조회 가능 (승인 권한 없음)
    *   **판매점 관리자:** 자신의 판매점만 조회 가능
3.  **승인 권한 검증:** `can_be_approved_by()` 메서드를 통해 승인 권한을 검증합니다.
4.  **응답:** 필터링된 데이터만 사용자에게 반환됩니다.

### 5.3 승인 시스템 흐름

1.  **승인 대기 사용자 조회:** `GET /api/companies/users/unapproved/` 엔드포인트로 승인 대기 사용자 목록 조회
2.  **승인 권한 검증:** `can_be_approved_by()` 메서드로 승인 권한 검증
3.  **승인/거절 처리:** `POST /api/companies/users/{id}/approve/` 또는 `POST /api/companies/users/{id}/reject/` 엔드포인트로 승인/거절
4.  **상태 변경:** 사용자의 `status`와 `is_approved` 필드 업데이트
5.  **로그인 허용:** 승인된 사용자만 로그인 가능

## 6. 데이터 흐름 및 상호작용

### 6.1 프론트엔드 ↔ 백엔드
*   **RESTful API:** JSON 데이터를 통한 HTTP 통신
*   **인증 토큰:** JWT 또는 세션 기반 인증
*   **에러 처리:** 표준화된 HTTP 상태 코드 및 에러 메시지

### 6.2 백엔드 ↔ 데이터베이스
*   **Django ORM:** SQL 쿼리 자동 생성 및 실행
*   **트랜잭션 관리:** 데이터 무결성 보장
*   **마이그레이션:** 스키마 변경 관리

### 6.3 앱 간 데이터 참조
*   **외래키 관계:** `ForeignKey`를 통한 모델 간 관계 설정
*   **역참조:** `related_name`을 통한 역방향 조회
*   **캐싱:** 성능 최적화를 위한 쿼리 캐싱

## 7. 로깅 및 모니터링

### 7.1 로깅 전략
*   **로그 레벨:** DEBUG, INFO, WARNING, ERROR, CRITICAL
*   **구조화된 로깅:** JSON 형태의 로그 출력
*   **컨텍스트 정보:** 사용자 ID, 요청 ID, IP 주소 등 포함

### 7.2 모니터링 포인트
*   **API 응답 시간:** 각 엔드포인트별 응답 시간 측정
*   **에러율:** HTTP 상태 코드별 에러 발생률
*   **사용자 활동:** 로그인, 회원가입, 승인 등의 사용자 활동 추적

이 문서는 `DN_solution` 시스템의 복잡한 구조와 다양한 컴포넌트 간의 상호작용을 명확하게 이해하는 데 필요한 청사진을 제공합니다.

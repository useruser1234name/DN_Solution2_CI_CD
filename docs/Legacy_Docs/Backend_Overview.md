# 백엔드 개요 (Backend Overview)

`DN_solution` 프로젝트의 백엔드는 Django 프레임워크와 Django REST Framework(DRF)를 기반으로 구축된 RESTful API 서버입니다. 이 백엔드는 시스템의 핵심 비즈니스 로직을 처리하고, 데이터베이스와의 상호작용을 관리하며, 프론트엔드 애플리케이션에 데이터를 제공하는 역할을 합니다.

## 1. 기술 스택

*   **프레임워크:** Django 4.x
*   **API 프레임워크:** Django REST Framework (DRF)
*   **데이터베이스:** SQLite (개발용), PostgreSQL/MySQL 등 (운영용)
*   **언어:** Python 3.x
*   **가상 환경:** `venv`

## 2. 아키텍처

백엔드는 Django의 MVT(Model-View-Template) 패턴을 따르지만, DRF를 사용하여 API 엔드포인트를 제공하므로 RESTful 아키텍처의 특성을 가집니다. 각 비즈니스 도메인별로 앱(예: `companies`, `orders`, `policies`)을 분리하여 모듈성과 유지보수성을 높였습니다.

## 3. 주요 앱 및 기능

### 3.1. `companies` 앱

*   **목적:** 업체(`Company`) 및 업체 소속 사용자(`CompanyUser`) 관리, 업체 간 메시지(`CompanyMessage`) 발송.
*   **핵심 모델:**
    *   `Company`: 본사, 협력사, 판매점 등 업체의 계층 구조 및 기본 정보 관리.
    *   `CompanyUser`: 각 업체에 소속된 사용자의 계정 정보 및 역할(관리자/직원) 관리.
    *   `CompanyMessage`: 업체에 발송되는 공지 메시지 관리 (개별/일괄).
*   **주요 API 엔드포인트:**
    *   `/api/companies/companies/`: 업체 목록 조회, 생성, 상세 조회, 수정, 삭제.
    *   `/api/companies/companies/{id}/toggle_status/`: 업체 운영 상태 토글.
    *   `/api/companies/companies/{id}/users/`: 특정 업체의 사용자 목록 조회.
    *   `/api/companies/users/`: 업체 사용자 목록 조회, 생성, 상세 조회, 수정, 삭제.
    *   `/api/companies/messages/`: 업체 메시지 목록 조회, 생성, 상세 조회, 수정, 삭제.
    *   `/api/companies/messages/send_bulk_message/`: 전체 업체에 일괄 메시지 발송.
*   **권한 로직:** `CompanyViewSet`의 `get_queryset` 메서드에서 로그인한 사용자의 역할에 따라 조회 가능한 업체 및 사용자 목록을 동적으로 필터링합니다. (슈퍼유저/본사는 전체, 협력사는 자신과 하위 판매점, 판매점은 자신만).
*   **유효성 검증:** `models.py`의 `clean` 메서드를 통해 모델 레벨에서 계층적 관계(예: 판매점은 반드시 협력사 하위) 및 데이터 무결성을 강제합니다.

### 3.2. `orders` 앱

*   **목적:** 주문 정보 관리.
*   **핵심 모델:** `Order`, `OrderMemo`, `Invoice` 등 주문 처리와 관련된 모델.
*   **주요 API 엔드포인트:** `/api/orders/orders/` 등 주문 생성, 조회, 상태 변경 등.

### 3.3. `policies` 앱

*   **목적:** 정책 정보 관리.
*   **핵심 모델:** `Policy`, `PolicyAssignment` 등 정책 정의 및 업체별 정책 배정 관련 모델.
*   **주요 API 엔드포인트:** `/api/policies/policies/` 등 정책 생성, 조회, 배정 등.

## 4. 인증 및 권한 (Authentication & Authorization)

*   **인증:** DRF의 `IsAuthenticated` 권한 클래스를 사용하여 API 접근 시 인증된 사용자만 허용합니다. 실제 운영 환경에서는 JWT(JSON Web Token) 등을 활용한 토큰 기반 인증이 적용될 수 있습니다.
*   **권한:** 각 `ViewSet`의 `get_queryset` 메서드 및 필요에 따라 커스텀 권한 클래스를 통해 사용자 역할에 따른 세밀한 데이터 접근 제어를 구현합니다.

## 5. 데이터베이스

*   Django ORM(Object-Relational Mapping)을 사용하여 Python 객체로 데이터베이스와 상호작용합니다. 이를 통해 SQL 쿼리를 직접 작성할 필요 없이 데이터베이스 작업을 수행할 수 있습니다.
*   마이그레이션(`migrations`)을 통해 모델 변경 사항을 데이터베이스 스키마에 반영합니다.

## 6. 로깅

`logging` 모듈을 사용하여 애플리케이션의 주요 이벤트(예: 업체 생성/수정/삭제, 사용자 로그인/생성)를 기록합니다. 이는 문제 해결 및 시스템 모니터링에 활용됩니다.

## 7. 개발 환경

*   `venv`를 사용하여 프로젝트별 격리된 Python 환경을 구축합니다.
*   `requirements.txt`에 모든 의존성 패키지를 명시하여 환경 설정의 일관성을 유지합니다.

이 문서는 `DN_solution` 백엔드 시스템의 전반적인 구조와 핵심 기능을 이해하는 데 도움이 될 것입니다.

# 백엔드 설계 (Backend Design)

이 문서는 `DN_solution` 프로젝트의 백엔드 시스템에 대한 상세 설계를 다룹니다. Django 프레임워크와 Django REST Framework(DRF)를 기반으로 하는 아키텍처, 핵심 모델, API 엔드포인트, 그리고 비즈니스 로직 구현에 초점을 맞춥니다.

## 1. 아키텍처 및 기술 스택

*   **프레임워크:** Django 5.2
*   **API 프레임워크:** Django REST Framework (DRF)
*   **언어:** Python 3.13
*   **데이터베이스:** SQLite (개발용), PostgreSQL/MySQL 등 (운영용)
*   **가상 환경:** `venv`
*   **설계 원칙:**
    *   **모듈성:** 각 비즈니스 도메인별로 앱(`companies`, `orders`, `policies`)을 분리하여 코드의 응집도를 높이고 결합도를 낮춥니다.
    *   **RESTful API:** 자원(Resource) 기반의 명확한 API 엔드포인트를 설계하여 클라이언트와의 통신을 표준화합니다.
    *   **계층형 아키텍처:** 모델(데이터), 시리얼라이저(데이터 변환), 뷰(요청 처리), URL(라우팅)의 명확한 역할 분담을 통해 유지보수성을 확보합니다.

## 2. 핵심 앱 상세 설계

### 2.1. `companies` 앱

시스템의 핵심 엔티티인 업체와 사용자를 관리합니다.

#### 2.1.1. 모델 (`models.py`)

*   **`Company` 모델:**
    *   **목적:** 본사, 협력사, 판매점 등 다양한 유형의 업체를 관리하고 계층 구조를 정의합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `parent_company` (ForeignKey to `self`): 상위 업체 참조. 계층 구조의 핵심.
        *   `name` (CharField): 업체명.
        *   `type` (CharField, choices: `headquarters`, `agency`, `retail`): 업체 유형.
        *   `status` (BooleanField): 운영 상태 (활성/비활성).
        *   `visible` (BooleanField): 하부 업체에 노출 여부.
        *   `default_courier` (CharField): 기본 택배사.
        *   `created_at`, `updated_at` (DateTimeField): 생성/수정 일시.
    *   **핵심 로직 (`clean()` 메서드 - 모델 레벨 유효성 검증):**
        *   **본사:** `parent_company`를 가질 수 없으며, 시스템에 하나만 존재해야 합니다.
        *   **협력사:** 반드시 `headquarters` 타입의 `Company`를 `parent_company`로 지정해야 합니다.
        *   **판매점:** 반드시 `agency` 타입의 `Company`를 `parent_company`로 지정해야 합니다.
        *   업체명 중복을 방지합니다.
    *   **로깅 (`save()`, `delete()`):** 생성, 수정, 삭제 시 상세 로그를 기록합니다.

*   **`CompanyUser` 모델:**
    *   **목적:** 각 `Company`에 소속된 사용자의 계정 정보를 관리합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `company` (ForeignKey to `Company`): 소속 업체 참조.
        *   `username` (CharField): 로그인 사용자명 (고유).
        *   `password` (CharField): 비밀번호 (실제로는 해시화).
        *   `role` (CharField, choices: `admin`, `staff`): 사용자 역할.
        *   `last_login`, `created_at` (DateTimeField).
    *   **핵심 로직:** `username` 중복 방지, 비활성 업체에 사용자 추가 금지.

*   **`CompanyMessage` 모델:**
    *   **목적:** 업체에 발송되는 공지 메시지 관리 (개별/일괄).
    *   **필드:** `message`, `is_bulk`, `sent_by` (ForeignKey to Django `User`), `company` (ForeignKey to `Company`), `sent_at`.
    *   **핵심 로직:** 개별 발송 시 `company` 필수, 일괄 발송 시 `company` 불가.

#### 2.1.2. 시리얼라이저 (`serializers.py`)

*   **`CompanySerializer`:** `Company` 모델의 직렬화/역직렬화를 담당합니다. `type_display`, `users_count`, `parent_company_name`, `child_companies`와 같은 읽기 전용 필드를 포함하여 데이터 표현을 풍부하게 합니다.
*   **`CompanyUserSerializer`:** `CompanyUser` 모델의 직렬화/역직렬화를 담당합니다. `password` 필드를 `write_only`로 설정하여 보안을 강화합니다.
*   **`CompanyMessageSerializer`:** `CompanyMessage` 모델의 직렬화/역직렬화를 담당합니다.
*   **유효성 검증:** 각 시리얼라이저의 `validate_필드명()` 및 `validate()` 메서드를 통해 API 요청 데이터의 유효성을 검증합니다.

#### 2.1.3. 뷰셋 (`views.py`)

*   **`CompanyViewSet`:** `Company` 모델에 대한 CRUD 및 추가 액션(일괄 삭제, 상태 토글, 사용자 목록 조회)을 제공합니다.
    *   **`get_queryset()` (권한 필터링 핵심):**
        *   `user.is_superuser`: 모든 `Company` 객체 반환.
        *   `headquarters` 타입 `CompanyUser`: 모든 `Company` 객체 반환.
        *   `agency` 타입 `CompanyUser`: 자신의 `Company` 객체와 `parent_company`가 자신인 `retail` 타입 `Company` 객체들을 반환.
        *   `retail` 타입 `CompanyUser`: 자신의 `Company` 객체만 반환.
    *   **`create()` (Company 생성 정책):**
        *   **현재 로직:** 본사 계정은 협력사를 생성할 수 있으며, 유효한 상위 협력사를 지정하는 경우 판매점도 생성할 수 있습니다. 협력사 계정은 자신의 하위에 판매점을 생성할 수 있습니다.
        *   **향후 강화 방안 (본사의 판매점 직접 생성 금지):** `create` 메서드 내에서 요청을 보낸 사용자가 본사 계정이고 생성하려는 `Company`의 `type`이 `retail`인 경우 `HTTP_403_FORBIDDEN` 또는 `HTTP_400_BAD_REQUEST`를 반환하는 로직을 추가할 수 있습니다.
    *   **`users()` 액션:** 특정 `Company`에 속한 `CompanyUser` 목록을 반환합니다. `agency` 타입 `Company`의 경우, 하위 `retail` `Company`에 속한 사용자들도 함께 반환합니다.

*   **`CompanyUserViewSet`:** `CompanyUser` 모델에 대한 CRUD 작업을 제공합니다.
*   **`CompanyMessageViewSet`:** `CompanyMessage` 모델에 대한 CRUD 및 `send_bulk_message` 액션을 제공합니다.

#### 2.1.4. URL 라우팅 (`urls.py`)

*   DRF `DefaultRouter`를 사용하여 `CompanyViewSet`, `CompanyUserViewSet`, `CompanyMessageViewSet`에 대한 RESTful URL 패턴을 자동으로 생성합니다.
*   `model-test/`와 같은 커스텀 뷰에 대한 URL도 정의합니다.

### 2.2. `orders` 앱 상세 설계

*   **목적:** 고객 주문 정보의 생성, 조회, 관리 및 상태 변경을 처리합니다.
*   **모델:** `Order`, `OrderMemo`, `Invoice`, `OrderRequest`.
*   **주요 로직:**
    *   **`Order` 모델:**
        *   고객 정보를 개별 필드로 관리 (`customer_name`, `customer_phone`, `customer_email`, `customer_address`)
        *   `update_status()`: 주문 상태를 변경하고, 유효하지 않은 상태 전환을 방지합니다.
        *   `calculate_rebate()`: 정책 기반 리베이트 계산 로직
        *   `created_by` (ForeignKey to `User`): 주문 생성자 추적
    *   **`OrderMemo` 모델:** 주문 처리 과정에서 발생하는 메모를 기록합니다.
    *   **`Invoice` 모델:** 
        *   송장 정보 관리 및 배송 완료 여부를 추적합니다.
        *   `recipient_name`, `recipient_phone` 필드 추가
        *   `sent_at`, `delivered_at` 시간 추적
        *   `mark_as_delivered()` 메서드로 배송 완료 처리
    *   **`OrderRequest` 모델:**
        *   교환, 취소, 반품 요청 관리
        *   `complete()` 메서드로 요청 완료 처리
        *   `processed_by` (ForeignKey to `User`): 처리자 추적

### 2.3. `policies` 앱 상세 설계

*   **목적:** 스마트기기 판매 정책을 정의하고, 이를 특정 업체에 배정하며, 리베이트 계산 등의 비즈니스 로직을 처리합니다.
*   **모델:** `Policy`, `PolicyNotice`, `PolicyAssignment`.
*   **주요 로직:**
    *   **`Policy` 모델:**
        *   정책의 제목, 설명, 폼 유형, 통신사, 가입기간, 리베이트율 등을 정의합니다.
        *   `carrier` (CharField): 통신사 필터링 (SKT, KT, LG U+ 등)
        *   `contract_period` (CharField): 가입기간 필터링 (12개월, 24개월 등)
        *   `expose` (BooleanField): 프론트엔드 노출 여부
        *   `premium_market_expose` (BooleanField): 프리미엄 마켓 자동 노출 여부
        *   `rebate_agency` (DecimalField): 대리점 리베이트 금액
        *   `rebate_retail` (DecimalField): 판매점 리베이트 금액
        *   `generate_html_content()`: 정책 데이터 기반 HTML 콘텐츠 자동 생성
        *   `toggle_expose()`, `toggle_premium_market_expose()`: 노출 상태 토글
        *   `clean()`: 제목 중복 검증, 리베이트 유효성 검증
    *   **`PolicyNotice` 모델:**
        *   정책별 안내사항 관리 (고객 안내, 업체 공지, 정책 특이사항, 일반 공지)
        *   `notice_type` (CharField): 안내 유형 구분
        *   `is_important` (BooleanField): 중요 안내 여부
        *   `order` (IntegerField): 표시 순서
    *   **`PolicyAssignment` 모델:**
        *   특정 `Policy`를 특정 `Company`에 배정하고, 커스텀 리베이트율을 설정할 수 있습니다.
        *   `custom_rebate` (DecimalField): 업체별 커스텀 리베이트
        *   `expose_to_child` (BooleanField): 하위 업체 노출 여부
        *   `get_effective_rebate()`: 배정된 정책의 실제 리베이트율을 계산합니다 (커스텀 리베이트 우선)
        *   `get_rebate_source()`: 리베이트 출처 표시 (기본값/커스텀)

#### 2.3.1. 정책 관리 뷰 (`views.py`)

*   **`PolicyListView`:** 정책 목록 조회, 필터링, 검색, 페이지네이션
*   **`PolicyDetailView`:** 정책 상세 정보 및 관련 안내사항, 배정 업체 목록
*   **`PolicyCreateView`:** 새 정책 생성
*   **`PolicyUpdateView`:** 정책 수정
*   **`PolicyDeleteView`:** 정책 삭제
*   **API 엔드포인트:**
    *   `toggle_policy_expose()`: 정책 노출 상태 토글
    *   `toggle_premium_market_expose()`: 프리미엄 마켓 노출 상태 토글
    *   `regenerate_html()`: HTML 콘텐츠 재생성
    *   `check_duplicate_policy()`: 정책 제목 중복 체크
    *   `policy_api_list()`: AJAX 기반 정책 목록 (필터링, 페이지네이션)
    *   `policy_statistics()`: 정책 통계 정보

#### 2.3.2. 정책 관리 Admin (`admin.py`)

*   **`PolicyAdmin`:** 정책 관리 인터페이스
    *   `list_display`: 정책 목록 표시 필드
    *   `list_filter`: 필터링 옵션
    *   `search_fields`: 검색 필드
    *   `fieldsets`: 폼 필드 그룹화
    *   `actions`: 일괄 작업 (노출 토글, HTML 재생성)
    *   `PolicyNoticeInline`: 안내사항 인라인 편집
*   **`PolicyNoticeAdmin`:** 안내사항 관리
*   **`PolicyAssignmentAdmin`:** 정책 배정 관리

#### 2.3.3. 정책 관리 시리얼라이저 (`serializers.py`)

*   **`PolicySerializer`:** 정책 기본 정보 직렬화
*   **`PolicyNoticeSerializer`:** 안내사항 직렬화
*   **`PolicyAssignmentSerializer`:** 정책 배정 직렬화
*   **`PolicyDetailSerializer`:** 정책 상세 정보 (중첩 안내사항, 배정 포함)
*   **`PolicyCreateSerializer`:** 정책 생성 (중첩 안내사항 포함)
*   **`PolicyUpdateSerializer`:** 정책 수정 (안내사항 재생성)

#### 2.3.4. 정책 관리 템플릿

*   **`policy_list.html`:** 정책 목록 페이지
    *   필터링 폼 (검색, 신청서 타입, 통신사, 가입기간, 노출 상태)
    *   정책 테이블 (토글 스위치, 액션 버튼)
    *   AJAX 기반 실시간 상태 변경
    *   페이지네이션
*   **`policy_form.html`:** 정책 생성/수정 폼
    *   단계별 입력 섹션 (기본 정보, 신청서 설정, 필터링 설정, 리베이트 설정, 노출 설정)
    *   실시간 중복 체크
    *   클라이언트 사이드 유효성 검증

## 3. 공통 백엔드 설계 요소

*   **인증 및 권한:**
    *   `rest_framework.permissions.IsAuthenticated`를 사용하여 인증된 사용자만 API 접근을 허용합니다.
    *   `CompanyViewSet.get_queryset()`에서 객체 레벨 권한을 구현하여 사용자의 역할에 따라 접근 가능한 데이터를 제한합니다.
*   **데이터 유효성 검증:**
    *   **모델 레벨:** `models.py`의 `clean()` 메서드를 통해 데이터베이스 저장 전 비즈니스 규칙을 검증합니다.
    *   **시리얼라이저 레벨:** `serializers.py`의 `validate_필드명()` 및 `validate()` 메서드를 통해 API 요청 데이터의 형식을 검증하고 비즈니스 규칙을 확인합니다.
*   **트랜잭션:** `django.db.transaction.atomic()`을 사용하여 여러 데이터베이스 작업의 원자성을 보장합니다.
*   **로깅:** `logging` 모듈을 사용하여 시스템의 모든 주요 동작과 통신을 상세하게 기록합니다 (자세한 내용은 `Development_Practices.md` 참조).
*   **예외 처리:** `try-except` 블록을 사용하여 런타임 오류를 처리하고, DRF의 `EXCEPTION_HANDLER`를 커스터마이징하여 일관된 오류 응답을 제공합니다 (자세한 내용은 `Development_Practices.md` 참조).

이 문서는 `DN_solution` 백엔드 시스템의 상세한 설계와 구현 방식을 이해하는 데 필요한 모든 정보를 제공합니다.

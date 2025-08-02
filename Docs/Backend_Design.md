# HB Admin 백엔드 설계 (Backend Design)

이 문서는 HB Admin 프로젝트의 백엔드 시스템에 대한 상세 설계를 다룹니다. Django 프레임워크와 Django REST Framework(DRF)를 기반으로 하는 아키텍처, 핵심 모델, API 엔드포인트, 그리고 비즈니스 로직 구현에 초점을 맞춥니다.

## 1. 아키텍처 및 기술 스택

*   **프레임워크:** Django 5.2.4
*   **API 프레임워크:** Django REST Framework (DRF) 3.16.0
*   **언어:** Python 3.13
*   **데이터베이스:** SQLite (개발용), PostgreSQL/MySQL 등 (운영용)
*   **가상 환경:** `venv`
*   **설계 원칙:**
    *   **모듈성:** 각 비즈니스 도메인별로 앱(`companies`, `policies`, `orders`, `inventory`, `messaging`)을 분리하여 코드의 응집도를 높이고 결합도를 낮춥니다.
    *   **RESTful API:** 자원(Resource) 기반의 명확한 API 엔드포인트를 설계하여 클라이언트와의 통신을 표준화합니다.
    *   **계층형 아키텍처:** 모델(데이터), 시리얼라이저(데이터 변환), 뷰(요청 처리), URL(라우팅)의 명확한 역할 분담을 통해 유지보수성을 확보합니다.

## 2. 핵심 앱 상세 설계

### 2.1. `companies` 앱

시스템의 핵심 엔티티인 업체와 사용자를 관리합니다.

#### 2.1.1. 모델 (`models.py`)

*   **`Company` 모델:**
    *   **목적:** 본사, 협력사, 대리점, 판매점 등 다양한 유형의 업체를 관리하고 계층 구조를 정의합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `code` (CharField): 고유한 업체 식별 코드. 계층별 승인 시스템의 기반.
        *   `name` (CharField): 업체명.
        *   `type` (CharField, choices: `headquarters`, `agency`, `dealer`, `retail`): 업체 유형.
        *   `parent_company` (ForeignKey to `self`): 상위 업체 참조. 계층 구조의 핵심.
        *   `status` (BooleanField): 운영 상태 (활성/비활성).
        *   `visible` (BooleanField): 하부 업체에 노출 여부.
        *   `default_courier` (CharField): 기본 택배사.
        *   `created_at`, `updated_at` (DateTimeField): 생성/수정 일시.
    *   **핵심 로직 (`clean()` 메서드 - 모델 레벨 유효성 검증):**
        *   **본사:** `parent_company`를 가질 수 없으며, 시스템에 하나만 존재해야 합니다.
        *   **협력사:** 반드시 `headquarters` 타입의 `Company`를 `parent_company`로 지정해야 합니다.
        *   **판매점:** 반드시 `agency` 타입의 `Company`를 `parent_company`로 지정해야 합니다.
        *   **대리점:** 반드시 `headquarters` 타입의 `Company`를 `parent_company`로 지정해야 합니다.
    *   **로깅 (`save()`, `delete()`):** 생성, 수정, 삭제 시 상세 로그를 기록합니다.

*   **`CompanyUser` 모델:**
    *   **목적:** 각 `Company`에 소속된 사용자의 계정 정보를 관리합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `company` (ForeignKey to `Company`): 소속 업체 참조.
        *   `django_user` (OneToOneField to `User`): Django User와의 연결.
        *   `username` (CharField): 로그인 사용자명 (고유).
        *   `role` (CharField, choices: `admin`, `staff`): 사용자 역할.
        *   `is_approved` (BooleanField): 승인 여부 (기본값: False).
        *   `status` (CharField, choices: `pending`, `approved`, `rejected`): 승인 상태.
        *   `last_login`, `created_at` (DateTimeField).
    *   **핵심 로직:** 
        *   `username` 중복 방지, 비활성 업체에 사용자 추가 금지.
        *   `can_be_approved_by()`: 특정 사용자가 이 사용자를 승인할 수 있는지 검증.
        *   `approve()`, `reject()`: 승인/거절 처리 메서드.

*   **`CompanyMessage` 모델:**
    *   **목적:** 업체에 발송되는 공지 메시지 관리 (개별/일괄).
    *   **필드:** `message`, `message_type`, `is_bulk`, `sent_by` (ForeignKey to `User`), `company` (ForeignKey to `Company`), `sent_at`.
    *   **핵심 로직:** 개별 발송 시 `company` 필수, 일괄 발송 시 `company` 불가.

#### 2.1.2. Django Admin 설정 (`admin.py`)

*   **`CompanyAdmin`:** 업체 목록, 필터링, 검색, 사용자 수 표시 기능
*   **`CompanyUserAdmin`:** 사용자 관리, Django User 자동 생성
*   **`CompanyMessageAdmin`:** 메시지 관리, 권한별 필터링

#### 2.1.3. 관리 명령어 (`management/commands/`)

*   **`create_initial_admin`:** 초기 관리자 계정 생성 명령어

### 2.2. `policies` 앱

정책 관리 시스템을 담당합니다.

#### 2.2.1. 모델 (`models.py`)

*   **`Policy` 모델:**
    *   **목적:** 상품 정책을 관리하는 핵심 모델입니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `company` (ForeignKey to `Company`): 등록 업체.
        *   `title` (CharField): 정책 제목.
        *   `description` (TextField): 정책 설명.
        *   `rebate_rate` (DecimalField): 기본 리베이트율 (%).
        *   `reception_type` (CharField, choices: `general`, `link`, `registration`, `egg`): 접수 방식.
        *   `html_content` (TextField): 자동 생성된 HTML 내용.
        *   `is_shared` (BooleanField): 공유 여부.
        *   `is_active` (BooleanField): 활성화 여부.
    *   **핵심 로직:**
        *   `generate_html_content()`: HTML 내용 자동 생성.
        *   `toggle_share()`, `toggle_active()`: 상태 토글 메서드.

*   **`PolicyAssignment` 모델:**
    *   **목적:** 특정 정책을 특정 업체에 배정하고 커스텀 리베이트율을 설정합니다.
    *   **필드:** `policy`, `company`, `custom_rebate_rate`, `is_active`.
    *   **핵심 로직:** `get_effective_rebate()`: 실제 적용되는 리베이트율 반환.

*   **`PolicyShare` 모델:**
    *   **목적:** 검증된 업체 간 정책 공유를 관리합니다.
    *   **필드:** `source_policy`, `target_company`, `shared_rebate_rate`, `is_approved`.
    *   **핵심 로직:** `approve()`, `reject()`: 공유 승인/거절 처리.

### 2.3. `orders` 앱

주문 관리 시스템을 담당합니다.

#### 2.3.1. 모델 (`models.py`)

*   **`Order` 모델:**
    *   **목적:** 고객 주문을 관리하는 핵심 모델입니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `policy` (ForeignKey to `Policy`): 적용 정책.
        *   `company` (ForeignKey to `Company`): 주문 업체.
        *   `customer_info` (JSONField): 고객 정보.
        *   `status` (CharField, choices: `pending`, `processing`, `shipped`, `completed`, `cancelled`, `return_requested`, `exchanged`): 주문 상태.
        *   `tracking_number` (CharField): 송장번호.
        *   `total_amount` (DecimalField): 총 금액.
        *   `rebate_amount` (DecimalField): 리베이트 금액.
        *   `notes` (TextField): 메모.
    *   **핵심 로직:**
        *   `calculate_rebate()`: 리베이트 금액 계산.
        *   `update_status()`: 주문 상태 업데이트.
        *   `can_transition_to()`: 상태 전환 가능 여부 검증.
        *   `add_tracking_number()`: 송장번호 등록.

*   **`OrderMemo` 모델:**
    *   **목적:** 주문 처리 과정에서 발생하는 메모를 기록합니다.
    *   **필드:** `order`, `content`, `created_by`, `created_at`.

*   **`Invoice` 모델:**
    *   **목적:** 송장 정보를 관리하고 배송 완료 여부를 추적합니다.
    *   **필드:** `order`, `tracking_number`, `courier`, `is_delivered`, `delivered_at`.
    *   **핵심 로직:** `mark_as_delivered()`: 배송완료 처리.

*   **`OrderRequest` 모델:**
    *   **목적:** 고객의 교환/취소 요청을 관리합니다.
    *   **필드:** `order`, `request_type`, `reason`, `status`, `processed_by`, `processed_at`.
    *   **핵심 로직:** `approve()`, `reject()`: 요청 승인/거절 처리.

### 2.4. `inventory` 앱

재고 및 기기 관리 시스템을 담당합니다.

#### 2.4.1. 모델 (`models.py`)

*   **`Device` 모델:**
    *   **목적:** 기기 정보를 관리하는 핵심 모델입니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `company` (ForeignKey to `Company`): 소유 업체.
        *   `device_type` (CharField, choices: `phone`, `tablet`, `laptop`, `desktop`, `accessory`, `other`): 기기 유형.
        *   `model_name` (CharField): 모델명.
        *   `serial_number` (CharField): 시리얼번호 (고유).
        *   `status` (CharField, choices: `available`, `in_use`, `maintenance`, `retired`): 상태.
        *   `purchase_date` (DateField): 구매일.
        *   `warranty_expiry` (DateField): 보증만료일.
    *   **핵심 로직:**
        *   `is_available`: 사용 가능 여부.
        *   `is_warranty_valid`: 보증 유효 여부.

*   **`Inventory` 모델:**
    *   **목적:** 각 업체별 재고를 관리합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `company` (ForeignKey to `Company`): 소유 업체.
        *   `product_name` (CharField): 상품명.
        *   `product_code` (CharField): 상품코드.
        *   `quantity` (IntegerField): 수량.
        *   `unit_price` (DecimalField): 단가.
        *   `min_stock` (IntegerField): 최소재고.
        *   `max_stock` (IntegerField): 최대재고.
        *   `location` (CharField): 보관위치.
    *   **핵심 로직:**
        *   `total_value`: 총 재고 가치.
        *   `is_low_stock`: 재고 부족 여부.
        *   `is_overstock`: 재고 과다 여부.
        *   `add_stock()`, `remove_stock()`: 재고 추가/차감.

*   **`DeviceLog` 모델:**
    *   **목적:** 기기 사용 이력을 관리합니다.
    *   **필드:** `device`, `log_type`, `user`, `notes`, `created_at`.

*   **`InventoryTransaction` 모델:**
    *   **목적:** 재고 입출고 이력을 관리합니다.
    *   **필드:** `inventory`, `transaction_type`, `quantity`, `unit_price`, `user`, `reference`, `notes`.
    *   **핵심 로직:** `total_amount`: 거래 총액.

### 2.5. `messaging` 앱

메시지 관리 시스템을 담당합니다.

#### 2.5.1. 모델 (`models.py`)

*   **`MessageTemplate` 모델:**
    *   **목적:** 재사용 가능한 메시지 템플릿을 관리합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `name` (CharField): 템플릿명.
        *   `template_type` (CharField, choices: `order_status`, `approval`, `notification`, `marketing`, `custom`): 템플릿 유형.
        *   `content` (TextField): 메시지 내용.
        *   `variables` (JSONField): 변수 목록.
        *   `is_active` (BooleanField): 활성화 여부.
        *   `created_by` (ForeignKey to `CompanyUser`): 생성자.
    *   **핵심 로직:** `render_content()`: 템플릿 내용 렌더링.

*   **`Message` 모델:**
    *   **목적:** 실제 발송되는 메시지를 관리합니다.
    *   **필드:**
        *   `id` (UUIDField): 고유 식별자.
        *   `template` (ForeignKey to `MessageTemplate`): 템플릿.
        *   `message_type` (CharField, choices: `sms`, `lms`, `mms`): 메시지 유형.
        *   `recipient_phone` (CharField): 수신번호.
        *   `content` (TextField): 메시지 내용.
        *   `status` (CharField, choices: `pending`, `sending`, `sent`, `failed`, `cancelled`): 발송 상태.
        *   `sent_by` (ForeignKey to `CompanyUser`): 발송자.
        *   `company` (ForeignKey to `Company`): 발송 업체.
        *   `external_id` (CharField): 외부 시스템 ID.
        *   `error_message` (TextField): 에러 메시지.
        *   `sent_at` (DateTimeField): 발송일시.
    *   **핵심 로직:**
        *   `send()`: 메시지 발송.
        *   `cancel()`: 메시지 발송 취소.

*   **`ScheduledMessage` 모델:**
    *   **목적:** 예약된 메시지 발송을 관리합니다.
    *   **필드:** `message`, `scheduled_at`, `is_sent`, `sent_at`.
    *   **핵심 로직:** `send_scheduled_message()`: 예약된 메시지 발송.

*   **`BulkMessage` 모델:**
    *   **목적:** 여러 수신자에게 동시에 발송하는 메시지를 관리합니다.
    *   **필드:** `template`, `message_type`, `recipients`, `content`, `sent_by`, `company`, `total_count`, `success_count`, `failed_count`, `is_completed`.
    *   **핵심 로직:** `send_bulk_messages()`: 일괄 메시지 발송.

*   **`MessageLog` 모델:**
    *   **목적:** 메시지 발송 이력을 관리합니다.
    *   **필드:** `message`, `action`, `status`, `details`, `created_at`.

## 3. 계층별 승인 시스템 설계

### 3.1. 업체 코드 시스템

*   **목적:** 각 업체를 고유하게 식별하고 계층별 승인 시스템의 기반을 마련합니다.
*   **코드 생성 규칙:** `{TYPE}_{UUID}` 형식 (예: `HQ_MAIN`, `AGENCY_001`, `RETAIL_001`)
*   **검증 로직:** 중복 코드 방지 및 계층별 코드 형식 검증

### 3.2. 계층별 회원가입 워크플로우

1. **사용자 회원가입 요청**
2. **상위 업체 코드 검증**
   - 본사: 상위 업체 코드 불필요
   - 협력사: 본사 코드 필수
   - 판매점: 협력사 코드 필수
   - 대리점: 본사 코드 필수
3. **업체 및 사용자 생성 (승인 대기 상태)**
4. **상위 업체 관리자에게 승인 요청 알림**
5. **승인/거절 처리**
6. **승인된 사용자 로그인 가능**

### 3.3. 승인 권한 체계

*   **본사 관리자:** 모든 업체 사용자 승인 가능
*   **협력사 관리자:** 자신의 하위 판매점 사용자만 승인 가능
*   **대리점 관리자:** 승인 권한 없음 (조회만 가능)
*   **판매점 관리자:** 직원만 승인 가능
*   **슈퍼유저:** 모든 사용자 승인 가능

## 4. 공통 백엔드 설계 요소

*   **인증 및 권한:**
    *   `rest_framework.permissions.IsAuthenticated`를 사용하여 인증된 사용자만 API 접근을 허용합니다.
    *   각 ViewSet의 `get_queryset()`에서 객체 레벨 권한을 구현하여 사용자의 역할에 따라 접근 가능한 데이터를 제한합니다.
*   **데이터 유효성 검증:**
    *   **모델 레벨:** `models.py`의 `clean()` 메서드를 통해 데이터베이스 저장 전 비즈니스 규칙을 검증합니다.
    *   **시리얼라이저 레벨:** `serializers.py`의 `validate_필드명()` 및 `validate()` 메서드를 통해 API 요청 데이터의 형식을 검증하고 비즈니스 규칙을 확인합니다.
*   **트랜잭션:** `django.db.transaction.atomic()`을 사용하여 여러 데이터베이스 작업의 원자성을 보장합니다.
*   **로깅:** `logging` 모듈을 사용하여 시스템의 모든 주요 동작과 통신을 상세하게 기록합니다.
*   **예외 처리:** `try-except` 블록을 사용하여 런타임 오류를 처리하고, DRF의 `EXCEPTION_HANDLER`를 커스터마이징하여 일관된 오류 응답을 제공합니다.

## 5. 확장성 고려사항

### 5.1. 모델 확장

*   **새로운 업체 유형 추가:** `Company` 모델의 `type` 필드에 새로운 선택지 추가
*   **새로운 사용자 역할 추가:** `CompanyUser` 모델의 `role` 필드에 새로운 선택지 추가
*   **새로운 주문 상태 추가:** `Order` 모델의 상태 필드 확장
*   **새로운 기기 유형 추가:** `Device` 모델의 `device_type` 필드 확장

### 5.2. API 확장

*   **새로운 엔드포인트 추가:** DRF ViewSet을 활용한 RESTful API 확장
*   **새로운 액션 추가:** 커스텀 액션 메서드를 통한 기능 확장
*   **새로운 시리얼라이저 추가:** 데이터 변환 로직 확장

### 5.3. 비즈니스 로직 확장

*   **새로운 승인 규칙:** `can_be_approved_by()` 메서드 확장
*   **새로운 상태 전환:** `can_transition_to()` 메서드 확장
*   **새로운 계산 로직:** 리베이트 계산, 재고 계산 등 확장

이 문서는 HB Admin 백엔드 시스템의 상세한 설계와 구현 방식을 이해하는 데 필요한 모든 정보를 제공합니다.

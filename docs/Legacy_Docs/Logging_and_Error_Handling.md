# 로깅 및 오류 처리 전략 (Logging and Error Handling Strategy)

이 문서는 `DN_solution` 프로젝트의 명확한 유지보수성, 문제 진단 및 시스템 안정성 확보를 위한 로깅 및 오류 처리 전략을 정의합니다. 모든 코드 작성자는 이 가이드라인을 준수하여 시스템의 투명성과 견고성을 높여야 합니다.

## 1. 로깅 전략 (Logging Strategy)

모든 시스템의 동작 과정, 내부 상태 변화, 외부 시스템과의 통신 내용을 상세하게 기록하여 시스템의 흐름을 추적하고 문제 발생 시 원인을 신속하게 파악할 수 있도록 합니다.

### 1.1. 로깅의 목적

*   **문제 진단 및 디버깅:** 오류 발생 시 정확한 원인과 발생 지점을 파악합니다.
*   **시스템 상태 모니터링:** 시스템의 정상 작동 여부, 성능 병목 현상 등을 지속적으로 감시합니다.
*   **비즈니스 흐름 추적:** 특정 요청이 시스템 내에서 어떻게 처리되었는지 전체 과정을 파악합니다.
*   **보안 감사:** 비정상적인 접근 시도나 데이터 변경 이력을 기록하여 보안 위협에 대응합니다.
*   **유지보수성 향상:** 코드 변경 없이도 시스템의 동작을 이해하고 분석할 수 있는 정보를 제공합니다.

### 1.2. 로깅 레벨 활용

Python의 `logging` 모듈에서 제공하는 표준 로깅 레벨을 목적에 맞게 사용합니다.

*   **`DEBUG`:** 개발 단계에서만 필요한 상세 정보. 변수 값, 함수 호출 흐름 등.
*   **`INFO`:** 시스템의 일반적인 동작 흐름. 주요 기능의 시작/종료, 성공적인 작업 완료 등.
    *   예: `INFO 새로운 업체가 등록되었습니다: {업체명} ({유형})`
    *   예: `INFO 업체 정보가 수정되었습니다: {이전 업체명} -> {새 업체명}`
    *   예: `INFO 업체 목록 조회 요청 - 사용자: {사용자명}`
*   **`WARNING`:** 잠재적인 문제 발생 가능성. 예상치 못한 상황이지만 시스템 동작에는 큰 영향이 없는 경우.
    *   예: `WARNING 중복 업체명으로 생성/수정 시도: {업체명}`
    *   예: `WARNING 사용자가 있는 업체 삭제 시도: {업체명} (사용자 수: {수})`
*   **`ERROR`:** 기능 수행 실패. 요청 처리 실패, 예상치 못한 예외 발생 등.
    *   예: `ERROR 업체 생성 실패: {오류 메시지} - 데이터: {요청 데이터}`
    *   예: `ERROR 업체 저장 중 오류 발생: {오류 메시지} - 업체: {업체명}`
*   **`CRITICAL`:** 시스템 전체의 심각한 문제. 즉시 개입이 필요한 상황.

### 1.3. 로깅 내용의 상세화

모든 주요 기능의 입력, 출력, 내부 처리 과정, 그리고 외부 시스템(DB, 다른 API)과의 통신 내용을 명확하게 기록합니다.

*   **입력 (Input):**
    *   API 요청의 경우: 요청 URL, HTTP 메서드, 요청 본문(민감 정보 제외), 요청 헤더(필요시).
    *   함수 호출의 경우: 주요 인자 값.
*   **출력 (Output):**
    *   API 응답의 경우: HTTP 상태 코드, 응답 본문(민감 정보 제외).
    *   함수 반환 값.
*   **통신 (Communication):**
    *   데이터베이스 쿼리 실행 전/후 (개발/디버그 모드에서). `django.db.backends` 로거 활용.
    *   외부 API 호출 시: 요청 URL, 요청 본문, 응답 상태 코드, 응답 본문.
*   **내부 처리 과정:**
    *   주요 비즈니스 로직의 분기점.
    *   데이터 변환 과정.
    *   트랜잭션 시작/커밋/롤백.
*   **컨텍스트 정보:**
    *   로그인한 사용자 정보 (ID, username, 역할).
    *   관련 객체 ID (예: `Company` ID, `CompanyUser` ID).
    *   요청 ID (가능하다면, 단일 요청의 모든 로그를 연결할 수 있는 고유 ID).

### 1.4. 로깅 예시 (Python `logging`)

```python
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

def create_company(request_data, user):
    logger.info(f"[Company Creation] Request received from user: {user.username}, Data: {request_data}")
    try:
        with transaction.atomic():
            # 데이터 유효성 검증 및 모델 생성 로직
            company = Company.objects.create(**request_data)
            logger.info(f"[Company Creation] Successfully created company: {company.name} (ID: {company.id})")
            return company
    except ValidationError as e:
        logger.warning(f"[Company Creation] Validation failed for data: {request_data}, Error: {e.message}")
        raise
    except Exception as e:
        logger.error(f"[Company Creation] Unexpected error during company creation for user {user.username}: {e}", exc_info=True)
        raise
```

## 2. 엣지 케이스 및 예외 처리 (Edge Cases and Exception Handling)

시스템의 안정성과 사용자 경험을 보장하기 위해 예상치 못한 상황(엣지 케이스)과 오류(예외)를 체계적으로 처리해야 합니다.

### 2.1. 엣지 케이스 정의 및 처리

엣지 케이스는 일반적인 흐름에서 벗어나는 극단적인 입력 값, 시스템 상태, 또는 사용자 행동을 의미합니다. 이들은 사전에 식별하고 명확하게 처리 로직을 정의해야 합니다.

*   **예시 엣지 케이스:**
    *   **데이터 관련:**
        *   필수 필드 누락 (예: 업체명 없이 Company 생성).
        *   중복 데이터 입력 (예: 동일한 업체명으로 Company 생성).
        *   유효하지 않은 참조 (예: 존재하지 않는 `parent_company` ID로 Company 생성).
        *   비활성화된 업체에 사용자 추가 시도.
    *   **권한 관련:**
        *   권한 없는 사용자가 특정 API 엔드포인트에 접근 시도.
        *   본사 계정이 판매점을 직접 생성 시도 (향후 정책).
    *   **시스템 상태 관련:**
        *   외부 API 호출 실패 또는 타임아웃.
        *   데이터베이스 연결 오류.
*   **처리 방안:**
    *   **유효성 검증:** 모델의 `clean()` 메서드, DRF Serializer의 `validate()` 메서드, 뷰 레벨의 추가 검증을 통해 잘못된 입력을 사전에 차단하고 사용자에게 명확한 오류 메시지를 반환합니다.
    *   **명시적 조건문:** 엣지 케이스를 처리하기 위한 `if/else` 또는 `try/except` 블록을 명확하게 작성합니다.
    *   **적절한 HTTP 상태 코드 반환:** 클라이언트에게 오류의 성격을 명확히 전달하기 위해 `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict` 등 적절한 HTTP 상태 코드를 사용합니다.

### 2.2. 예외 처리 (Exception Handling)

예상치 못한 오류(런타임 에러)가 발생했을 때 시스템이 비정상적으로 종료되거나 사용자에게 불친절한 메시지를 노출하는 것을 방지합니다.

*   **`try-except` 블록 활용:** 오류가 발생할 수 있는 코드 블록을 `try`로 감싸고, 예상되는 예외를 `except`로 처리합니다.
*   **구체적인 예외 처리:** `Exception`과 같은 일반적인 예외보다는 `DoesNotExist`, `ValidationError`, `IntegrityError` 등 구체적인 예외 타입을 명시하여 처리합니다.
*   **오류 로깅:** 예외 발생 시 반드시 `ERROR` 레벨로 상세한 로그를 기록합니다. `exc_info=True` 옵션을 사용하여 스택 트레이스(Stack Trace)를 함께 기록하여 문제 진단에 필요한 모든 정보를 확보합니다.
*   **사용자 친화적인 메시지:** 내부적인 오류 메시지를 사용자에게 직접 노출하지 않고, 일반적이고 이해하기 쉬운 오류 메시지를 반환합니다.
*   **우아한 실패 (Graceful Degradation):** 가능한 경우, 오류가 발생하더라도 시스템의 다른 부분이 계속 작동하도록 설계합니다.
*   **재시도 로직:** 외부 시스템과의 통신 실패와 같이 일시적인 오류의 경우, 재시도(Retry) 로직을 고려할 수 있습니다.

### 2.3. 중앙 집중식 오류 처리 (DRF)

Django REST Framework는 중앙 집중식 예외 처리를 위한 메커니즘을 제공합니다. `settings.py`에서 `REST_FRAMEWORK` 설정의 `EXCEPTION_HANDLER`를 커스터마이징하여 모든 API 예외를 일관된 형식으로 처리할 수 있습니다.

```python
# hb_admin/settings.py

REST_FRAMEWORK = {
    # ...
    'EXCEPTION_HANDLER': 'path.to.your.custom_exception_handler',
}
```

```python
# path/to/your/custom_exception_handler.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # DRF의 기본 예외 핸들러를 호출하여 표준 응답을 얻습니다.
    response = exception_handler(exc, context)

    # 예상치 못한 예외 (500 Internal Server Error) 처리
    if response is None:
        logger.error(f"[Unhandled Exception] Path: {context['request'].path}, Method: {context['request'].method}, Error: {exc}", exc_info=True)
        return Response(
            {'detail': '서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 예상된 예외 (4xx) 처리 및 로깅
    if response.status_code >= 400 and response.status_code < 500:
        logger.warning(f"[Client Error] Path: {context['request'].path}, Method: {context['request'].method}, Status: {response.status_code}, Detail: {response.data}")

    return response
```

이 전략을 통해 `DN_solution` 프로젝트는 높은 수준의 유지보수성과 안정성을 확보할 수 있을 것입니다.

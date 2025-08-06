# 개발 실천 가이드라인 (Development Practices Guidelines)

이 문서는 `DN_solution` 프로젝트의 모든 코드 작성 및 개발 과정에 적용되는 핵심 원칙과 가이드라인을 정의합니다. 코드의 품질, 유지보수성, 확장성, 협업 효율성, 그리고 시스템의 안정성을 극대화하는 것을 목표로 합니다. 모든 코드 작성자(인간 개발자 및 AI 코드 생성 도구 포함)는 이 원칙을 준수해야 합니다.

## 1. 핵심 코딩 원칙

### 1.1. 단일 책임 원칙 (Single Responsibility Principle - SRP)

*   **원칙:** 모든 클래스, 모듈 또는 함수는 단 하나의, 명확하게 정의된 책임만을 가져야 합니다. 즉, 변경될 이유가 오직 하나여야 합니다.
*   **적용:**
    *   함수는 하나의 작업을 수행하고, 그 작업에 대한 결과만을 반환해야 합니다.
    *   클래스는 특정 데이터 또는 기능 집합에 대한 단일 책임을 가져야 합니다.
    *   예: `Company` 모델은 업체 정보 관리 책임, `CompanySerializer`는 업체 데이터 직렬화/역직렬화 책임, `CompanyViewSet`은 업체 관련 API 엔드포인트 처리 책임.

### 1.2. 디자인 패턴 활용 (Gang of Four - GoF Patterns)

*   **원칙:** 검증된 디자인 패턴을 적절히 활용하여 일반적인 소프트웨어 설계 문제를 해결하고, 코드의 구조를 표준화하며, 재사용성을 높입니다.
*   **적용:**
    *   Django의 MVT(Model-View-Template) 패턴은 이미 적용된 구조적 패턴입니다.
    *   DRF의 `ViewSet`과 `Serializer`는 각각 Command 패턴과 Adapter/Strategy 패턴의 개념을 내포합니다.
    *   필요에 따라 Factory, Builder, Strategy, Observer 등 다른 GoF 패턴을 적용하여 복잡한 로직을 단순화하고 확장성을 확보합니다.

### 1.3. 애자일(Agile) 개발 방법론 준수

*   **원칙:** 유연하고 반복적인 개발을 통해 변화에 빠르게 대응하고, 지속적인 개선을 추구합니다.
*   **적용:**
    *   작은 단위의 기능 구현 및 테스트를 반복합니다.
    *   코드 리뷰를 통해 지속적으로 품질을 개선합니다.
    *   요구사항 변경에 유연하게 대응할 수 있는 코드 구조를 유지합니다.

### 1.4. JWT 기반 보안 시스템

*   **JWT 인증 구현:** 클라우드 환경에 최적화된 JWT (JSON Web Token) 기반 상태 비저장 인증 시스템을 구현했습니다.
*   **이중 인증 메커니즘:** Django User와 CompanyUser 모델을 분리하여 시스템 접근과 업무 권한을 이중으로 검증합니다.
*   **토큰 보안 강화:**
    *   `CustomTokenObtainPairSerializer`를 통한 승인 상태 검증
    *   Access Token 및 Refresh Token의 적절한 만료 시간 설정
    *   토큰에 최소한의 필수 정보만 포함하여 보안 위험 최소화
*   **CORS 설정:** `django-cors-headers`를 통한 안전한 크로스 도메인 통신 지원

*   **보안 체크리스트 (현재 적용 완료):**
    *   [✓] 모든 ViewSet에 JWT 인증 적용
    *   [✓] 계층적 권한 제어 시스템 구현  
    *   [✓] 이중 사용자 검증 시스템 (Django User + CompanyUser)
    *   [✓] 환경 변수를 통한 민감 정보 관리
    *   [✓] CORS 보안 설정
    *   [ ] HTTPS 적용 (운영 환경 배포 시)

## 2. 클린 코드 (Clean Code) 규칙

### 2.1. 명확하고 의도적인 이름 지정

*   **원칙:** 변수, 함수, 클래스, 모듈 등 모든 식별자는 그 목적과 역할을 명확하게 드러내도록 이름을 지정해야 합니다.
*   **적용:**
    *   함수명은 동사+명사 형태로 `get_company_list()`, `create_company_user()`, `toggle_status()`와 같이 동작을 명확히 나타냅니다.
    *   변수명은 `company_name`, `user_role`, `parent_company_id`와 같이 데이터의 의미를 명확히 나타냅니다.
    *   약어 사용은 지양하며, 보편적으로 통용되는 약어(예: `id`, `API`)만 허용합니다.

### 2.2. 주석 활용 (Why, Not What)

*   **원칙:** 주석은 코드의 `무엇(What)`이 아닌 `왜(Why)` 그렇게 작성되었는지, `어떤 원리`로 동작하는지, 그리고 `어떤 다른 기능/함수와 연결`되는지를 설명하는 데 사용합니다.
*   **적용:**
    *   복잡한 로직, 비즈니스 규칙, 특정 디자인 결정에 대한 설명을 주석으로 남깁니다.
    *   함수나 클래스의 시작 부분에 해당 기능의 목적, 입력, 출력, 주요 동작 원리를 간략하게 설명합니다.
    *   다른 모듈이나 기능과의 중요한 연결점(예: 특정 API 호출, 데이터 흐름)을 명시합니다.
    *   코드 자체로 명확한 부분에는 불필요한 주석을 달지 않습니다.

### 2.3. 로직의 단순화 및 복잡성 제한

*   **원칙:** 코드는 가능한 한 단순하고 이해하기 쉬워야 합니다. 복잡성을 줄여 오류 발생 가능성을 낮추고 유지보수성을 높입니다.
*   **적용:**
    *   함수 길이는 짧게 유지하고, 하나의 함수가 너무 많은 일을 하지 않도록 합니다.
    *   중첩된 조건문(if/else)이나 반복문은 최소화하고, 필요시 함수로 분리하여 가독성을 높입니다.
    *   매직 넘버(Magic Number)나 매직 스트링(Magic String) 사용을 지양하고, 상수로 정의하여 사용합니다.
    *   불필요한 추상화나 과도한 일반화는 피하고, 현재 요구사항을 명확하게 해결하는 데 집중합니다.

## 3. 로깅 전략 (Logging Strategy)

모든 시스템의 동작 과정, 내부 상태 변화, 외부 시스템과의 통신 내용을 상세하게 기록하여 시스템의 흐름을 추적하고 문제 발생 시 원인을 신속하게 파악할 수 있도록 합니다.

### 3.1. 로깅의 목적

*   **문제 진단 및 디버깅:** 오류 발생 시 정확한 원인과 발생 지점을 파악합니다.
*   **시스템 상태 모니터링:** 시스템의 정상 작동 여부, 성능 병목 현상 등을 지속적으로 감시합니다.
*   **비즈니스 흐름 추적:** 특정 요청이 시스템 내에서 어떻게 처리되었는지 전체 과정을 파악합니다.
*   **보안 감사:** 비정상적인 접근 시도나 데이터 변경 이력을 기록하여 보안 위협에 대응합니다.
*   **유지보수성 향상:** 코드 변경 없이도 시스템의 동작을 이해하고 분석할 수 있는 정보를 제공합니다.

### 3.2. 로깅 레벨 활용

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

### 3.3. 로깅 내용의 상세화

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

### 3.4. 테스트 코드 실행 시 로깅 파악

테스트 코드를 실행할 때도 실제 애플리케이션과 동일한 로깅 설정이 적용되어야 합니다. 이를 통해 테스트 과정에서 발생하는 모든 내부 동작, 데이터 흐름, 예외 처리 등을 로그로 상세하게 파악할 수 있습니다.

*   **문제점:** Django의 `TestCase`나 `APITestCase`는 기본적으로 테스트 데이터베이스를 사용하고, 로깅 설정이 실제 애플리케이션과 다르게 동작할 수 있습니다. 특히, 테스트 실행 시 콘솔에 모든 로그가 출력되지 않아 디버깅이 어려울 수 있습니다.
*   **해결 방안:**
    *   **테스트 로깅 설정:** `settings.py`에 테스트 환경을 위한 별도의 로깅 설정을 추가하거나, `test_settings.py`와 같은 파일을 만들어 테스트 실행 시 해당 설정을 로드하도록 합니다.
    *   **콘솔 핸들러 활성화:** 테스트 실행 시 `DEBUG` 레벨 이상의 모든 로그가 콘솔에 출력되도록 `logging.StreamHandler`를 설정합니다.
    *   **파일 핸들러 추가:** 필요하다면 테스트 실행 중 발생하는 로그를 별도의 파일로 저장하도록 `logging.FileHandler`를 설정합니다.
    *   **예시 (settings.py 또는 test_settings.py에 추가):**
        ```python
        # LOGGING 설정 예시 (테스트 환경용)
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                    'style': '{',
                },
                'simple': {
                    'format': '{levelname} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple' # 또는 'verbose'
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.FileHandler',
                    'filename': './test_debug.log',
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'django': {
                    'handlers': ['console', 'file'],
                    'level': 'INFO',
                    'propagate': False,
                },
                'companies': { # 특정 앱 로거
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG', # 테스트 시 상세 로그 확인을 위해 DEBUG 레벨로 설정
                    'propagate': False,
                },
                # 다른 앱 로거들도 필요에 따라 추가
                '': { # 루트 로거 (모든 로그를 처리)
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': False,
                },
            },
        }
        ```
    *   **테스트 실행:** `python manage.py test --settings=hb_admin.test_settings companies.tests` (만약 별도의 테스트 설정 파일을 사용한다면).

## 4. 엣지 케이스 및 예외 처리 (Edge Cases and Exception Handling)

시스템의 안정성과 사용자 경험을 보장하기 위해 예상치 못한 상황(엣지 케이스)과 오류(예외)를 체계적으로 처리해야 합니다.

### 4.1. 엣지 케이스 정의 및 처리

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

### 4.2. 예외 처리 (Exception Handling)

예상치 못한 오류(런타임 에러)가 발생했을 때 시스템이 비정상적으로 종료되거나 사용자에게 불친절한 메시지를 노출하는 것을 방지합니다.

*   **`try-except` 블록 활용:** 오류가 발생할 수 있는 코드 블록을 `try`로 감싸고, 예상되는 예외를 `except`로 처리합니다.
*   **구체적인 예외 처리:** `Exception`과 같은 일반적인 예외보다는 `DoesNotExist`, `ValidationError`, `IntegrityError` 등 구체적인 예외 타입을 명시하여 처리합니다.
*   **오류 로깅:** 예외 발생 시 반드시 `ERROR` 레벨로 상세한 로그를 기록합니다. `exc_info=True` 옵션을 사용하여 스택 트레이스(Stack Trace)를 함께 기록하여 문제 진단에 필요한 모든 정보를 확보합니다.
*   **사용자 친화적인 메시지:** 내부적인 오류 메시지를 사용자에게 직접 노출하지 않고, 일반적이고 이해하기 쉬운 오류 메시지를 반환합니다.
*   **우아한 실패 (Graceful Degradation):** 가능한 경우, 오류가 발생하더라도 시스템의 다른 부분이 계속 작동하도록 설계합니다.
*   **재시도 로직:** 외부 시스템과의 통신 실패와 같이 일시적인 오류의 경우, 재시도(Retry) 로직을 고려할 수 있습니다.

### 4.3. 중앙 집중식 오류 처리 (DRF)

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

이 가이드라인은 `DN_solution` 프로젝트의 성공적인 개발과 지속적인 성장을 위한 기반이 될 것입니다. 모든 기여자는 이 원칙을 숙지하고 실천해야 합니다.

# 5. API 엔드포인트

## 🔌 DN_SOLUTION2 API 엔드포인트

### 5.1 인증 및 사용자 관리

#### 5.1.1 인증 API
```
POST /api/auth/login/ - 로그인
POST /api/auth/logout/ - 로그아웃
POST /api/auth/refresh/ - 토큰 갱신
POST /api/companies/signup/ - 통합 회원가입
GET /api/companies/profile/ - 프로필 조회
PUT /api/companies/profile/ - 프로필 수정
```

#### 5.1.2 로그인 API 상세
```python
# POST /api/auth/login/
{
    "username": "bon_admin",
    "password": "password123"
}

# 응답
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_info": {
        "id": "89a73d07-4a46-4d8f-a463-d633696037bb",
        "company_id": "38c6c60f-6588-4029-9448-656e63707fd0",
        "company_name": "본사_test",
        "company_type": "headquarters",
        "role": "admin",
        "username": "bon_admin",
        "email": "admin@skthq.com",
        "phone": "010-1234-5678",
        "status": "approved",
        "is_approved": true
    }
}
```

#### 5.1.3 회원가입 API 상세
```python
# POST /api/companies/signup/
{
    "user_type": "headquarters",  # headquarters, agency, retail
    "parent_company_code": "HQ20241207123456ABCD",  # 본사 제외
    "company": {
        "name": "SKT 본사",
        "business_number": "123-45-67890",
        "address": "서울시 강남구...",
        "contact_number": "02-1234-5678"
    },
    "admin": {
        "username": "hq_admin",
        "password": "password123",
        "email": "admin@skthq.com",
        "contact_name": "김본사",
        "contact_phone": "010-1234-5678"
    }
}

# 응답
{
    "success": true,
    "company_code": "HQ20241207123456ABCD",
    "message": "회원가입이 완료되었습니다. 승인 후 로그인이 가능합니다."
}
```

### 5.2 업체 관리

#### 5.2.1 업체 관리 API
```
GET /api/companies/ - 업체 목록
POST /api/companies/ - 업체 생성
GET /api/companies/{id}/ - 업체 상세
PUT /api/companies/{id}/ - 업체 수정
DELETE /api/companies/{id}/ - 업체 삭제
GET /api/companies/my-company/ - 내 업체 정보
GET /api/companies/hierarchy/{company_id}/ - 계층 구조 조회
GET /api/companies/subordinates/{company_id}/ - 하위 업체 목록
```

#### 5.2.2 업체 목록 API 상세
```python
# GET /api/companies/
# Query Parameters
{
    "type": "headquarters",  # headquarters, agency, retail
    "status": "active",      # active, inactive
    "search": "SKT",         # 검색어
    "page": 1,
    "page_size": 20
}

# 응답
{
    "count": 150,
    "next": "http://localhost:8000/api/companies/?page=2",
    "previous": null,
    "results": [
        {
            "id": "38c6c60f-6588-4029-9448-656e63707fd0",
            "code": "HQ20241207123456ABCD",
            "name": "SKT 본사",
            "type": "headquarters",
            "parent_company": null,
            "business_number": "123-45-67890",
            "address": "서울시 강남구...",
            "contact_number": "02-1234-5678",
            "status": true,
            "rebate_balance": 0,
            "created_at": "2024-12-07T12:34:56Z"
        }
    ]
}
```

#### 5.2.3 계층 구조 조회 API 상세
```python
# GET /api/companies/hierarchy/{company_id}/
# 응답
{
    "company": {
        "id": "38c6c60f-6588-4029-9448-656e63707fd0",
        "name": "SKT 본사",
        "type": "headquarters"
    },
    "hierarchy": {
        "agencies": [
            {
                "id": "agency-1",
                "name": "SKT 협력사 A",
                "type": "agency",
                "retailers": [
                    {
                        "id": "retailer-1",
                        "name": "판매점 A-1",
                        "type": "retail"
                    },
                    {
                        "id": "retailer-2",
                        "name": "판매점 A-2",
                        "type": "retail"
                    }
                ]
            }
        ]
    }
}
```

### 5.3 정책 관리

#### 5.3.1 정책 관리 API
```
GET /api/policies/ - 정책 목록
POST /api/policies/step1/ - 1단계: 업체 선택
POST /api/policies/step2/ - 2단계: 주문서 양식
POST /api/policies/step3/ - 3단계: 리베이트 설정
POST /api/policies/step4/ - 4단계: 계약 조건
POST /api/policies/step5/ - 5단계: 정책 활성화
GET /api/policies/{id}/ - 정책 상세
PUT /api/policies/{id}/ - 정책 수정
DELETE /api/policies/{id}/ - 정책 삭제
GET /api/policies/my-policies/ - 내가 생성한 정책
GET /api/policies/assigned-policies/ - 배정받은 정책
```

#### 5.3.2 정책 생성 1단계 API 상세
```python
# POST /api/policies/step1/
{
    "selected_companies": [
        "agency-1",
        "agency-2"
    ],
    "group_name": "SKT 갤럭시 S25 프로모션 그룹",
    "description": "SKT 갤럭시 S25 프로모션을 위한 정책 그룹"
}

# 응답
{
    "success": true,
    "policy_group_id": "policy-group-1",
    "selected_companies_count": 2,
    "message": "업체 그룹이 생성되었습니다."
}
```

#### 5.3.3 정책 생성 2단계 API 상세
```python
# POST /api/policies/step2/
{
    "policy_group_id": "policy-group-1",
    "form_fields": [
        {
            "field_id": "customer_name",
            "is_required": true,
            "order_index": 1,
            "default_value": ""
        },
        {
            "field_id": "customer_phone",
            "is_required": true,
            "order_index": 2,
            "default_value": ""
        },
        {
            "field_id": "telecom_provider",
            "is_required": true,
            "order_index": 3,
            "default_value": "SKT"
        }
    ]
}

# 응답
{
    "success": true,
    "form_fields_count": 3,
    "message": "주문서 양식이 설정되었습니다."
}
```

#### 5.3.4 정책 생성 3단계 API 상세
```python
# POST /api/policies/step3/
{
    "policy_group_id": "policy-group-1",
    "rebates": [
        {
            "telecom_provider_id": "skt-provider",
            "plan_category": "10K 이상",
            "rebate_amount": 200000
        },
        {
            "telecom_provider_id": "skt-provider",
            "plan_category": "8K",
            "rebate_amount": 160000
        },
        {
            "telecom_provider_id": "kt-provider",
            "plan_category": "10K 이상",
            "rebate_amount": 180000
        }
    ]
}

# 응답
{
    "success": true,
    "rebates_count": 3,
    "message": "리베이트가 설정되었습니다."
}
```

#### 5.3.5 정책 생성 4단계 API 상세
```python
# POST /api/policies/step4/
{
    "policy_group_id": "policy-group-1",
    "contract_terms": {
        "min_contract_days": 24,
        "penalty_amount": 50000,
        "auto_renewal": true,
        "cancellation_notice_days": 30
    }
}

# 응답
{
    "success": true,
    "message": "계약 조건이 설정되었습니다."
}
```

#### 5.3.6 정책 생성 5단계 API 상세
```python
# POST /api/policies/step5/
{
    "policy_group_id": "policy-group-1",
    "policy_name": "SKT 갤럭시 S25 프로모션",
    "description": "SKT 갤럭시 S25 프로모션을 위한 정책",
    "type": "individual"
}

# 응답
{
    "success": true,
    "policy_id": "policy-1",
    "message": "정책이 성공적으로 생성되었습니다."
}
```

### 5.4 주문 관리

#### 5.4.1 주문 관리 API
```
GET /api/orders/ - 주문 목록
POST /api/orders/ - 주문 생성
GET /api/orders/{id}/ - 주문 상세
PUT /api/orders/{id}/ - 주문 수정
DELETE /api/orders/{id}/ - 주문 삭제
POST /api/orders/{id}/status/ - 상태 변경
POST /api/orders/{id}/tracking/ - 운송장번호 입력
GET /api/orders/excel/ - 엑셀 다운로드
```

#### 5.4.2 주문 생성 API 상세
```python
# POST /api/orders/
{
    "policy_id": "policy-1",
    "selected_plan_id": "plan-1",
    "product_price_id": "product-1",
    "customer_info": {
        "customer_name": "김철수",
        "customer_phone": "010-1234-5678",
        "customer_address": "서울시 강남구...",
        "customer_email": "kim@example.com"
    },
    "shipping_info": {
        "recipient_name": "김철수",
        "shipping_address": "서울시 강남구...",
        "shipping_type": "택배",
        "is_same_address": true
    },
    "device_info": {
        "device_model": "갤럭시 S25 256G",
        "device_color": "블랙",
        "device_serial": "SN123456789"
    }
}

# 응답
{
    "success": true,
    "order_id": "order-1",
    "rebate_amount": 200000,
    "product_profit": 100000,
    "total_profit": 300000,
    "message": "주문이 성공적으로 생성되었습니다."
}
```

#### 5.4.3 주문 상태 변경 API 상세
```python
# POST /api/orders/{id}/status/
{
    "status": "approved",  # pending, approved, rejected, shipped, completed
    "memo": "승인 처리 완료"
}

# 응답
{
    "success": true,
    "order_id": "order-1",
    "new_status": "approved",
    "message": "주문 상태가 변경되었습니다."
}
```

#### 5.4.4 운송장번호 입력 API 상세
```python
# POST /api/orders/{id}/tracking/
{
    "tracking_number": "1234567890",
    "shipping_company": "CJ대한통운"
}

# 응답
{
    "success": true,
    "order_id": "order-1",
    "tracking_number": "1234567890",
    "message": "운송장번호가 입력되었습니다."
}
```

### 5.5 리베이트 관리

#### 5.5.1 리베이트 관리 API
```
GET /api/rebates/allocations/ - 할당 목록
POST /api/rebates/allocations/ - 리베이트 할당
POST /api/rebates/allocations/bulk/ - 대량 리베이트 할당
GET /api/rebates/settlements/ - 정산 목록
POST /api/rebates/settlements/ - 정산 처리
POST /api/rebates/settlements/approvals/bulk/ - 대량 정산 승인
GET /api/rebates/balance/ - 잔액 조회
```

#### 5.5.2 리베이트 할당 API 상세
```python
# POST /api/rebates/allocations/
{
    "from_company_id": "hq-company",
    "to_company_id": "agency-1",
    "allocation_amount": 5000000,
    "allocation_period_start": "2024-08-01",
    "allocation_period_end": "2024-08-31",
    "notes": "8월 리베이트 할당"
}

# 응답
{
    "success": true,
    "allocation_id": "allocation-1",
    "message": "리베이트가 성공적으로 할당되었습니다."
}
```

#### 5.5.3 대량 리베이트 할당 API 상세
```python
# POST /api/rebates/allocations/bulk/
{
    "allocations": [
        {
            "to_company_id": "agency-1",
            "allocation_amount": 5000000
        },
        {
            "to_company_id": "agency-2",
            "allocation_amount": 3000000
        }
    ],
    "allocation_period_start": "2024-08-01",
    "allocation_period_end": "2024-08-31",
    "notes": "8월 대량 리베이트 할당"
}

# 응답
{
    "success": true,
    "allocated_count": 2,
    "total_amount": 8000000,
    "message": "대량 리베이트 할당이 완료되었습니다."
}
```

#### 5.5.4 잔액 조회 API 상세
```python
# GET /api/rebates/balance/
# 응답
{
    "company_id": "agency-1",
    "total_allocated": 5000000,
    "total_used": 2000000,
    "current_balance": 3000000,
    "allocation_period": {
        "start": "2024-08-01",
        "end": "2024-08-31"
    },
    "usage_history": [
        {
            "order_id": "order-1",
            "amount": 50000,
            "used_at": "2024-08-15T10:30:00Z"
        }
    ]
}
```

### 5.6 상품 가격 관리

#### 5.6.1 상품 가격 관리 API
```
GET /api/product-prices/ - 상품 가격 목록
POST /api/product-prices/ - 상품 가격 추가
PUT /api/product-prices/{id}/ - 상품 가격 수정
DELETE /api/product-prices/{id}/ - 상품 가격 삭제
GET /api/product-prices/company/{company_id}/ - 업체별 상품 가격
```

#### 5.6.2 상품 가격 생성 API 상세
```python
# POST /api/product-prices/
{
    "company_id": "company-1",
    "product_name": "갤럭시 S25 256G",
    "product_category": "단말기",
    "purchase_price": 800000,
    "selling_price": 900000,
    "profit_margin": 100000
}

# 응답
{
    "success": true,
    "product_price_id": "product-price-1",
    "message": "상품 가격이 성공적으로 추가되었습니다."
}
```

### 5.7 엑셀 다운로드

#### 5.7.1 엑셀 다운로드 API
```
GET /api/settlements/excel/ - 정산 상세 내역 엑셀
GET /api/settlements/excel/hierarchical/ - 계층별 정산 내역 엑셀
GET /api/orders/excel/ - 주문 내역 엑셀
GET /api/rebates/excel/ - 리베이트 내역 엑셀
```

#### 5.7.2 정산 상세 내역 엑셀 API 상세
```python
# GET /api/settlements/excel/?start_date=2024-08-01&end_date=2024-08-31
# Query Parameters
{
    "start_date": "2024-08-01",
    "end_date": "2024-08-31",
    "company_id": "company-1"  # 선택사항
}

# 응답
# Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
# Content-Disposition: attachment; filename="정산내역_20241207_143022.xlsx"
# 엑셀 파일 바이너리 데이터
```

#### 5.7.3 계층별 정산 내역 엑셀 API 상세
```python
# GET /api/settlements/excel/hierarchical/?start_date=2024-08-01&end_date=2024-08-31
# Query Parameters
{
    "start_date": "2024-08-01",
    "end_date": "2024-08-31"
}

# 응답
# Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
# Content-Disposition: attachment; filename="계층별정산내역_20241207_143022.xlsx"
# 엑셀 파일 바이너리 데이터
```

### 5.8 통계 및 대시보드

#### 5.8.1 통계 API
```
GET /api/statistics/dashboard/ - 대시보드 통계
GET /api/statistics/orders/ - 주문 통계
GET /api/statistics/rebates/ - 리베이트 통계
GET /api/statistics/settlements/ - 정산 통계
```

#### 5.8.2 대시보드 통계 API 상세
```python
# GET /api/statistics/dashboard/
# 응답
{
    "period": {
        "start": "2024-08-01",
        "end": "2024-08-31"
    },
    "orders": {
        "total": 150,
        "pending": 10,
        "approved": 120,
        "shipped": 15,
        "completed": 5
    },
    "rebates": {
        "total_allocated": 20000000,
        "total_used": 12500000,
        "remaining": 7500000
    },
    "settlements": {
        "total_rebate": 12500000,
        "total_product_profit": 7500000,
        "total_settlement": 20000000
    },
    "recent_activities": [
        {
            "type": "order_created",
            "message": "새로운 주문이 생성되었습니다.",
            "timestamp": "2024-08-15T10:30:00Z"
        }
    ]
}
```

### 5.9 파일 업로드

#### 5.9.1 파일 업로드 API
```
POST /api/orders/{id}/attachments/ - 주문 첨부파일 업로드
GET /api/orders/{id}/attachments/ - 주문 첨부파일 목록
DELETE /api/orders/{id}/attachments/{attachment_id}/ - 첨부파일 삭제
```

#### 5.9.2 첨부파일 업로드 API 상세
```python
# POST /api/orders/{id}/attachments/
# Content-Type: multipart/form-data
{
    "file": <파일>,
    "file_slot": 1  # 1~4
}

# 응답
{
    "success": true,
    "attachment_id": "attachment-1",
    "file_name": "document.pdf",
    "file_size": 1024000,
    "message": "파일이 성공적으로 업로드되었습니다."
}
```

### 5.10 알림 및 메시지

#### 5.10.1 알림 API
```
GET /api/notifications/ - 알림 목록
POST /api/notifications/mark-read/ - 알림 읽음 처리
DELETE /api/notifications/{id}/ - 알림 삭제
```

#### 5.10.2 알림 목록 API 상세
```python
# GET /api/notifications/
# 응답
{
    "count": 10,
    "results": [
        {
            "id": "notification-1",
            "type": "order_created",
            "title": "새로운 주문",
            "message": "판매점 A-1에서 새로운 주문이 생성되었습니다.",
            "is_read": false,
            "created_at": "2024-08-15T10:30:00Z"
        }
    ]
}
```

### 5.11 에러 처리

#### 5.11.1 공통 에러 응답 형식
```python
# 400 Bad Request
{
    "error": "validation_error",
    "message": "입력 데이터가 올바르지 않습니다.",
    "details": {
        "field_name": ["이 필드는 필수입니다."]
    }
}

# 401 Unauthorized
{
    "error": "authentication_error",
    "message": "인증이 필요합니다."
}

# 403 Forbidden
{
    "error": "permission_error",
    "message": "권한이 없습니다."
}

# 404 Not Found
{
    "error": "not_found",
    "message": "요청한 리소스를 찾을 수 없습니다."
}

# 500 Internal Server Error
{
    "error": "server_error",
    "message": "서버 오류가 발생했습니다."
}
```

### 5.12 API 버전 관리

#### 5.12.1 버전 관리 전략
```
/api/v1/ - 현재 버전
/api/v2/ - 향후 버전 (계획)
```

#### 5.12.2 버전별 호환성
```python
# API 버전 헤더
Accept: application/vnd.dn-solution.v1+json

# 버전별 엔드포인트
GET /api/v1/companies/
GET /api/v2/companies/  # 향후 버전
```

### 5.13 API 문서화

#### 5.13.1 Swagger/OpenAPI 문서
```
GET /api/docs/ - API 문서 (Swagger UI)
GET /api/schema/ - API 스키마 (JSON)
```

#### 5.13.2 API 문서 예시
```yaml
openapi: 3.0.0
info:
  title: DN_SOLUTION2 API
  version: 1.0.0
  description: DN_SOLUTION2 시스템 API 문서
paths:
  /api/auth/login/:
    post:
      summary: 로그인
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: 로그인 성공
          content:
            application/json:
              schema:
                type: object
                properties:
                  access:
                    type: string
                  refresh:
                    type: string
                  user_info:
                    type: object
```

이 API 엔드포인트 문서는 시스템의 모든 기능을 RESTful API로 제공하는 방법을 상세하게 설명합니다.

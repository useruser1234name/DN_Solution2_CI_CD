# DN_SOLUTION2 시스템 문서

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [권한 매트릭스](#권한-매트릭스)
3. [테이블 구조](#테이블-구조)
4. [기능 흐름도](#기능-흐름도)
5. [API 엔드포인트](#api-엔드포인트)
6. [프론트엔드 구조](#프론트엔드-구조)
7. [테스트 시나리오](#테스트-시나리오)
8. [배포 가이드](#배포-가이드)

---

## 🏢 시스템 개요

### 1.1 핵심 비즈니스 모델
```
본사 (HQ) → 협력사 (Agency) → 판매점 (Retailer) → 고객 (Customer)
├── 본사: 정책 생성, 리베이트 할당, 주문 승인
├── 협력사: 리베이트 분배, 하위 판매점 관리
├── 판매점: 고객 주문 처리, 정책 선택
└── 고객: 상품 구매, 서비스 이용
```

### 1.2 주요 기능
```
✅ 계층별 업체 관리 (본사 → 협력사 → 판매점)
✅ 통합 회원가입 (업체 + 관리자 동시 생성)
✅ 동적 정책 생성 (업체 선택 → 주문서 양식 → 리베이트 설정)
✅ 통신사별 요금제 기준 리베이트 시스템
✅ 상품 가격 관리 (매입가/판매가/마진)
✅ 주문서 작성 및 승인 플로우
✅ 리베이트 할당 및 정산 시스템
✅ 엑셀 다운로드 기능
✅ 실시간 대시보드
✅ 권한 기반 접근 제어
```

---

## 🔐 권한 매트릭스

### 2.1 계층별 권한 구조

#### 2.1.1 본사 (Headquarters)
```
✅ 모든 업체 정보 조회/수정
✅ 모든 주문 정보 조회/수정
✅ 리베이트 할당/관리
✅ 정책 생성/수정/삭제
✅ 상품 가격 관리
✅ 전체 통계 조회
✅ 정산 승인
✅ 시스템 설정 관리
```

#### 2.1.2 협력사 (Agency)
```
✅ 본사 정보 조회
✅ 하위 판매점 정보 조회/수정
✅ 본사 주문 정보 조회
✅ 하위 판매점 주문 정보 조회
✅ 할당받은 리베이트 관리
✅ 하위 판매점에 리베이트 분배
✅ 상품 가격 조회
✅ 하위 판매점 정산 승인
✅ 본인 통계 조회
```

#### 2.1.3 판매점 (Retailer)
```
✅ 상위 협력사 정보 조회
✅ 본사 정보 조회
✅ 본사 주문 정보 조회
✅ 본인 주문 정보 생성/조회/수정
✅ 할당받은 리베이트 사용
✅ 상품 가격 조회
✅ 본인 정산 확인
✅ 본인 통계 조회
```

### 2.2 역할별 권한 구조

#### 2.2.1 관리자 (Admin)
```
✅ 업체 정보 관리
✅ 사용자 관리
✅ 정책 관리
✅ 주문 관리
✅ 리베이트 관리
✅ 상품 가격 관리
✅ 정산 관리
✅ 통계 조회
```

#### 2.2.2 직원 (Staff)
```
✅ 주문 생성
✅ 주문 조회
✅ 고객 정보 관리
✅ 상품 가격 조회
✅ 리베이트 잔액 확인
✅ 기본 정보 조회
```

---

## 🗄️ 테이블 구조

### 3.1 핵심 테이블 목록
```
1. companies - 업체 정보
2. company_users - 업체 사용자
3. telecom_providers - 통신사
4. plans - 요금제
5. policies - 정책
6. policy_groups - 정책 그룹
7. policy_group_assignments - 정책 그룹 배정
8. policy_rebates - 정책별 리베이트
9. product_prices - 상품 가격
10. order_form_fields - 주문서 필드
11. policy_form_fields - 정책별 주문서 필드
12. customer_orders - 고객 주문
13. order_status_logs - 주문 상태 로그
14. order_attachments - 주문 첨부파일
15. rebate_allocations - 리베이트 할당
16. rebate_settlements - 리베이트 정산
17. settlement_approvals - 정산 승인
18. settlement_summaries - 정산 요약
```

### 3.2 상세 테이블 스키마

#### 3.2.1 Company (업체) 테이블
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL, -- 업체코드 (자동생성)
    name VARCHAR(200) NOT NULL, -- 업체명
    type ENUM('headquarters', 'agency', 'retail') NOT NULL, -- 업체 타입
    parent_company_id UUID REFERENCES companies(id), -- 상위 업체 ID
    business_number VARCHAR(20), -- 사업자등록번호
    address TEXT, -- 주소
    contact_number VARCHAR(20), -- 연락처
    status BOOLEAN DEFAULT TRUE, -- 운영 상태
    rebate_balance DECIMAL(15,2) DEFAULT 0, -- 리베이트 잔액
    created_by UUID REFERENCES company_users(id), -- 생성자
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.2 CompanyUser (업체 사용자) 테이블
```sql
CREATE TABLE company_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    django_user_id INTEGER NOT NULL REFERENCES auth_user(id),
    username VARCHAR(150) NOT NULL, -- 사용자명
    role ENUM('admin', 'staff') NOT NULL DEFAULT 'staff', -- 역할
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending', -- 승인 상태
    is_approved BOOLEAN DEFAULT FALSE, -- 승인 여부
    approved_by UUID REFERENCES company_users(id), -- 승인자
    approved_at TIMESTAMP, -- 승인 일시
    is_primary_admin BOOLEAN DEFAULT FALSE, -- 최초 관리자 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.3 CustomerOrder (고객 주문) 테이블
```sql
CREATE TABLE customer_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id), -- 주문 업체
    policy_id UUID REFERENCES policies(id), -- 선택된 정책
    customer_group VARCHAR(50), -- 고객 그룹
    store VARCHAR(100), -- 판매점
    status VARCHAR(50) DEFAULT 'pending', -- 진행 상태
    activation_status VARCHAR(50), -- 개통 상태
    customer_name VARCHAR(100) NOT NULL, -- 고객명
    customer_type VARCHAR(50), -- 고객유형
    registration_number VARCHAR(20), -- 주민등록번호
    customer_address TEXT, -- 고객 주소
    customer_email VARCHAR(100), -- 고객 이메일
    customer_phone VARCHAR(20), -- 고객 연락처
    alt_contact VARCHAR(20), -- 비상연락처
    recipient_name VARCHAR(100), -- 수령인
    shipping_address TEXT, -- 수령 주소
    shipping_type VARCHAR(30), -- 배송 유형
    is_same_address BOOLEAN DEFAULT FALSE, -- 고객 주소 동일 여부
    application_code VARCHAR(50), -- 신청코드
    device_color VARCHAR(50), -- 단말기 색상
    device_model VARCHAR(100), -- 모델번호
    device_model_type VARCHAR(100), -- 유심 모델
    device_serial VARCHAR(100), -- 유심일련번호
    selected_plan_id UUID REFERENCES plans(id), -- 선택된 요금제 ID
    plan_monthly_fee INTEGER, -- 요금제 월 요금
    plan_category VARCHAR(20), -- 요금제 카테고리
    rebate_amount DECIMAL(15,2) DEFAULT 0, -- 해당 요금제 리베이트 금액
    product_price_id UUID REFERENCES product_prices(id), -- 선택된 상품 가격 ID
    product_purchase_price DECIMAL(15,2), -- 상품 매입가
    product_selling_price DECIMAL(15,2), -- 상품 판매가
    product_profit DECIMAL(15,2), -- 상품 마진
    telecom_provider VARCHAR(50), -- 가입통신사
    subscriber_type VARCHAR(50), -- 유심가입구분
    sales_person VARCHAR(100), -- 판매자명
    benefit_code VARCHAR(50), -- 혜택코드
    usage_fee DECIMAL(15,2), -- 실사용액
    payment_method VARCHAR(30), -- 납부 방법
    payment_issuer VARCHAR(50), -- 은행 또는 카드사
    account_or_card_number VARCHAR(50), -- 계좌(카드) 번호
    card_expiry DATE, -- 카드 유효기간
    depositor_name VARCHAR(100), -- 예금주명
    depositor_birth DATE, -- 예금주 생년월일
    is_same_as_customer BOOLEAN DEFAULT FALSE, -- 고객명과 동일 여부
    tracking_number VARCHAR(100), -- 운송장번호
    recent_note TEXT, -- 최근 메모
    status_manager_id UUID REFERENCES company_users(id), -- 진행 상태 담당자
    activation_manager_id UUID REFERENCES company_users(id), -- 개통 상태 담당자
    final_rebate_amount DECIMAL(15,2) DEFAULT 0, -- 최종 리베이트 금액
    created_by UUID NOT NULL REFERENCES company_users(id), -- 생성자
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 기능 흐름도

### 4.1 회원가입 플로우
```
시작: 회원가입 페이지 접속
↓
1. 회원 유형 선택
   - 본사 관리자
   - 협력사 관리자
   - 판매점 직원
↓
2. 상위 업체코드 입력 (본사 제외)
   - 본사: 상위 업체코드 입력 불필요
   - 협력사: 본사 업체코드 입력 필수
   - 판매점: 협력사 업체코드 입력 필수
↓
3. 상위 업체 정보 확인
   - 업체코드로 상위 업체 조회
   - 업체명, 타입, 상태 표시
↓
4. 업체 정보 입력
   - 업체명, 사업자등록번호, 주소, 연락처
↓
5. 관리자 정보 입력
   - 아이디, 비밀번호, 이메일, 담당자명, 연락처
↓
6. 업체코드 자동 생성
   - 협력사: "HQ20241207123456ABCD-AG20241207124500EFGH"
   - 판매점: "HQ20241207123456ABCD-AG20241207124500EFGH-RT20241207125000QRST"
↓
7. 통합 생성 처리
   - Company 테이블에 업체 정보 저장
   - CompanyUser 테이블에 관리자 정보 저장
   - 계층 관계 설정
   - 승인 대기 상태로 설정
↓
8. 업체코드 표시
   - "업체코드: HQ20241207123456ABCD-AG20241207124500EFGH"
   - "이 업체코드를 안전한 곳에 보관하세요"
↓
9. 승인 대기
   - 상태: 'pending'
   - 승인자: 상위 계층 관리자
↓
10. 승인 처리
    - 상위 계층에서 승인
    - 상태: 'approved'
    - 로그인 가능
↓
완료: 업체와 관리자가 동시에 생성되어 시스템 이용 가능
```

### 4.2 정책 생성 플로우
```
본사 관리자
↓
1단계: 업체 그룹 선택
   - 협력사 목록에서 체크박스로 선택
   - 선택된 협력사와 하위 판매점 그룹화
↓
2단계: 주문서 양식 작성
   - 미리 정의된 항목들 중에서 선택
   - 필수/선택 항목 구분
   - 드롭다운/직접입력 설정
↓
3단계: 리베이트 설정
   - SKT 요금제별 리베이트 (10K 이상: 200,000원)
   - KT 요금제별 리베이트 (10K 이상: 180,000원)
   - LGU 요금제별 리베이트 (10K 이상: 160,000원)
↓
4단계: 계약 조건 설정
   - 최소 계약 유지일: 24개월
   - 위약금: 50,000원
   - 기타 조건 설정
↓
5단계: 정책 활성화
   - 선택된 업체들에게 정책 배정
   - 주문서 양식 생성
   - 정책 활성화
```

### 4.3 주문 처리 플로우
```
판매점 직원
↓
1. 정책 선택
   - "SKT 갤럭시 S25 프로모션" 선택
↓
2. 요금제 선택
   - "5G 프리미엄 10K" 선택
   - 리베이트: 200,000원 자동 계산
↓
3. 상품 선택
   - "갤럭시 S25 256G" 선택
   - 매입가: 800,000원
   - 판매가: 900,000원
   - 마진: 100,000원
↓
4. 고객 정보 입력
   - 고객명, 연락처, 주소 등
↓
5. 최종 계산
   - 상품 마진: 100,000원
   - 리베이트: 200,000원
   - 총 수익: 300,000원
↓
6. 주문서 제출
   - 본사로 주문서 전송
   - 상태: "접수"
↓
본사 관리자
↓
7. 주문서 검토
   - 고객 정보 확인
   - 정책 조건 확인
   - 승인/반려 결정
↓
8. 상품 발송
   - 운송장번호 입력
   - 상태: "발송완료"
↓
9. 리베이트 정산
   - 상품 마진 + 리베이트 계산
   - 최종 정산 금액 계산
```

### 4.4 리베이트 할당 플로우
```
본사 (HQ)
↓
1. 협력사에 총 리베이트 할당
   - 협력사 A: 500,000원
   - 협력사 B: 300,000원
↓
협력사 (Agency)
↓
2. 할당받은 금액을 판매점에 분배
   - 판매점 A-1: 200,000원
   - 판매점 A-2: 150,000원
   - 협력사 A 잔액: 150,000원
↓
판매점 (Retailer)
↓
3. 주문 시 리베이트 사용
   - 주문 1: 50,000원 사용
   - 주문 2: 30,000원 사용
   - 잔액: 120,000원
```

### 4.5 정산 승인 플로우
```
본사 관리자
↓
1. 정산 승인 페이지 접속
↓
2. 정산 기간 선택
   - 시작일: 2024-08-01
   - 종료일: 2024-08-31
   - 기간: 31일
↓
3. 정산 대상 조회
   - 총 주문: 150건
   - 총 리베이트 사용: 12,500,000원
   - 총 상품 마진: 7,500,000원
   - 총 정산 금액: 20,000,000원
↓
4. 정산 내역 확인
   ├── 협력사1: 5,000,000원 (50건)
   ├── 협력사2: 4,000,000원 (40건)
   ├── 협력사3: 3,500,000원 (35건)
   └── 협력사4: 3,000,000원 (25건)
↓
5. 전체 선택 → 정산 승인
   - 정산 상태: 'pending' → 'approved'
   - 정산 일시 기록
   - 정산 완료 알림 발송
↓
완료: 선택된 기간의 정산이 승인되어 최종 처리됨
```

---

## 🔌 API 엔드포인트

### 5.1 인증 및 사용자 관리
```
POST /api/auth/login/ - 로그인
POST /api/auth/logout/ - 로그아웃
POST /api/auth/refresh/ - 토큰 갱신
POST /api/companies/signup/ - 통합 회원가입
GET /api/companies/profile/ - 프로필 조회
PUT /api/companies/profile/ - 프로필 수정
```

### 5.2 업체 관리
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

### 5.3 정책 관리
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

### 5.4 주문 관리
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

### 5.5 리베이트 관리
```
GET /api/rebates/allocations/ - 할당 목록
POST /api/rebates/allocations/ - 리베이트 할당
POST /api/rebates/allocations/bulk/ - 대량 리베이트 할당
GET /api/rebates/settlements/ - 정산 목록
POST /api/rebates/settlements/ - 정산 처리
POST /api/rebates/settlements/approvals/bulk/ - 대량 정산 승인
GET /api/rebates/balance/ - 잔액 조회
```

### 5.6 상품 가격 관리
```
GET /api/product-prices/ - 상품 가격 목록
POST /api/product-prices/ - 상품 가격 추가
PUT /api/product-prices/{id}/ - 상품 가격 수정
DELETE /api/product-prices/{id}/ - 상품 가격 삭제
GET /api/product-prices/company/{company_id}/ - 업체별 상품 가격
```

### 5.7 엑셀 다운로드
```
GET /api/settlements/excel/ - 정산 상세 내역 엑셀
GET /api/settlements/excel/hierarchical/ - 계층별 정산 내역 엑셀
GET /api/orders/excel/ - 주문 내역 엑셀
GET /api/rebates/excel/ - 리베이트 내역 엑셀
```

---

## 🎨 프론트엔드 구조

### 6.1 페이지 구조
```
/login - 로그인
/signup - 통합 회원가입
/forgot-password - 비밀번호 찾기
/dashboard - 메인 대시보드
/statistics - 통계 페이지
/companies - 업체 목록
/companies/create - 업체 생성
/companies/{id} - 업체 상세
/companies/{id}/edit - 업체 수정
/policies - 정책 목록
/policies/create - 정책 생성 (단계별)
/policies/{id} - 정책 상세
/policies/{id}/edit - 정책 수정
/orders - 주문 목록
/orders/create - 주문 생성
/orders/{id} - 주문 상세
/orders/{id}/edit - 주문 수정
/rebates - 리베이트 관리
/rebates/allocations - 할당 관리
/rebates/settlements - 정산 관리
/product-prices - 상품 가격 관리
/product-prices/create - 상품 가격 추가
/product-prices/{id}/edit - 상품 가격 수정
```

### 6.2 컴포넌트 구조
```
src/
├── components/
│   ├── ProtectedRoute.js - 권한 기반 라우트
│   ├── Sidebar.js - 사이드바
│   ├── ExcelDownload.js - 엑셀 다운로드
│   ├── SettlementSummary.js - 정산 요약
│   ├── OrderSummary.js - 주문 요약
│   ├── RebateSummary.js - 리베이트 요약
│   └── HierarchicalSettlement.js - 계층별 정산
├── pages/
│   ├── LoginPage.js - 로그인
│   ├── SignupPage.js - 회원가입
│   ├── DashboardPage.js - 대시보드
│   ├── CompanyListPage.js - 업체 목록
│   ├── PolicyListPage.js - 정책 목록
│   ├── OrderListPage.js - 주문 목록
│   └── RebatePage.js - 리베이트 관리
├── features/
│   ├── auth/
│   │   └── authSlice.js - 인증 상태 관리
│   ├── policies/
│   │   └── policySlice.js - 정책 상태 관리
│   └── orders/
│       └── orderSlice.js - 주문 상태 관리
├── services/
│   └── api.js - API 통신
└── utils/
    ├── permissions.js - 권한 관리
    └── formatters.js - 데이터 포맷팅
```

---

## 🧪 테스트 시나리오

### 7.1 회원가입 테스트

#### 7.1.1 본사 회원가입
```
시나리오: 본사 관리자 회원가입
전제조건: 시스템에 본사가 없음

단계:
1. 회원가입 페이지 접속
2. 회원 유형 "본사 관리자" 선택
3. 업체 정보 입력
   - 업체명: "SKT 본사"
   - 사업자등록번호: "123-45-67890"
   - 주소: "서울시 강남구..."
   - 연락처: "02-1234-5678"
4. 관리자 정보 입력
   - 아이디: "hq_admin"
   - 비밀번호: "password123"
   - 이메일: "admin@skthq.com"
   - 담당자명: "김본사"
   - 연락처: "010-1234-5678"
5. 회원가입 완료

예상 결과:
- 업체코드 자동 생성: "HQ20241207123456ABCD"
- 상태: 'approved' (본사는 자동 승인)
- 로그인 가능
- 본사 권한 부여
```

#### 7.1.2 협력사 회원가입
```
시나리오: 협력사 관리자 회원가입
전제조건: 본사가 존재함

단계:
1. 회원가입 페이지 접속
2. 회원 유형 "협력사 관리자" 선택
3. 상위 업체코드 입력: "HQ20241207123456ABCD"
4. 상위 업체 정보 확인
5. 업체 정보 입력
   - 업체명: "SKT 협력사 A"
   - 사업자등록번호: "234-56-78901"
   - 주소: "서울시 서초구..."
   - 연락처: "02-2345-6789"
6. 관리자 정보 입력
   - 아이디: "agency_admin"
   - 비밀번호: "password123"
   - 이메일: "admin@sktagency.com"
   - 담당자명: "이협력사"
   - 연락처: "010-2345-6789"
7. 회원가입 완료

예상 결과:
- 업체코드 자동 생성: "HQ20241207123456ABCD-AG20241207124500EFGH"
- 상태: 'pending'
- 본사 승인 대기
- 승인 후 로그인 가능
```

#### 7.1.3 판매점 회원가입
```
시나리오: 판매점 직원 회원가입
전제조건: 협력사가 존재함

단계:
1. 회원가입 페이지 접속
2. 회원 유형 "판매점 직원" 선택
3. 상위 업체코드 입력: "HQ20241207123456ABCD-AG20241207124500EFGH"
4. 상위 업체 정보 확인
5. 업체 정보 입력
   - 업체명: "판매점 A-1"
   - 사업자등록번호: "345-67-89012"
   - 주소: "서울시 강남구..."
   - 연락처: "02-3456-7890"
6. 관리자 정보 입력
   - 아이디: "retail_admin"
   - 비밀번호: "password123"
   - 이메일: "admin@sktretail.com"
   - 담당자명: "박판매점"
   - 연락처: "010-3456-7890"
7. 회원가입 완료

예상 결과:
- 업체코드 자동 생성: "HQ20241207123456ABCD-AG20241207124500EFGH-RT20241207125000QRST"
- 상태: 'pending'
- 협력사 승인 대기
- 승인 후 로그인 가능
```

### 7.2 정책 생성 테스트

#### 7.2.1 정책 생성 (본사)
```
시나리오: 본사에서 정책 생성
전제조건: 본사 관리자 로그인됨

단계:
1. 정책 관리 페이지 접속
2. "정책 생성" 버튼 클릭
3. 1단계: 업체 그룹 선택
   - 협력사 A 체크박스 선택
   - 협력사 B 체크박스 선택
4. 2단계: 주문서 양식 작성
   - 고객명 (필수) 선택
   - 연락처 (필수) 선택
   - 통신사 (필수) 선택
   - 요금제 (필수) 선택
5. 3단계: 리베이트 설정
   - SKT 10K 이상: 200,000원
   - KT 10K 이상: 180,000원
   - LGU 10K 이상: 160,000원
6. 4단계: 계약 조건 설정
   - 최소 계약일: 24개월
   - 위약금: 50,000원
7. 5단계: 정책 활성화
   - 정책명: "SKT 갤럭시 S25 프로모션"
   - 활성화 완료

예상 결과:
- 정책 생성 완료
- 선택된 협력사와 판매점에 정책 배정
- 주문서 양식 생성
- 리베이트 설정 완료
```

### 7.3 주문 처리 테스트

#### 7.3.1 주문 생성 (판매점)
```
시나리오: 판매점에서 주문 생성
전제조건: 판매점 직원 로그인됨, 정책이 배정됨

단계:
1. 주문 관리 페이지 접속
2. "주문 생성" 버튼 클릭
3. 정책 선택
   - "SKT 갤럭시 S25 프로모션" 선택
4. 요금제 선택
   - "5G 프리미엄 10K" 선택
   - 리베이트: 200,000원 자동 계산
5. 상품 선택
   - "갤럭시 S25 256G" 선택
   - 매입가: 800,000원
   - 판매가: 900,000원
   - 마진: 100,000원
6. 고객 정보 입력
   - 고객명: "김철수"
   - 연락처: "010-1234-5678"
   - 주소: "서울시 강남구..."
7. 주문서 제출

예상 결과:
- 주문 생성 완료
- 상태: "접수"
- 본사로 전송
- 리베이트 차감
- 정산 정보 생성
```

#### 7.3.2 주문 승인 (본사)
```
시나리오: 본사에서 주문 승인
전제조건: 본사 관리자 로그인됨, 주문이 접수됨

단계:
1. 주문 관리 페이지 접속
2. 접수된 주문 목록 확인
3. 주문 상세 조회
   - 고객 정보 확인
   - 정책 조건 확인
   - 리베이트 정보 확인
4. 승인 처리
   - "승인" 버튼 클릭
5. 운송장번호 입력
   - 운송장번호: "1234567890"
6. 발송 완료

예상 결과:
- 주문 상태: "승인" → "발송완료"
- 운송장번호 입력 완료
- 정산 처리 완료
- 판매점에 알림 발송
```

### 7.4 리베이트 할당 테스트

#### 7.4.1 리베이트 할당 (본사)
```
시나리오: 본사에서 협력사에 리베이트 할당
전제조건: 본사 관리자 로그인됨

단계:
1. 리베이트 관리 페이지 접속
2. "리베이트 할당" 버튼 클릭
3. 할당 기간 설정
   - 시작일: 2024-08-01
   - 종료일: 2024-08-31
4. 협력사 선택
   - 협력사 A 체크박스 선택
   - 협력사 B 체크박스 선택
5. 할당 금액 입력
   - 협력사 A: 5,000,000원
   - 협력사 B: 3,000,000원
6. 할당 처리

예상 결과:
- 리베이트 할당 완료
- 협력사 잔액 업데이트
- 협력사에게 알림 발송
- 할당 기간 설정 완료
```

#### 7.4.2 리베이트 분배 (협력사)
```
시나리오: 협력사에서 판매점에 리베이트 분배
전제조건: 협력사 관리자 로그인됨, 리베이트 할당됨

단계:
1. 리베이트 관리 페이지 접속
2. 할당받은 리베이트 확인
   - 할당 금액: 5,000,000원
   - 사용 가능 금액: 5,000,000원
3. 판매점 선택 및 분배
   - 판매점 A-1: 2,000,000원
   - 판매점 A-2: 1,500,000원
   - 판매점 A-3: 1,000,000원
4. 분배 처리

예상 결과:
- 리베이트 분배 완료
- 판매점 잔액 업데이트
- 판매점에게 알림 발송
- 잔여 금액: 500,000원
```

### 7.5 정산 승인 테스트

#### 7.5.1 정산 승인 (본사)
```
시나리오: 본사에서 정산 승인
전제조건: 본사 관리자 로그인됨, 주문이 완료됨

단계:
1. 정산 관리 페이지 접속
2. 정산 기간 설정
   - 시작일: 2024-08-01
   - 종료일: 2024-08-31
3. 정산 대상 조회
   - 총 주문: 150건
   - 총 리베이트 사용: 12,500,000원
   - 총 상품 마진: 7,500,000원
   - 총 정산 금액: 20,000,000원
4. 정산 내역 확인
   - 협력사별 정산 내역 확인
5. 전체 선택 → 정산 승인

예상 결과:
- 정산 승인 완료
- 정산 상태: 'approved'
- 정산 일시 기록
- 정산 완료 알림 발송
```

### 7.6 엑셀 다운로드 테스트

#### 7.6.1 정산 내역 엑셀 다운로드
```
시나리오: 정산 내역 엑셀 다운로드
전제조건: 사용자 로그인됨, 정산 데이터 존재

단계:
1. 대시보드 접속
2. 엑셀 다운로드 섹션 확인
3. 기간 선택
   - 시작일: 2024-08-01
   - 종료일: 2024-08-31
4. "정산 상세 내역 다운로드" 버튼 클릭
5. 파일 다운로드 확인

예상 결과:
- 엑셀 파일 다운로드 완료
- 파일명: "정산내역_20241207_143022.xlsx"
- 정산 상세 내역 포함
- 스타일링된 엑셀 파일
```

---

## 🚀 배포 가이드

### 8.1 개발 환경 설정

#### 8.1.1 백엔드 설정
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 초기 데이터 생성
python manage.py loaddata initial_data.json

# 개발 서버 실행
python manage.py runserver
```

#### 8.1.2 프론트엔드 설정
```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm start

# 빌드
npm run build
```

### 8.2 프로덕션 배포

#### 8.2.1 서버 요구사항
```
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis 6+
- Nginx
```

#### 8.2.2 환경 변수 설정
```bash
# .env 파일
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/dn_solution2
REDIS_URL=redis://localhost:6379
ALLOWED_HOSTS=your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

#### 8.2.3 배포 스크립트
```bash
#!/bin/bash
# deploy.sh

# 백엔드 배포
cd backend
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

# 프론트엔드 배포
cd ../frontend
git pull origin main
npm install
npm run build
sudo cp -r build/* /var/www/html/
```

---

## 📝 결론

DN_SOLUTION2는 계층별 업체 관리, 동적 정책 생성, 리베이트 할당 및 정산 시스템을 제공하는 종합적인 비즈니스 관리 플랫폼입니다.

### 주요 특징:
- ✅ 계층별 권한 관리
- ✅ 실시간 데이터 업데이트
- ✅ 엑셀 다운로드 기능
- ✅ 자동 정산 시스템
- ✅ 사용자 친화적 UI/UX

### 향후 발전 방향:
- 🔮 AI 기반 분석 및 예측
- 🔮 모바일 앱 개발
- 🔮 블록체인 기반 정산
- 🔮 실시간 알림 시스템
- 🔮 고급 통계 및 리포트

이 문서는 시스템의 전체적인 구조와 기능을 이해하는 데 도움이 될 것입니다.

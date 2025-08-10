# DN\_SOLUTION2 기능 명세 v1.0 (리모델링 기준)

> 목적: 07/08/09 설계 문서에 맞추어 **기능을 명확히 정의**하고, 백엔드/프론트/데브옵스가 동일한 기준으로 구현·검수할 수 있도록 한다. (트래픽: 사용자 1,500명 / 일 200,000건 / 동시 1,000)

---

## 1. 역할(Role)과 권한(High-level)

* **Headquarters(HQ)**: 전사 정책/리베이트/정산 승인, 모든 하위 데이터 조회·관리
* **Agency**: 소속 리테일 관리, 리베이트 배분, 소속 주문/정산 조회·관리(정책 생성 불가)
* **Retail**: 주문 생성/조회, 본인 데이터만 접근
* 모든 API는 JWT 인증 필수, 계층 권한 검증(문서 08 참조)

---

## 2. 핵심 기능 목록 (Feature List)

1. **인증/인가**

   * 로그인/토큰재발급/로그아웃(블랙리스트) + `GET /api/v1/auth/me` 사용자·회사 컨텍스트 제공
   * 캐시: 사용자 권한/회사 트리 5분 TTL
   * 수락 기준(AC): 비정상 토큰 401, 만료 토큰 401+자동 재발급(프론트 인터셉터), 블랙리스트 후 즉시 무효

2. **회사/조직 관리**

   * 회사 생성(HQ/Agency/Retail), 부모-자식 계층 규칙 검증
   * 사용자 생성/승인(상위 조직만 승인 가능, HQ는 자동 승인)
   * 계층 조회 API(트리)
   * AC: 잘못된 계층 연결 400, 중복 코드 409, 트리 조회는 본인 가시 범위만

3. **정책(Policy) 관리 \[HQ 전용]**

   * 5단계 워크플로로 정책 생성(회사 묶음/요금제/리베이트/계약조건/활성화)
   * 정책 그룹 할당(선택 회사 + 모든 하위 자동 포함)
   * 리베이트 테이블: (정책×통신사×요금제카테고리) 유니크
   * AC: 정책 활성/비활성, 중복 리베이트 조합 409

4. **상품가격(ProductPrice) 관리**

   * 회사별 매입/판매/마진 자동 일치(검증), 활성/비활성
   * AC: 마진=판매-매입 불일치 400

5. **주문(Order)**

   * 리테일이 주문 생성(옵션: 정책, 요금제, 상품가격)
   * 주문 생성 시: 리베이트 계산(정책×통신사×카테고리) → **회사 잔액 선차감(F) & 트랜잭션 처리**
   * 상태 전이: `pending → approved/rejected → shipped → completed` (취소는 approved 이전까지)
   * AC: 리베이트 부족 400, 잘못된 상태 전이 409, 동시 주문 시 멱등키로 중복 방지

6. **리베이트 배분(Allocation)**

   * HQ→Agency, Agency→Retail 배분, 규칙 위반 차단
   * HQ 승인 자동, 그 외 수동 승인(역할 검증)
   * 승인 시 잔액 이동 트랜잭션, 음수 불가
   * AC: 기간역전 400/ 금액<=0 400/ 권한 불일치 403

7. **정산(Settlement)**

   * 주문 `completed` 시 정산 레코드 자동 생성(`rebate + product_profit`)
   * HQ/Agency 기간 합산 승인 집계 API(읽기용)
   * AC: 기간 내 합산 금액/건수 일치, 비동기 리포트 생성 가능(Celery)

8. **대시보드/리포트**

   * 대시보드: 주문/리베이트/정산 요약(권한 가시범위), 캐시 TTL 60s
   * 엑셀 리포트: 정산/주문/배분 (민감정보 마스킹, 파일 만료 링크)
   * AC: 캐시 히트율 > 80% 목표, 리포트 1만 행 기준 30초 내 비동기 완료

---

## 3. 유저 스토리 (대표 시나리오)

* **Retail 주문 생성**: 리테일 직원이 단말/요금제/정책 선택→ 예상 리베이트 확인→ 주문 제출 → 성공 시 주문ID/선차감 리베이트 노출
* **HQ 승인**: HQ 관리자가 주문 목록에서 `pending` 필터→ 상세 확인→ 승인→ 배송번호 입력→ 완료 시 정산 레코드 확인
* **Agency 배분**: Agency 관리자가 소속 리테일에 월별 배분 생성→ HQ 자동 승인 아님→ 자체 승인 후 리테일 잔액 반영

---

## 4. API 사양 (요약)

* `POST /api/v1/auth/login` → {access, refresh}
* `POST /api/v1/auth/refresh` → {access}
* `POST /api/v1/auth/logout` → 204 + 블랙리스트
* `GET /api/v1/auth/me` → {user, role, company}
* `GET /api/v1/companies/tree` (권한 범위)
* `POST /api/v1/policies` (HQ)
* `GET /api/v1/policies?assigned=true` (가시 범위)
* `POST /api/v1/orders` (Retail 기본)
* `PATCH /api/v1/orders/{id}/status` (권한/전이검증)
* `POST /api/v1/rebates/allocations` (HQ/Agency)
* `POST /api/v1/reports/export` (비동기)

> 모든 목록 API: `?page[size]=20&cursor=...` (기본 20, 최대 100), 정렬/필터 스키마 통일

---

## 5. 데이터 규칙/무결성

* 회사 계층: HQ 상위 없음, Agency 상위=HQ, Retail 상위=Agency (DB/모델 clean 검증)
* 리베이트 잔액: 음수 불가, F-expression으로 동시성 제어, 승인/주문 처리 시 단일 트랜잭션
* 주문 상태 전이표에 따른 엄격 검증(서비스 레이어)

---

## 6. 캐시/성능/쿼리

* Redis 캐시: 회사 트리, 권한, 대시보드 요약(60s)
* DB 풀링: pgbouncer 또는 django-db-geventpool 설정, 재시도 백오프
* N+1 제거: `select_related('company','selected_plan__telecom_provider')`, `prefetch_related('settlements')`
* 인덱스: (주요 검색)

  * orders: (company\_id, status, created\_at), (policy\_id)
  * rebates: (policy\_id, telecom\_provider\_id, plan\_category) unique
  * allocations: (from\_company\_id, to\_company\_id), (period\_start, period\_end), (status)

---

## 7. 보안/컴플라이언스

* JWT(SimpleJWT), 토큰 블랙리스트 사용
* 계층 권한 필수(Permission 클래스 + object-level)
* XSS: 프론트 출력 인코딩, 위험 HTML 금지
* CSRF: 안전 메서드 제외, CORS 허용 도메인 화이트리스트
* 민감정보 마스킹: 주민/카드/계좌번호, 로그·응답·리포트 모두 동일 규칙 적용

---

## 8. 로깅/모니터링

* 레벨: DEBUG/INFO/WARNING/ERROR
* 파일 로테이션 + JSON 구조화 + Sentry 핸들러
* 메트릭: 요청/응답 시간, DB 쿼리 시간, 캐시 히트율, 큐 대기/실패율

---

## 9. 예외 처리

* 서비스 레이어에서 도메인 예외 → 표준 에러 응답 `{code, message, detail}`
* 트랜잭션 롤백: 주문/승인/배분은 atomic 블록, 멱등키로 재시도 안전
* 사용자 메시지: 한국어 기본 + 개발자용 trace\_id 포함

---

## 10. 확장성

* API 버전: `/api/v1` 유지, `/api/v2`는 응답 필드 변경 시 도입
* 도메인 경계 폴더링(orders/rebates/reports/users)
* 정책·정산 로직 플러그인(전략/팩토리)로 교체 가능
* 배치/리포트: Celery + Redis + S3 아카이브

---

## 11. 페이지/화면 (프론트)

* 로그인/로그아웃(토큰 재발급 자동), 대시보드(요약/최근), 주문 목록/상세/생성, 정책 목록/생성(HQ), 배분 생성/승인, 정산 요약, 리포트 다운로드
* 공통: 페이지네이션, 권한 기반 메뉴 표시, 에러 토스트, 멱등 제출 방지(로딩/비활성)

---

## 12. 검증 체크리스트(샘플)

* [ ] 리테일 주문 생성 시 리베이트 부족 400
* [ ] HQ 승인 시 정산 레코드 자동 생성
* [ ] Agency→Retail 배분 승인 후 잔액 정확히 이동
* [ ] 대시보드 캐시 60s 반영, 무효화 시점 확인
* [ ] N+1 없는지 API 별 쿼리 수 측정
* [ ] 로그에 민감정보 마스킹 확인

---

## 13. 오픈 이슈/확인 필요(예)

* 주문 멱등키 헤더 규격(`Idempotency-Key`) 확정 필요
* 리포트 보존기간/만료 정책(다운로드 링크 TTL)
* 다중 통신사/복수 요금제 묶음 주문 지원 여부

# HB Admin - B2B 플랫폼 백엔드 설정 가이드

Django 4.2와 Python 3.11 기반의 B2B 플랫폼 백엔드 프로젝트입니다.

## 1. 프로젝트 구조

```
hb_admin/
├── hb_admin/              # Django 프로젝트 설정
│   ├── settings.py        # 메인 설정 파일
│   ├── urls.py           # 메인 URL 설정
│   └── wsgi.py           # WSGI 설정
├── companies/            # 업체 관리 앱
│   ├── models.py         # 업체, 사용자, 메시지 모델
│   ├── serializers.py    # API 시리얼라이저
│   ├── views.py          # API 뷰
│   ├── urls.py           # URL 라우팅
│   └── admin.py          # Django Admin 설정
├── policies/             # 정책 관리 앱
│   ├── models.py         # 정책, 정책배정 모델
│   ├── serializers.py    # API 시리얼라이저
│   ├── views.py          # API 뷰
│   ├── urls.py           # URL 라우팅
│   └── admin.py          # Django Admin 설정
├── orders/               # 주문 관리 앱
│   ├── models.py         # 주문, 메모, 송장 모델
│   ├── serializers.py    # API 시리얼라이저
│   ├── views.py          # API 뷰
│   ├── urls.py           # URL 라우팅
│   └── admin.py          # Django Admin 설정
├── logs/                 # 로그 파일 디렉토리
├── requirements.txt      # 필수 패키지 목록
├── .env.example         # 환경 변수 예제
└── manage.py            # Django 관리 명령
```

## 2. 설치 및 환경 설정

### 2.1 Python 가상환경 생성

```bash
# Python 3.11 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate
```

### 2.2 필수 패키지 설치

```bash
# 필수 패키지 설치
pip install -r requirements.txt
```

### 2.3 PostgreSQL 데이터베이스 설정

```bash
# PostgreSQL 설치 후 데이터베이스 생성
psql -U postgres
CREATE DATABASE hb_admin;
CREATE USER hb_admin_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE hb_admin TO hb_admin_user;
\q
```

### 2.4 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env

# .env 파일을 편집하여 실제 값으로 변경
# - SECRET_KEY: Django 비밀키 설정
# - DB_PASSWORD: 데이터베이스 비밀번호
# - DEBUG: 개발환경에서는 True, 운영환경에서는 False
```

## 3. 데이터베이스 마이그레이션

### 3.1 마이그레이션 파일 생성

```bash
# 각 앱별 마이그레이션 파일 생성
python manage.py makemigrations companies
python manage.py makemigrations policies  
python manage.py makemigrations orders
```

### 3.2 데이터베이스 마이그레이션 실행

```bash
# 데이터베이스 마이그레이션 적용
python manage.py migrate
```

### 3.3 슈퍼유저 생성

```bash
# Django Admin 접근용 슈퍼유저 생성
python manage.py createsuperuser
```

## 4. 프로젝트 실행

### 4.1 개발 서버 실행

```bash
# Django 개발 서버 시작
python manage.py runserver 0.0.0.0:8000
```

### 4.2 접속 확인

- **API 루트**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/
- **업체 관리 API**: http://localhost:8000/api/companies/
- **정책 관리 API**: http://localhost:8000/api/policies/
- **주문 관리 API**: http://localhost:8000/api/orders/

## 5. 주요 API 엔드포인트

### 5.1 업체 관리 API

- **권한 기반 조회**:
  - **슈퍼유저**: 모든 업체 정보를 조회합니다.
  - **대리점 관리자**: 자신의 대리점 정보와 소속된 하위 판매점 목록을 조회합니다.
  - **판매점 직원**: 자신이 속한 판매점 정보만 조회합니다.

```
GET    /api/companies/companies/                    # 업체 목록 조회 (권한에 따라 필터링)
POST   /api/companies/companies/                    # 새 업체 생성 (대리점은 하위 판매점 생성 가능)
GET    /api/companies/companies/{id}/               # 업체 상세 조회
PUT    /api/companies/companies/{id}/               # 업체 정보 수정
DELETE /api/companies/companies/{id}/               # 업체 삭제
POST   /api/companies/companies/{id}/toggle_status/ # 업체 상태 전환
POST   /api/companies/companies/bulk_delete/        # 업체 일괄 삭제
```

### 5.2 정책 관리 API

```
GET    /api/policies/policies/                      # 정책 목록 조회
POST   /api/policies/policies/                      # 새 정책 생성
GET    /api/policies/policies/{id}/                 # 정책 상세 조회
PUT    /api/policies/policies/{id}/                 # 정책 정보 수정
DELETE /api/policies/policies/{id}/                 # 정책 삭제
POST   /api/policies/policies/{id}/generate_html/   # HTML 자동 생성
POST   /api/policies/policies/{id}/toggle_expose/   # 정책 노출 전환
```

### 5.3 주문 관리 API

```
GET    /api/orders/orders/                          # 주문 목록 조회
POST   /api/orders/orders/                          # 새 주문 생성
GET    /api/orders/orders/{id}/                     # 주문 상세 조회
PUT    /api/orders/orders/{id}/                     # 주문 정보 수정
DELETE /api/orders/orders/{id}/                     # 주문 삭제
POST   /api/orders/orders/{id}/update_status/       # 주문 상태 업데이트
GET    /api/orders/orders/statistics/               # 주문 통계 조회
```

## 6. 데이터 모델 구조

### 6.1 업체 관련 모델

- **Company**: 업체 정보 (대리점/판매점)
  - `parent_company`: 판매점이 속한 상위 대리점을 가리키는 외래 키. 대리점-판매점 간의 계층 구조를 형성합니다.
- **CompanyUser**: 업체별 사용자 계정
- **CompanyMessage**: 업체 메시지

### 6.2 정책 관련 모델

- **Policy**: 스마트기기 판매 정책
- **PolicyAssignment**: 정책-업체 배정 관계

### 6.3 주문 관련 모델

- **Order**: 고객 주문서
- **OrderMemo**: 주문별 메모
- **Invoice**: 배송 송장 정보

## 7. 개발 도구

### 7.1 Django Shell 실행

```bash
# Django 셸에서 모델 테스트
python manage.py shell
```

### 7.2 로그 확인

```bash
# 로그 파일 실시간 확인
tail -f logs/hb_admin.log
```

### 7.3 테스트 실행

```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test companies
python manage.py test policies
python manage.py test orders
```

## 8. 배포 고려사항

### 8.1 운영 환경 설정

1. `DEBUG=False`로 설정
2. `ALLOWED_HOSTS`에 도메인 추가
3. 정적 파일 수집: `python manage.py collectstatic`
4. 데이터베이스 백업 설정
5. 로그 로테이션 설정

### 8.2 보안 설정

1. SECRET_KEY 안전하게 관리
2. CORS 설정 검토
3. API 레이트 리미팅 설정
4. HTTPS 적용

## 9. 문제 해결

### 9.1 일반적인 문제들

**데이터베이스 연결 오류**:
- PostgreSQL 서비스 실행 확인
- .env 파일의 데이터베이스 설정 확인

**마이그레이션 오류**:
- 기존 마이그레이션 파일 삭제 후 재생성
- `python manage.py migrate --fake-initial`

**패키지 설치 오류**:
- pip 버전 업그레이드: `pip install --upgrade pip`
- 가상환경 재생성

### 9.2 로그 확인 방법

- 애플리케이션 로그: `logs/hb_admin.log`
- Django 디버그 정보: 개발 서버 콘솔 출력
- 데이터베이스 쿼리 로그: Django settings의 LOGGING 설정

## 10. 개발 팀 가이드

### 10.1 코드 스타일

- 함수와 변수명: 명확하고 이해하기 쉬운 이름 사용
- 주석: 모든 함수와 클래스에 목적과 동작 설명
- 로깅: 모든 중요한 동작에 대한 로그 기록
- 예외 처리: 모든 예외 상황에 대한 적절한 처리

### 10.2 개발 워크플로우

1. 기능 개발 전 이슈 생성
2. 브랜치 생성하여 개발
3. 테스트 코드 작성
4. 코드 리뷰 후 메인 브랜치 병합

이제 프로젝트가 완전히 설정되었습니다. 위의 가이드를 따라 환경을 구성하고 실행해보세요!
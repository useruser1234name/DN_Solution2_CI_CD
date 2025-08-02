# 초기 설정 및 사용자 관리 가이드

## 1. 시스템 개요

DN_solution은 계층적 승인 시스템을 가진 업체 관리 플랫폼입니다. 본사-협력사-판매점의 3단계 계층 구조로 구성되어 있으며, 각 계층별로 승인 권한이 다릅니다.

### 1.1 계층 구조
- **본사 (Headquarters)**: 최상위 관리자, 모든 사용자 승인 가능
- **협력사 (Agency)**: 본사 하위, 자신의 하위 판매점만 승인 가능
- **판매점 (Retail)**: 협력사 하위, 승인 권한 없음

### 1.2 승인 권한
- **슈퍼유저**: 모든 사용자 승인 가능
- **본사 관리자**: 모든 사용자 승인 가능
- **협력사 관리자**: 자신의 하위 판매점만 승인 가능
- **판매점 사용자**: 승인 권한 없음

## 2. 초기 설정

### 2.1 시스템 시작 시 필요한 것

처음 시스템을 시작할 때는 승인할 관리자가 없는 상황이 발생할 수 있습니다. 이를 해결하기 위한 방법들:

#### 방법 1: 초기 관리자 계정 생성 (권장)
```bash
# 기본 설정으로 초기 관리자 생성
python manage.py create_initial_admin

# 커스텀 설정으로 생성
python manage.py create_initial_admin --username myadmin --password mypassword123 --company-name "우리회사 본사" --company-code "HQ_001"
```

#### 방법 2: 기존 사용자 일괄 승인
```bash
# 모든 기존 사용자를 승인 상태로 변경
python manage.py approve_existing_users
```

#### 방법 3: 특정 사용자 승인
```bash
# 특정 사용자만 승인
python manage.py approve_specific_user --username username
```

### 2.2 생성되는 계정 정보

`create_initial_admin` 명령어로 생성되는 계정:
- **Django 슈퍼유저**: 모든 권한을 가진 관리자
- **본사 업체**: 최상위 계층의 업체
- **CompanyUser**: 승인된 상태의 관리자 계정

기본 생성 정보:
- **사용자명**: admin
- **비밀번호**: admin1234
- **업체명**: 메인 본사
- **업체 코드**: HQ_MAIN

## 3. 사용자 관리

### 3.1 Django Admin을 통한 관리

#### 접속 정보
- **URL**: `http://your-domain:8000/admin/`
- **계정**: admin / admin1234

#### 주요 관리 기능
1. **업체 관리** (`companies/companies/`)
   - 업체 생성, 수정, 삭제
   - 상위 업체 관계 설정
   - 업체 상태 관리

2. **사용자 관리** (`companies/companyusers/`)
   - 사용자 생성, 수정, 삭제
   - 승인 상태 관리
   - 역할 설정

### 3.2 승인 시스템

#### 승인 상태
- **pending**: 승인 대기
- **approved**: 승인됨
- **rejected**: 거절됨

#### 승인 프로세스
1. 사용자가 회원가입
2. 상위 업체 코드 검증
3. 승인 대기 상태로 생성
4. 상위 업체 관리자가 승인/거절
5. 승인된 사용자만 로그인 가능

### 3.3 계층별 회원가입

#### 본사 가입
- **상위 업체 코드**: 불필요
- **승인자**: 슈퍼유저 또는 기존 본사 관리자

#### 협력사 가입
- **상위 업체 코드**: 본사 코드 필수
- **승인자**: 본사 관리자

#### 판매점 가입
- **상위 업체 코드**: 협력사 코드 필수
- **승인자**: 협력사 관리자

## 4. 데이터 정리

### 4.1 전체 데이터 정리
```bash
# admin 계정을 제외한 모든 데이터 삭제
python manage.py cleanup_data --confirm
```

### 4.2 특정 데이터 삭제
```bash
# 특정 사용자 삭제
python manage.py shell
>>> from companies.models import CompanyUser
>>> CompanyUser.objects.filter(username='username').delete()
```

## 5. 문제 해결

### 5.1 승인 대기 사용자가 보이지 않는 경우

#### 원인
1. 상위 업체 관계가 설정되지 않음
2. 승인 권한이 없음
3. API 권한 문제

#### 해결 방법
1. **Django Admin**에서 업체의 상위 업체 설정
2. 사용자 권한 확인
3. API 권한 설정 확인

### 5.2 로그인 실패

#### 원인
1. 승인되지 않은 사용자
2. 비밀번호 오류
3. Django User와 CompanyUser 불일치

#### 해결 방법
1. **Django Admin**에서 사용자 승인 상태 확인
2. 비밀번호 재설정
3. Django User와 CompanyUser 매핑 확인

### 5.3 권한 문제

#### 원인
1. 사용자 역할 설정 오류
2. 업체 계층 관계 오류
3. 승인 상태 문제

#### 해결 방법
1. **Django Admin**에서 사용자 역할 확인
2. 업체 계층 관계 재설정
3. 승인 상태 재설정

## 6. 권장 워크플로우

### 6.1 시스템 초기 설정
```bash
# 1. 마이그레이션 실행
python manage.py migrate

# 2. 초기 관리자 계정 생성
python manage.py create_initial_admin

# 3. 서버 시작
python manage.py runserver
```

### 6.2 새로운 업체 추가
1. **본사 관리자**로 로그인
2. **회원가입** 페이지에서 협력사 생성
3. **사용자 승인 관리**에서 협력사 승인
4. **협력사 관리자**로 로그인
5. **회원가입** 페이지에서 판매점 생성
6. **사용자 승인 관리**에서 판매점 승인

### 6.3 일상적인 관리
1. **Django Admin**을 통한 사용자 관리
2. **웹 인터페이스**를 통한 승인 관리
3. **API**를 통한 자동화된 관리

## 7. 보안 고려사항

### 7.1 초기 비밀번호 변경
- 생성된 모든 계정의 초기 비밀번호는 반드시 변경
- 강력한 비밀번호 정책 적용

### 7.2 권한 관리
- 각 사용자의 역할과 권한을 정기적으로 검토
- 불필요한 권한은 즉시 제거

### 7.3 데이터 백업
- 정기적인 데이터베이스 백업
- 설정 변경 전 백업 생성

## 8. 추가 도움말

### 8.1 관련 문서
- `docs/Backend_Design.md`: 백엔드 설계 문서
- `docs/System_Architecture_and_Flow.md`: 시스템 아키텍처 문서
- `docs/Initial_Setup_Guide.md`: 초기 설정 가이드

### 8.2 명령어 목록
- `python manage.py create_initial_admin`: 초기 관리자 생성
- `python manage.py approve_existing_users`: 기존 사용자 일괄 승인
- `python manage.py approve_specific_user --username username`: 특정 사용자 승인
- `python manage.py cleanup_data --confirm`: 데이터 정리

### 8.3 API 엔드포인트
- `/api/companies/auth/login/`: 로그인
- `/api/companies/auth/signup/`: 회원가입
- `/api/companies/users/unapproved/`: 승인 대기 사용자 목록
- `/api/companies/users/{id}/approve/`: 사용자 승인
- `/api/companies/users/{id}/reject/`: 사용자 거절 
# 초기 설정 가이드

## 처음 시스템을 시작할 때

DN_solution 시스템은 사용자 승인 시스템이 구현되어 있어서, 처음 시스템을 시작할 때는 승인할 관리자가 없는 상황이 발생할 수 있습니다. 이를 해결하기 위한 방법들을 안내합니다.

## 방법 1: 초기 관리자 계정 생성 (권장)

### 1. Django 관리 명령어 실행

```bash
# 기본 설정으로 초기 관리자 생성
python manage.py create_initial_admin

# 또는 커스텀 설정으로 생성
python manage.py create_initial_admin --username myadmin --password mypassword123 --company-name "우리회사 본사" --company-code "HQ_001"
```

### 2. 생성되는 계정 정보

- **Django 슈퍼유저**: 모든 권한을 가진 관리자
- **본사 업체**: 최상위 계층의 업체
- **CompanyUser**: 승인된 상태의 관리자 계정

### 3. 로그인 및 사용

생성된 계정으로 로그인하여 다음 작업을 수행할 수 있습니다:

- 다른 사용자들의 승인/거절
- 협력사 및 판매점 업체 생성
- 시스템 관리

## 방법 2: 기존 사용자 일괄 승인

만약 이미 사용자들이 생성되어 있다면:

```bash
# 모든 기존 사용자를 승인 상태로 변경
python manage.py approve_existing_users
```

## 방법 3: Django Admin을 통한 수동 설정

### 1. 슈퍼유저 생성

```bash
python manage.py createsuperuser
```

### 2. Django Admin 접속

1. `http://localhost:8000/admin/` 접속
2. 슈퍼유저로 로그인
3. Companies > Companies에서 본사 업체 생성
4. Companies > Company users에서 관리자 계정 생성 및 승인

## 권장 워크플로우

### 1단계: 초기 설정
```bash
# 1. 마이그레이션 실행
python manage.py migrate

# 2. 초기 관리자 계정 생성
python manage.py create_initial_admin

# 3. 서버 시작
python manage.py runserver
```

### 2단계: 시스템 사용
1. 생성된 관리자 계정으로 로그인
2. User Approval 페이지에서 다른 사용자들 승인
3. Company Management에서 업체 관리

## 주의사항

1. **보안**: 초기 비밀번호는 반드시 변경하세요
2. **백업**: 초기 설정 후 데이터베이스 백업을 권장합니다
3. **테스트**: 운영 환경에 배포하기 전에 충분한 테스트를 진행하세요

## 문제 해결

### 로그인 실패 시
- Django User와 CompanyUser가 모두 생성되었는지 확인
- 비밀번호가 올바른지 확인
- 사용자 상태가 'approved'인지 확인

### 승인 권한 문제 시
- 본사 계정으로 로그인했는지 확인
- 슈퍼유저 권한이 있는지 확인

## 추가 도움말

더 자세한 정보는 다음 문서를 참조하세요:
- `docs/Backend_Design.md`: 백엔드 설계 문서
- `docs/System_Architecture_and_Flow.md`: 시스템 아키텍처 문서 
# DN_solution 프로젝트 분석 보고서

## 1. 프로젝트 개요

이 프로젝트는 Django와 Django REST Framework를 기반으로 구축된 B2B 플랫폼의 백엔드 시스템입니다. 주요 기능은 업체, 정책, 주문을 관리하는 것입니다.

## 2. 기술 스택

- **프레임워크:** Django 4.2.7, Django REST Framework 3.14.0
- **데이터베이스:** PostgreSQL
- **CORS 처리:** django-cors-headers
- **필터링:** django-filter
- **환경 변수 관리:** python-decouple, python-dotenv
- **API 문서화:** drf-spectacular
- **로깅:** colorlog
- **테스트:** factory-boy, Faker
- **보안:** django-ratelimit
- **파일 처리:** Pillow
- **유틸리티:** requests

## 3. 프로젝트 구조

- **hb_admin/**: 메인 Django 프로젝트 디렉토리
- **companies/**: 업체, 사용자, 메시지 관리 앱
- **policies/**: 정책 및 정책 할당 관리 앱
- **orders/**: 주문, 메모, 송장 관리 앱
- **logs/**: 로그 파일 디렉토리
- **requirements.txt**: 필수 패키지 목록
- **manage.py**: Django 관리 스크립트

## 4. 주요 기능

- **업체 관리:** 업체 정보 등록, 수정, 삭제 및 상태 관리
- **정책 관리:** 판매 정책 생성, 수정, 삭제 및 노출 여부 관리
- **주문 관리:** 주문 생성, 수정, 삭제 및 상태 업데이트
- **API 문서 자동화:** drf-spectacular를 이용한 API 문서 제공
- **로깅 및 모니터링:** 파일 기반 로깅 시스템

## 5. 설정 및 실행

1.  **가상환경 생성 및 활성화:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
2.  **패키지 설치:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **데이터베이스 설정:**
    - PostgreSQL에 `hb_admin` 데이터베이스 및 사용자 생성
    - `.env` 파일에 데이터베이스 정보 설정
4.  **데이터베이스 마이그레이션:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
5.  **슈퍼유저 생성:**
    ```bash
    python manage.py createsuperuser
    ```
6.  **개발 서버 실행:**
    ```bash
    python manage.py runserver
    ```

## 6. 주요 API 엔드포인트

- **업체 관리:** `/api/companies/`
- **정책 관리:** `/api/policies/`
- **주문 관리:** `/api/orders/`

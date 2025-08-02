# 프로젝트 구조 (Project Structure)

`DN_solution` 프로젝트는 Django를 기반으로 하는 백엔드 시스템과 잠재적인 프론트엔드 애플리케이션을 위한 구조를 가집니다. 주요 디렉토리와 파일은 다음과 같습니다.

## 1. 최상위 디렉토리 (`DN_solution/`)

*   `.git/`: Git 버전 관리를 위한 디렉토리.
*   `companies/`: `Company` 모델 및 관련 API 로직을 포함하는 Django 앱.
*   `hb_admin/`: Django 프로젝트의 메인 설정 파일 및 URL 구성을 포함하는 디렉토리.
*   `logs/`: 애플리케이션 로그 파일이 저장되는 디렉토리.
*   `orders/`: 주문 관련 모델 및 API 로직을 포함하는 Django 앱.
*   `policies/`: 정책 관련 모델 및 API 로직을 포함하는 Django 앱.
*   `venv/`: Python 가상 환경 디렉토리. 프로젝트 의존성 관리를 위해 사용됩니다.
*   `docs/`: 프로젝트 관련 문서(현재 이 파일 포함)가 저장되는 디렉토리.
*   `.env`: 환경 변수 설정을 위한 파일 (일반적으로 `.gitignore`에 포함).
*   `.gitignore`: Git 버전 관리에서 제외할 파일 및 디렉토리 목록.
*   `db.sqlite3`: SQLite 데이터베이스 파일 (개발 환경에서 사용).
*   `manage.py`: Django 프로젝트 관리를 위한 커맨드라인 유틸리티.
*   `requirements.txt`: 프로젝트에 필요한 Python 패키지 목록.

## 2. `companies/` 앱

`Company` 모델과 관련된 핵심 비즈니스 로직을 담당합니다.

*   `__init__.py`
*   `admin.py`: Django 관리자 페이지 설정.
*   `apps.py`: Django 앱 설정.
*   `models.py`: `Company`, `CompanyUser`, `CompanyMessage` 모델 정의.
*   `serializers.py`: Django REST Framework를 위한 모델 직렬화/역직렬화.
*   `tests.py`: `Company` 모델 및 API에 대한 단위 및 통합 테스트.
*   `urls.py`: `companies` 앱의 URL 라우팅 설정.
*   `views.py`: `Company`, `CompanyUser`, `CompanyMessage`에 대한 API 뷰셋 정의.
*   `templates/companies/`: `model_test.html`과 같은 HTML 템플릿 파일 저장.

## 3. `hb_admin/` 디렉토리

Django 프로젝트의 전역 설정 및 URL 라우팅을 담당합니다.

*   `__init__.py`
*   `asgi.py`: ASGI 호환 웹 서버를 위한 진입점.
*   `settings.py`: Django 프로젝트의 모든 설정(데이터베이스, 앱 등록, 미들웨어 등).
*   `urls.py`: 프로젝트 전체의 URL 라우팅 설정.
*   `wsgi.py`: WSGI 호환 웹 서버를 위한 진입점.

## 4. `orders/` 앱

주문 관리와 관련된 모델 및 API 로직을 포함합니다.

*   `models.py`: 주문 관련 모델 정의.
*   `views.py`: 주문 관련 API 뷰셋 정의.
*   `serializers.py`: 주문 관련 직렬화/역직렬화.
*   `urls.py`: 주문 앱의 URL 라우팅 설정.

## 5. `policies/` 앱

정책 관리와 관련된 모델 및 API 로직을 포함합니다.

*   `models.py`: 정책 관련 모델 정의.
*   `views.py`: 정책 관련 API 뷰셋 정의.
*   `serializers.py`: 정책 관련 직렬화/역직렬화.
*   `urls.py`: 정책 앱의 URL 라우팅 설정.

## 6. `docs/` 디렉토리

프로젝트의 모든 문서화를 위한 중앙 저장소입니다.

*   `Company_Creation_Policy.md`: `Company` 생성 정책에 대한 상세 문서.
*   `UI_Access_Control_Strategy.md`: UI 접근 제어 전략에 대한 문서.
*   `Project_Structure.md`: (현재 문서) 프로젝트의 전체적인 디렉토리 및 파일 구조.
*   `Frontend_Overview.md`: 프론트엔드 애플리케이션의 개요.
*   `Backend_Overview.md`: 백엔드 시스템의 개요.
*   `Features_and_Logic.md`: 주요 기능 및 핵심 로직 설명.
*   `Overall_Summary.md`: 프로젝트의 종합적인 요약.

이 구조는 모듈화된 개발을 지향하며, 각 앱이 특정 비즈니스 도메인을 담당하도록 설계되었습니다.

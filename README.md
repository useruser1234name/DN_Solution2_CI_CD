# DN_SOLUTION2 - 통신사 리베이트 관리 시스템

## 📋 프로젝트 개요

DN_SOLUTION2는 본사 → 대리점 → 소매점의 계층 구조를 가진 통신사 리베이트 관리 시스템입니다. 
동적 정책 생성, 리베이트 할당, 주문 처리, 정산 관리 등의 핵심 기능을 제공합니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (React)       │◄──►│   (Django)      │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Cache         │
                       │   (Redis)       │
                       └─────────────────┘
```

## 🚀 주요 기능

### 1. 계층별 업체 관리
- **본사 (HQ)**: 전체 시스템 관리, 정책 생성, 리베이트 할당
- **대리점 (Agency)**: 하위 소매점 관리, 리베이트 분배
- **소매점 (Retail)**: 주문 처리, 고객 관리

### 2. 정책 관리 시스템
- 5단계 워크플로우 정책 생성
- 통신사별 요금제 기준 리베이트 설정
- 동적 주문서 양식 생성

### 3. 리베이트 관리
- 계층별 리베이트 할당 및 분배
- 자동 정산 시스템
- 실시간 잔액 관리

### 4. 주문 처리
- 정책 기반 주문 생성
- 상태별 워크플로우 관리
- 엑셀 다운로드 기능

## 🛠️ 기술 스택

### Backend
- **Framework**: Django 5.2.5 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Authentication**: JWT (SimpleJWT)
- **Async Tasks**: Celery + Redis
- **API Documentation**: DRF Spectacular

### Frontend
- **Framework**: React 18
- **State Management**: Redux Toolkit
- **UI Library**: Material-UI
- **HTTP Client**: Axios

### DevOps
- **Containerization**: Docker + Docker Compose
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn
- **Process Manager**: Supervisor (선택사항)

## 📦 설치 및 실행

### 1. 사전 요구사항
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 2. 로컬 개발 환경

#### Backend 설정
```bash
# 저장소 클론
git clone <repository-url>
cd DN_Solution2

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 필요한 값 설정

# 데이터베이스 마이그레이션
python manage.py migrate

# 개발 서버 실행
python manage.py runserver
```

#### Frontend 설정
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm start
```

### 3. Docker 환경 실행

```bash
# 모든 서비스 시작
docker-compose up -d

# 특정 서비스만 시작
docker-compose up -d postgres redis backend

# 로그 확인
docker-compose logs -f backend

# 서비스 중지
docker-compose down
```

### 4. 모니터링 도구 접근
- **pgAdmin**: http://localhost:8080
- **Redis Insight**: http://localhost:8001
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000

## 🔧 환경 변수 설정

### .env 파일 예시
```bash
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True

# 데이터베이스
DB_NAME=dn_solution2_dev
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/1

# JWT
JWT_SECRET_KEY=your-jwt-secret-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## 📚 API 문서

### 주요 엔드포인트
- **인증**: `/api/auth/`
- **회사 관리**: `/api/companies/`
- **정책 관리**: `/api/policies/`
- **주문 관리**: `/api/orders/`
- **리베이트 관리**: `/api/rebates/`

### API 문서 접근
- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`

## 🧪 테스트

### Backend 테스트
```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test companies
python manage.py test policies
python manage.py test orders

# 커버리지 테스트
pytest --cov=. --cov-report=html
```

### Frontend 테스트
```bash
cd frontend

# 테스트 실행
npm test

# 커버리지 테스트
npm run test:coverage
```

## 🚀 배포

### 프로덕션 환경 설정
```bash
# 프로덕션 설정 사용
export DJANGO_SETTINGS_MODULE=dn_solution.settings.production

# 정적 파일 수집
python manage.py collectstatic --noinput

# 데이터베이스 마이그레이션
python manage.py migrate

# Gunicorn으로 서버 실행
gunicorn --config gunicorn.conf.py dn_solution.wsgi:application
```

### Docker 배포
```bash
# 프로덕션 빌드
docker-compose -f docker-compose.prod.yml up -d

# 스케일링
docker-compose up -d --scale backend=3
```

## 📁 프로젝트 구조

```
DN_Solution2/
├── companies/           # 회사 관리 앱
├── policies/            # 정책 관리 앱
├── orders/              # 주문 관리 앱
├── inventory/           # 재고 관리 앱
├── messaging/           # 메시징 앱
├── dn_solution/         # 프로젝트 설정
│   ├── settings/        # 환경별 설정
│   ├── utils/           # 유틸리티 모듈
│   └── middleware/      # 커스텀 미들웨어
├── frontend/            # React 프론트엔드
├── scripts/             # 운영 스크립트
├── Docs/                # 프로젝트 문서
├── docker-compose.yml   # Docker Compose 설정
└── requirements.txt     # Python 의존성
```

## 🔒 보안

### 주요 보안 기능
- JWT 기반 인증
- 계층별 권한 관리
- CORS 설정
- SQL 인젝션 방지
- XSS 방어
- 민감정보 마스킹

### 보안 설정 체크리스트
- [ ] SECRET_KEY 변경
- [ ] DEBUG=False 설정
- [ ] ALLOWED_HOSTS 설정
- [ ] CORS 허용 도메인 제한
- [ ] HTTPS 강제 설정

## 📊 성능 최적화

### 캐싱 전략
- Redis 다층 캐시 시스템
- 데이터베이스 쿼리 최적화
- 정적 파일 압축

### 모니터링
- 성능 메트릭 수집
- 에러 추적 및 로깅
- 데이터베이스 쿼리 분석

## 🤝 기여하기

### 개발 가이드라인
1. 코드 스타일: PEP 8 준수
2. 커밋 메시지: Conventional Commits 형식
3. 테스트: 새로운 기능에 대한 테스트 코드 작성
4. 문서화: 코드 변경 시 관련 문서 업데이트

### 이슈 리포트
- 버그 리포트: 상세한 재현 단계 포함
- 기능 요청: 명확한 사용 사례 설명
- 보안 이슈: 즉시 담당자에게 연락

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

### 연락처
- **개발팀**: dev@dn-solution.com
- **기술지원**: support@dn-solution.com

### 문서
- [API 문서](./Docs/)
- [개발 가이드](./Docs/Development_Practices.md)
- [배포 가이드](./Docs/Deployment_Guide.md)

---

## 🎉 **최신 업데이트 (2025-08-17)**

### ✅ **완성된 핵심 기능들**
- **업체 계층 구조 시스템**: 본사 → 협력사 → 판매점 3단계 계층 완성
- **정책 자동 노출 시스템**: 협력사 선택 시 하위 판매점 자동 노출
- **권한 기반 접근 제어**: 계층별 엄격한 데이터 접근 제한
- **주문 생성 워크플로우**: 판매점에서 할당된 정책으로 주문 생성 가능

### 🔧 **해결된 주요 이슈들**
1. **권한 시스템 보안 강화**: 타 업체 정보 노출 차단
2. **정책 노출 기능 완성**: 실제 API 연동 및 자동 하위 노출
3. **계층 구조 시각화**: 직관적인 트리 구조 표시
4. **주문 생성 플로우**: 정책 선택부터 주문 완료까지 전체 플로우

### 📚 **상세 문서**
- [`FINAL_IMPLEMENTATION_SUMMARY.md`](./FINAL_IMPLEMENTATION_SUMMARY.md) - 전체 구현 완료 보고서
- [`RECENT_ISSUES_AND_SOLUTIONS.md`](./RECENT_ISSUES_AND_SOLUTIONS.md) - 최근 해결된 이슈들
- [`ISSUES.md`](./ISSUES.md) - 전체 이슈 해결 기록

### 🎯 **현재 상태**
**모든 핵심 기능이 완벽하게 작동하며, 실제 운영 환경에서 사용 가능한 수준으로 완성되었습니다.**

---

**버전**: 2.1.0  
**최종 업데이트**: 2025년 8월 17일  
**작성자**: DN_SOLUTION2 개발팀 
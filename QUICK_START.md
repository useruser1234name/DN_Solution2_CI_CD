# 🚀 DN_SOLUTION2 빠른 시작 가이드

## 📋 전제 조건

### 필수 소프트웨어
- **Python 3.11+** - [다운로드](https://www.python.org/downloads/)
- **Node.js 18+** - [다운로드](https://nodejs.org/)
- **Git** - [다운로드](https://git-scm.com/)

### 선택사항 (Docker 사용 시)
- **Docker Desktop** - [다운로드](https://www.docker.com/products/docker-desktop/)

---

## 🎯 방법 1: 로컬 개발 환경 (추천)

### 1단계: 자동 설정 실행
```bash
# Windows
.\setup_dev.bat

# Linux/Mac
chmod +x setup_dev.sh
./setup_dev.sh
```

### 2단계: 개발 서버 실행
```bash
# Windows
.\run_dev.bat

# Linux/Mac  
source venv/bin/activate
python manage.py runserver
```

### 3단계: 프론트엔드 실행 (별도 터미널)
```bash
cd frontend
npm start
```

**접속 주소:**
- 🌐 Frontend: http://localhost:3000
- 🔧 Backend API: http://localhost:8000
- 📚 API 문서: http://localhost:8000/api/schema/swagger-ui/

---

## 🐳 방법 2: Docker 환경

### 1단계: 환경 설정
```bash
# 개발용 환경변수 복사
cp .env.dev .env
```

### 2단계: 전체 서비스 시작
```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 상태 확인
docker-compose ps
```

### 3단계: 초기 데이터 설정 (선택사항)
```bash
# 슈퍼유저 생성 (컨테이너 내부에서)
docker-compose exec backend python manage.py createsuperuser
```

**접속 주소:**
- 🌐 Frontend: http://localhost:3000
- 🔧 Backend API: http://localhost:8000
- 📊 pgAdmin: http://localhost:8080 (admin@dev.local / admin)
- 🔍 Redis Insight: http://localhost:8001

---

## 🛠️ 추가 도구 실행

### 모니터링 도구 시작
```bash
# 개발용 모니터링 도구들 (pgAdmin, Redis Insight)
docker-compose --profile monitoring up -d
```

### Celery 작업자 실행 (로컬 환경)
```bash
# 별도 터미널에서
source venv/bin/activate  # Windows: venv\Scripts\activate
celery -A dn_solution worker -l info
```

### 테스트 실행
```bash
# Backend 테스트
python manage.py test

# Frontend 테스트  
cd frontend
npm test

# E2E 테스트
npx playwright test
```

---

## 🔧 문제 해결

### 일반적인 문제들

#### 1. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -an | findstr :8000  # Windows
lsof -i :8000               # Linux/Mac

# Docker 포트 변경
# .env 파일에서 BACKEND_PORT=8001 설정
```

#### 2. 데이터베이스 연결 오류
```bash
# PostgreSQL 서비스 확인
docker-compose ps postgres

# 데이터베이스 수동 연결 테스트
docker-compose exec postgres psql -U postgres -d dn_solution2_dev
```

#### 3. 가상환경 문제
```bash
# 가상환경 재생성
rm -rf venv  # Linux/Mac
rmdir /s venv  # Windows
python -m venv venv
```

#### 4. Node.js 의존성 문제
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 로그 확인 방법
```bash
# Docker 로그
docker-compose logs -f [service_name]

# 로컬 개발 로그
tail -f logs/django.log  # Linux/Mac
Get-Content logs\django.log -Wait  # Windows PowerShell
```

---

## 📚 다음 단계

### 개발 가이드
- [API 문서](http://localhost:8000/api/schema/swagger-ui/)
- [관리자 페이지](http://localhost:8000/admin/)
- [프로젝트 구조](./PROJECT_STRUCTURE.md)
- [개발 가이드](./DEVELOPMENT_GUIDE.md)

### 주요 기능 테스트
1. **회사 등록**: 관리자 페이지에서 본사/협력사/판매점 등록
2. **정책 생성**: 본사에서 리베이트 정책 생성
3. **정책 노출**: 협력사에서 하위 판매점에 정책 노출
4. **주문 생성**: 판매점에서 할당된 정책으로 주문 생성

---

## 🆘 지원

### 문제 발생 시
1. **GitHub Issues**: 버그 리포트 및 기능 요청
2. **개발팀 연락**: dev@dn-solution.com
3. **문서 확인**: `./documentation/` 폴더

### 추가 명령어
```bash
# 전체 리셋 (주의: 모든 데이터 삭제)
docker-compose down -v
docker system prune -f

# 프로덕션 배포
docker-compose -f docker-compose.prod.yml up -d
```

---

**축하합니다! 🎉 DN_SOLUTION2 개발 환경이 준비되었습니다.**

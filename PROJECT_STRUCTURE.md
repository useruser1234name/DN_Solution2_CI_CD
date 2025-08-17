# DN Solution 2 - 프로젝트 구조

## 📁 정리된 프로젝트 구조

```
DN_Solution2/
├── 📚 documentation/                  # 통합 문서 관리
│   ├── README.md                     # 문서 가이드
│   ├── 🏗️ system/                    # 시스템 문서
│   │   ├── 시스템_개요.md             # 전체 시스템 개요
│   │   ├── 권한_매트릭스.md           # 사용자 권한 및 접근 제어
│   │   ├── 테이블_구조.md             # 데이터베이스 스키마
│   │   └── 기능_흐름도.md             # 비즈니스 프로세스
│   ├── 🔧 backend/                   # 백엔드 문서
│   │   ├── API_엔드포인트.md          # REST API 명세서
│   │   ├── 백엔드_아키텍처.md         # Django 구조 및 설계
│   │   └── 인증_시스템.md             # JWT 인증 및 권한
│   ├── 🎨 frontend/                  # 프론트엔드 문서
│   │   ├── 프론트엔드_구조.md         # React 컴포넌트 구조
│   │   └── 라우팅_가이드.md           # React Router 설정
│   └── 🚀 deployment/               # 배포 문서
│       ├── 배포_가이드.md             # 프로덕션 배포
│       └── 개발_환경_설정.md          # 로컬 개발 환경
│
├── 🧪 tests_integrated/              # 통합 테스트 관리
│   ├── README.md                     # 테스트 가이드
│   ├── 🔬 unit/                      # 단위 테스트
│   │   ├── test_api.py              # Companies API 테스트
│   │   ├── test_cache.py            # 캐시 시스템 테스트
│   │   ├── test_models.py           # 모델 테스트
│   │   ├── test_security.py         # 보안 테스트
│   │   └── test_services.py         # 서비스 로직 테스트
│   ├── 🌐 e2e/                      # End-to-End 테스트
│   │   ├── api-health.spec.js       # API 상태 확인
│   │   ├── auth.spec.js             # 인증 기능 테스트
│   │   ├── security.spec.js         # 보안 테스트
│   │   ├── workflow.spec.js         # 업무 흐름 테스트
│   │   └── test-data.js             # 테스트 데이터
│   ├── 🔌 api/                      # API 테스트
│   └── 🖥️ system/                   # 시스템 테스트
│       ├── test_system_features.py  # 시스템 기능 통합 테스트
│       ├── load_test.py             # 성능 및 부하 테스트
│       └── test_system.sh           # 시스템 테스트 스크립트
│
├── 🏗️ dn_solution/                   # Django 프로젝트 설정
│   ├── settings/                    # 환경별 설정
│   ├── middleware/                  # 미들웨어
│   ├── utils/                       # 유틸리티
│   └── auth_views.py               # 인증 뷰
│
├── 🏢 companies/                     # 회사 관리 앱
├── 📋 policies/                      # 정책 관리 앱
├── 📦 orders/                        # 주문 관리 앱
├── 💰 settlements/                   # 정산 관리 앱
├── 🎯 core/                          # 공통 기능 앱
│
├── 🌐 frontend/                      # React 프론트엔드
│   ├── src/                         # 소스 코드
│   │   ├── components/              # 재사용 컴포넌트
│   │   ├── pages/                   # 페이지 컴포넌트
│   │   ├── contexts/                # Context API
│   │   ├── services/                # API 서비스
│   │   └── utils/                   # 유틸리티
│   └── public/                      # 정적 파일
│
├── 🐳 docker-compose.yml             # Docker 구성
├── 🐳 Dockerfile.backend             # 백엔드 Docker 설정
├── 🔧 requirements.txt               # Python 의존성
├── 📝 package.json                   # Node.js 의존성
├── ⚙️ playwright.config.js          # Playwright 설정
├── 🧪 pytest.ini                    # pytest 설정
├── 🚨 ISSUES.md                      # 이슈 및 해결 기록
├── 📖 README.md                      # 프로젝트 개요
└── 🏗️ DEVELOPMENT_GUIDE.md          # 개발 가이드
```

## 🎯 주요 개선사항

### ✅ 문서 통합 정리
- **이전**: Docs/, archive/ 폴더에 50+ 개의 문서 분산
- **개선**: documentation/ 폴더에 카테고리별 8개 핵심 문서

### ✅ 테스트 통합 관리
- **이전**: 각 앱별로 분산된 테스트 파일들
- **개선**: tests_integrated/ 폴더에 유형별 통합 관리

### ✅ 이슈 추적 강화
- **개선**: ISSUES.md에 모든 문제 해결 과정 상세 기록
- **포함**: API 연결 문제, 인증 이슈, UI 오류 등

### ✅ 불필요한 파일 제거
- **삭제된 파일들**:
  - 중복 리팩토링 문서들 (8개)
  - 임시 테스트 파일들 (5개)
  - 레거시 설정 파일들 (3개)

## 🚀 사용 가이드

### 📖 문서 열람
```bash
# 시스템 이해하기
documentation/system/시스템_개요.md

# API 개발 시
documentation/backend/API_엔드포인트.md

# 프론트엔드 개발 시
documentation/frontend/프론트엔드_구조.md

# 배포 시
documentation/deployment/배포_가이드.md
```

### 🧪 테스트 실행
```bash
# 단위 테스트
cd tests_integrated/unit
python -m pytest

# E2E 테스트
cd tests_integrated/e2e
npx playwright test

# 시스템 테스트
cd tests_integrated/system
python test_system_features.py
```

### 🔍 문제 해결
1. **ISSUES.md** 먼저 확인
2. **로그 파일** 확인 (`logs/` 디렉토리)
3. **테스트 실행**으로 문제 재현
4. **문서** 참조하여 해결

## 📋 유지보수 가이드

### 새로운 문서 추가 시
- 적절한 카테고리 폴더에 배치
- README.md 업데이트
- 관련 문서와 상호 링크 연결

### 새로운 테스트 추가 시
- tests_integrated/ 하위 적절한 디렉토리에 배치
- 테스트 가이드 문서 업데이트

### 이슈 발생 시
- ISSUES.md에 상세 기록
- 해결 과정 단계별 문서화
- 재발 방지 방안 포함

이제 프로젝트 구조가 체계적으로 정리되어 유지보수성과 확장성이 크게 향상되었습니다! 🎉


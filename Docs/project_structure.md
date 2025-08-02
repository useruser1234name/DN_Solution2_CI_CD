# 프로젝트 구조 및 파일 목록

## 📁 프로젝트 개요
업체 관리 시스템 (Django + React)

## 🏗️ 프로젝트 구조

```
DN_Solution/
├── 📁 hb_admin/                 # Django 프로젝트 설정
│   ├── settings.py              # Django 설정
│   ├── urls.py                  # 메인 URL 설정
│   └── wsgi.py                  # WSGI 설정
│
├── 📁 companies/                # 업체 관리 앱
│   ├── models.py                # 데이터 모델
│   ├── views.py                 # API 뷰
│   ├── serializers.py           # 데이터 직렬화
│   ├── admin.py                 # Django Admin 설정
│   ├── urls.py                  # 앱 URL 설정
│   └── middleware.py            # API 로깅 미들웨어
│
├── 📁 policies/                 # 정책 관리 앱
├── 📁 orders/                   # 주문 관리 앱
├── 📁 inventory/                # 재고 관리 앱
├── 📁 messaging/                # 메시지 관리 앱
│
├── 📁 frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── components/          # React 컴포넌트
│   │   ├── pages/               # 페이지 컴포넌트
│   │   ├── contexts/            # React Context
│   │   ├── services/            # API 서비스
│   │   └── App.js               # 메인 앱 컴포넌트
│   └── package.json             # Node.js 의존성
│
├── 📁 logs/                     # 로그 파일
│   └── api.log                  # API 로그
│
├── 📁 Docs/                     # 문서
│   ├── project_structure.md     # 이 파일
│   ├── Backend_Design.md        # 백엔드 설계 문서
│   ├── Frontend_Design.md       # 프론트엔드 설계 문서
│   └── ...                      # 기타 문서들
│
├── manage.py                    # Django 관리 스크립트
└── db.sqlite3                   # SQLite 데이터베이스
```

## 🗂️ 핵심 파일 목록

### 🔧 **Django 백엔드**
| 파일 | 설명 | 상태 |
|------|------|------|
| `hb_admin/settings.py` | Django 설정 (로깅, CORS, 미들웨어) | ✅ 완료 |
| `hb_admin/urls.py` | 메인 URL 라우팅 | ✅ 완료 |
| `companies/models.py` | 데이터 모델 (Company, CompanyUser, CompanyMessage) | ✅ 완료 |
| `companies/views.py` | API 뷰 (ViewSet, LoginView, DashboardView) | ✅ 완료 |
| `companies/serializers.py` | 데이터 직렬화 | ✅ 완료 |
| `companies/admin.py` | Django Admin 설정 | ✅ 완료 |
| `companies/urls.py` | 앱 URL 라우팅 | ✅ 완료 |
| `companies/middleware.py` | API 로깅 미들웨어 | ✅ 완료 |

### 🎨 **React 프론트엔드**
| 파일 | 설명 | 상태 |
|------|------|------|
| `frontend/src/App.js` | 메인 앱 컴포넌트 | ✅ 완료 |
| `frontend/src/contexts/AuthContext.js` | 인증 컨텍스트 | ✅ 완료 |
| `frontend/src/services/api.js` | API 서비스 | ✅ 완료 |
| `frontend/src/pages/LoginPage.js` | 로그인 페이지 | ✅ 완료 |
| `frontend/src/pages/DashboardPage.js` | 대시보드 페이지 | ✅ 완료 |
| `frontend/src/components/ProtectedRoute.js` | 보호된 라우트 | ✅ 완료 |
| `frontend/src/components/Sidebar.js` | 사이드바 컴포넌트 | ✅ 완료 |
| `frontend/src/pages/MainLayout.js` | 메인 레이아웃 | ✅ 완료 |

### 📋 **프론트엔드 페이지**
| 파일 | 설명 | 상태 |
|------|------|------|
| `frontend/src/pages/LoginPage.js` | 로그인 페이지 | ✅ 완료 |
| `frontend/src/pages/DashboardPage.js` | 대시보드 페이지 | ✅ 완료 |
| `frontend/src/pages/CompanyListPage.js` | 업체 목록 페이지 | ✅ 완료 |
| `frontend/src/pages/CompanyCreatePage.js` | 업체 등록 페이지 | ✅ 완료 |
| `frontend/src/pages/UserListPage.js` | 사용자 목록 페이지 | ✅ 완료 |
| `frontend/src/pages/UserCreatePage.js` | 사용자 등록 페이지 | ✅ 완료 |
| `frontend/src/pages/MainLayout.js` | 메인 레이아웃 | ✅ 완료 |

### 🎨 **프론트엔드 컴포넌트**
| 파일 | 설명 | 상태 |
|------|------|------|
| `frontend/src/components/Sidebar.js` | 사이드바 컴포넌트 | ✅ 완료 |
| `frontend/src/components/ProtectedRoute.js` | 보호된 라우트 | ✅ 완료 |
| `frontend/src/contexts/AuthContext.js` | 인증 컨텍스트 | ✅ 완료 |
| `frontend/src/services/api.js` | API 서비스 | ✅ 완료 |

### 📝 **로그 및 데이터**
| 파일 | 설명 | 상태 |
|------|------|------|
| `logs/api.log` | API 로그 파일 | ✅ 완료 |
| `db.sqlite3` | SQLite 데이터베이스 | ✅ 완료 |

## 🧹 **정리 완료된 파일들**

### ✅ **삭제된 테스트 파일들**
- `templates/api_test.html` - API 테스트 페이지
- `templates/simple_test.html` - 간단한 API 테스트
- `check_db.py` - 데이터베이스 확인 스크립트
- `add_test_data.py` - 테스트 데이터 추가 스크립트
- `cleanup_test_files.py` - 테스트 파일 정리 스크립트
- `HB Admin 상품매뉴얼_20140902.pdf` - 불필요한 PDF 파일

### ✅ **삭제된 React 기본 파일들**
- `frontend/src/logo.svg` - React 기본 로고
- `frontend/src/setupTests.js` - 테스트 설정 파일
- `frontend/src/reportWebVitals.js` - 성능 측정 파일
- `frontend/src/App.test.js` - 기본 테스트 파일
- `frontend/src/index.css` - 기본 CSS 파일
- `frontend/public/logo192.png` - React 기본 이미지
- `frontend/public/logo512.png` - React 기본 이미지

### ✅ **삭제된 빈 디렉토리들**
- `frontend/src/utils/` - 빈 유틸리티 디렉토리
- `frontend/src/hooks/` - 빈 훅 디렉토리
- `templates/` - 빈 템플릿 디렉토리

## 🔗 **API 엔드포인트**

### 📊 **대시보드 API**
- `GET /api/dashboard/stats/` - 대시보드 통계
- `GET /api/dashboard/activities/` - 활동 내역

### 🏢 **업체 관리 API**
- `GET /api/companies/` - 업체 목록
- `POST /api/companies/` - 업체 생성
- `GET /api/companies/{id}/` - 업체 상세
- `PUT /api/companies/{id}/` - 업체 수정
- `DELETE /api/companies/{id}/` - 업체 삭제

### 👥 **사용자 관리 API**
- `GET /api/users/` - 사용자 목록
- `POST /api/users/` - 사용자 생성
- `GET /api/users/{id}/` - 사용자 상세
- `PUT /api/users/{id}/` - 사용자 수정
- `DELETE /api/users/{id}/` - 사용자 삭제
- `GET /api/companies/{id}/users/` - 특정 업체의 사용자 목록

### 🔐 **인증 API**
- `POST /api/auth/login/` - 로그인

## 📊 **현재 데이터 상태**

### 🏢 **업체 데이터**
- **총 업체 수**: 4개
  - 메인 본사 (headquarters)
  - 테스트 협력사 1 (agency)
  - 테스트 대리점 1 (dealer)
  - 테스트 판매점 1 (retail)

### 👥 **사용자 데이터**
- **총 사용자 수**: 4개
  - admin (관리자, 승인됨)
  - testuser1 (관리자, 승인됨)
  - testuser2 (직원, 대기 중)
  - testuser3 (관리자, 승인됨)

## 🚀 **실행 방법**

### 🔧 **백엔드 실행**
```bash
# 가상환경 활성화
& c:/Users/kci01/DN_Solution/venv/Scripts/Activate.ps1

# Django 서버 실행
python manage.py runserver 8001
```

### 🎨 **프론트엔드 실행**
```bash
# 프론트엔드 디렉토리 이동
cd frontend

# React 앱 실행
npm start
```

## 📝 **주요 기능**

### ✅ **완료된 기능**
- [x] Django 백엔드 API 구축
- [x] React 프론트엔드 구축
- [x] API 연결 및 통신
- [x] 로그인 시스템
- [x] 대시보드 통계
- [x] 업체 관리 (CRUD)
- [x] 사용자 관리 (CRUD)
- [x] 상세한 로깅 시스템
- [x] CORS 설정
- [x] Django Admin 연동

### 🔄 **진행 중인 기능**
- [ ] 프론트엔드 데이터 연동 확인
- [ ] 사용자 권한 시스템
- [ ] 실시간 알림 시스템

## 📚 **참고 자료**
- Django REST Framework 문서
- React 공식 문서
- Django Admin 커스터마이징 가이드 
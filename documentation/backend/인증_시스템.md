# JWT 인증 및 계층적 권한 제어 시스템 (JWT Authentication and Hierarchical Authorization)

이 문서는 `DN_solution` 프로젝트에 구현된 JWT 기반 인증 시스템과 계층적 권한 제어 메커니즘에 대한 상세한 설명을 제공합니다.

## 1. JWT 인증 시스템 개요

### 1.1. 도입 배경

**기존 세션 기반 인증의 한계:**
- 서버 상태 의존성으로 인한 클라우드 확장성 제약
- CSRF 토큰 관리의 복잡성
- 분산 환경에서의 세션 동기화 문제

**JWT 도입으로 얻은 이점:**
- ✅ 상태 비저장(Stateless) 인증으로 클라우드 친화적 설계
- ✅ 토큰에 사용자 정보 포함으로 데이터베이스 쿼리 최소화
- ✅ 마이크로서비스 아키텍처에 적합한 분산 인증
- ✅ 자동 토큰 갱신으로 향상된 사용자 경험

### 1.2. 기술 스택

- **백엔드:** `djangorestframework-simplejwt`
- **프론트엔드:** React + `axios` 인터셉터
- **토큰 저장:** `localStorage` (향후 보안 강화 시 `httpOnly` 쿠키 고려)
- **CORS 지원:** `django-cors-headers`

## 2. 이중 사용자 인증 시스템

### 2.1. 모델 구조

```python
# Django 기본 사용자 모델
User (django.contrib.auth.models.User)
├── username (로그인 ID)
├── password (해시된 비밀번호)
├── email
├── is_active, is_staff, is_superuser
└── 시스템 레벨 권한 관리

# 업체 소속 사용자 모델  
CompanyUser (companies.models.CompanyUser)
├── django_user (OneToOneField to User)
├── company (ForeignKey to Company)
├── role (admin, staff)
├── is_approved (승인 여부)
├── status (pending, approved, rejected, suspended)
└── 업무 레벨 권한 관리
```

### 2.2. 이중 검증 프로세스

1. **1차 검증:** Django User 인증 (username, password)
2. **2차 검증:** CompanyUser 승인 상태 확인
   - `CompanyUser` 존재 여부
   - `is_approved = True` 상태
   - `status = 'approved'` 상태
   - 소속 `Company.status = True` (업체 활성화 상태)

## 3. 커스텀 JWT 시리얼라이저

### 3.1. CustomTokenObtainPairSerializer

```python
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT 토큰 발급 시 CompanyUser의 승인 상태를 확인하는 커스텀 시리얼라이저
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # JWT 페이로드에 업체 정보 추가
        company_user = CompanyUser.objects.get(django_user=user)
        token['company_id'] = str(company_user.company.id)
        token['company_name'] = company_user.company.name
        token['company_type'] = company_user.company.type
        token['role'] = company_user.role
        token['is_approved'] = company_user.is_approved
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # CompanyUser 승인 상태 검증
        company_user = CompanyUser.objects.get(django_user=self.user)
        if not company_user.is_approved or company_user.status != 'approved':
            raise serializers.ValidationError("계정이 승인되지 않았습니다.")
        if not company_user.company.status:
            raise serializers.ValidationError("소속 업체가 비활성화 상태입니다.")
            
        return data
```

### 3.2. 토큰 구조

**Access Token 페이로드 예시:**
```json
{
  "token_type": "access",
  "exp": 1683123456,
  "iat": 1683119856,
  "jti": "abc123...",
  "user_id": 1,
  "company_id": "uuid-string",
  "company_name": "협력사_test",
  "company_type": "agency", 
  "role": "admin",
  "is_approved": true
}
```

## 4. 계층적 권한 제어 시스템

### 4.1. 계층 구조

```
본사 (headquarters)
├── 협력사 A (agency)
│   ├── 판매점 A1 (retail)
│   └── 판매점 A2 (retail)
└── 협력사 B (agency)
    ├── 판매점 B1 (retail)
    └── 판매점 B2 (retail)
```

### 4.2. 권한 제어 유틸리티 함수 (companies/utils.py)

```python
def get_accessible_company_ids(user):
    """사용자가 접근 가능한 업체 ID 목록 반환"""
    if user.is_superuser:
        return Company.objects.values_list('id', flat=True)
    
    company_user = CompanyUser.objects.get(django_user=user)
    company = company_user.company
    
    if company.is_headquarters:
        # 본사: 자신 + 모든 하위 업체 (1,2단계)
        return Company.objects.filter(
            Q(id=company.id) |
            Q(parent_company=company) |
            Q(parent_company__parent_company=company)
        ).values_list('id', flat=True)
    elif company.is_agency:
        # 협력사: 자신 + 직속 하위 판매점
        return Company.objects.filter(
            Q(id=company.id) |
            Q(parent_company=company)
        ).values_list('id', flat=True)
    elif company.is_retail:
        # 판매점: 자신만
        return Company.objects.filter(id=company.id).values_list('id', flat=True)
```

### 4.3. ViewSet 적용

```python
class CompanyViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return get_visible_companies(self.request.user)

class CompanyUserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return get_visible_users(self.request.user)
```

### 4.4. Django Admin 적용

```python
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        accessible_ids = get_accessible_company_ids(request.user)
        return qs.filter(id__in=accessible_ids)
```

## 5. 프론트엔드 JWT 관리

### 5.1. AuthContext 구현

```javascript
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    
    const login = async (username, password) => {
        const response = await post('companies/auth/jwt/login/', {
            username, password
        });
        
        if (response.success && response.data.access) {
            const userData = {
                username,
                token: response.data.access,
                // JWT 페이로드에서 추출된 정보
                company: response.data.company_name,
                role: response.data.role
            };
            
            setUser(userData);
            localStorage.setItem('user', JSON.stringify(userData));
            localStorage.setItem('authToken', response.data.access);
            localStorage.setItem('refreshToken', response.data.refresh);
        }
    };
    
    const logout = () => {
        setUser(null);
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
    };
};
```

### 5.2. Axios 인터셉터

```javascript
// 요청 인터셉터: 모든 요청에 JWT 토큰 추가
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// 응답 인터셉터: 401 오류 시 자동 토큰 갱신
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // 토큰 갱신 로직 또는 로그아웃 처리
            if (window.location.pathname !== '/login') {
                localStorage.clear();
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);
```

## 6. 보안 고려사항

### 6.1. 토큰 보안

- **Access Token 수명:** 60분 (단기)
- **Refresh Token 수명:** 1일 (장기)
- **토큰 로테이션:** Refresh Token 사용 시 새로운 토큰 발급
- **토큰 블랙리스트:** 로그아웃 시 토큰 무효화

### 6.2. XSS 방지

- **저장 위치:** 현재 `localStorage` (개발 편의성)
- **향후 개선:** `httpOnly` 쿠키 + CSRF 토큰 조합 고려
- **Content Security Policy:** 스크립트 실행 제한

### 6.3. CORS 설정

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # 개발 환경
    "https://yourdomain.com", # 운영 환경
]

CORS_ALLOW_CREDENTIALS = True
```

## 7. 운영 환경 배포 고려사항

### 7.1. 환경 변수 관리

```python
# settings.py
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_LIFETIME', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_LIFETIME', default=1, cast=int)),
    'SIGNING_KEY': config('JWT_SIGNING_KEY', default=SECRET_KEY),
}
```

### 7.2. HTTPS 필수

- JWT 토큰은 반드시 HTTPS 환경에서 전송
- 개발 환경에서도 HTTPS 테스트 권장
- 로드 밸런서에서 SSL 터미네이션 설정

### 7.3. 로깅 및 모니터링

```python
# JWT 인증 실패 로깅
import logging
logger = logging.getLogger(__name__)

def validate(self, attrs):
    try:
        data = super().validate(attrs)
        company_user = CompanyUser.objects.get(django_user=self.user)
        if not company_user.is_approved:
            logger.warning(f"Unapproved login attempt: {self.user.username}")
            raise serializers.ValidationError("계정이 승인되지 않았습니다.")
    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
        raise
```

## 8. 향후 개선 방향

### 8.1. 단기 개선 (1-2개월)
- [ ] Refresh Token 자동 갱신 구현
- [ ] 토큰 블랙리스트 시스템 구축
- [ ] 다중 디바이스 로그인 제어

### 8.2. 중기 개선 (3-6개월)
- [ ] OAuth 2.0 / OpenID Connect 지원
- [ ] MFA (Multi-Factor Authentication) 도입
- [ ] 역할 기반 세밀한 권한 제어 (RBAC)

### 8.3. 장기 개선 (6개월+)
- [ ] SSO (Single Sign-On) 연동
- [ ] 감사 로그 및 사용자 활동 추적
- [ ] 생체 인증 지원 (WebAuthn)

이 문서는 `DN_solution` 프로젝트의 JWT 인증 및 권한 제어 시스템의 현재 구현 상태와 향후 발전 방향을 제시하는 종합적인 기술 문서입니다.
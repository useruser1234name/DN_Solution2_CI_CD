 # DN_SOLUTION2 개발 환경 및 규칙

## 🖥️ 개발 환경 정보

### 현재 시스템 환경
- **OS**: Windows 11
- **개발 도구**: VSCode + Claude Code
- **Python**: 3.11.x
- **Node.js**: 18.x
- **Git**: 설치됨
- **Docker**: Docker Desktop for Windows

### 프로젝트 경로
```
C:\Users\kci01\DN_Solution2\
```

### 가상환경
```bash
# 가상환경 위치
C:\Users\kci01\DN_Solution2\venv\

# 활성화 명령 (Windows)
venv\Scripts\activate

# 비활성화
deactivate
```

## 📝 코딩 규칙 및 컨벤션

### Python/Django 코딩 규칙

#### 1. 명명 규칙
```python
# 클래스: PascalCase
class CompanyUser(models.Model):
    pass

# 함수/메서드: snake_case
def calculate_rebate_amount(policy, order):
    pass

# 상수: UPPER_SNAKE_CASE
MAX_REBATE_AMOUNT = 1000000
DEFAULT_CACHE_TIMEOUT = 300

# Private 메서드: 언더스코어 prefix
def _validate_hierarchy(self):
    pass
```

#### 2. 모델 구조
```python
class StandardModel(models.Model):
    """모든 모델의 표준 구조"""
    
    # 1. ID 필드 (UUID)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 2. 관계 필드 (ForeignKey, ManyToMany)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # 3. 데이터 필드
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 4. 상태 필드
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_active = models.BooleanField(default=True)
    
    # 5. 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """비즈니스 로직 검증"""
        pass
    
    def save(self, *args, **kwargs):
        """저장 시 처리"""
        self.full_clean()
        super().save(*args, **kwargs)
```

#### 3. View/ViewSet 구조
```python
class PolicyViewSet(viewsets.ModelViewSet):
    """정책 관리 ViewSet"""
    
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """권한별 쿼리셋 필터링"""
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        
        # 계층별 필터링
        return filter_by_hierarchy(self.queryset, user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """커스텀 액션"""
        instance = self.get_object()
        # 비즈니스 로직
        return Response({'status': 'approved'})
```

#### 4. Serializer 구조
```python
class PolicySerializer(serializers.ModelSerializer):
    """정책 시리얼라이저"""
    
    # 관계 필드 표시
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    # 계산 필드
    total_rebate = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_rebate(self, obj):
        """계산 필드 메서드"""
        return obj.calculate_total_rebate()
    
    def validate(self, data):
        """전체 검증"""
        # 비즈니스 로직 검증
        return data
```

### JavaScript/React 코딩 규칙

#### 1. 컴포넌트 구조
```jsx
// 함수형 컴포넌트 사용
import React, { useState, useEffect } from 'react';
import { Card, Button } from 'antd';
import api from '../../services/api';

const PolicyList = () => {
    // 1. State 선언
    const [policies, setPolicies] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // 2. Effect Hooks
    useEffect(() => {
        fetchPolicies();
    }, []);
    
    // 3. Handler 함수
    const fetchPolicies = async () => {
        setLoading(true);
        try {
            const response = await api.get('/policies/');
            setPolicies(response.data);
        } catch (error) {
            console.error('Error fetching policies:', error);
        } finally {
            setLoading(false);
        }
    };
    
    // 4. Render
    return (
        <Card title="정책 목록" loading={loading}>
            {/* 컴포넌트 내용 */}
        </Card>
    );
};

export default PolicyList;
```

#### 2. API 서비스 구조
```javascript
// services/api.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
});

// Request 인터셉터
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response 인터셉터
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // 토큰 갱신 로직
        }
        return Promise.reject(error);
    }
);

export default api;
```

## 🗂️ 파일 구조 규칙

### Django 앱 구조
```
app_name/
├── __init__.py
├── apps.py
├── models.py           # 모델 정의
├── views.py           # ViewSet/APIView
├── serializers.py     # 시리얼라이저
├── urls.py           # URL 패턴
├── permissions.py    # 커스텀 권한
├── tasks.py         # Celery 태스크
├── utils.py         # 유틸리티 함수
├── managers.py      # 커스텀 매니저
├── signals.py       # 시그널 핸들러
├── tests/
│   ├── test_models.py
│   ├── test_views.py
│   └── test_serializers.py
└── migrations/
```

### React 컴포넌트 구조
```
src/
├── components/        # 재사용 컴포넌트
│   ├── common/       # 공통 컴포넌트
│   ├── layouts/      # 레이아웃 컴포넌트
│   └── features/     # 기능별 컴포넌트
├── pages/            # 페이지 컴포넌트
├── services/         # API 서비스
├── store/           # 상태 관리
├── hooks/           # 커스텀 훅
├── utils/           # 유틸리티 함수
└── styles/          # 스타일 파일
```

## 🔍 로깅 규칙

### Python 로깅
```python
import logging

logger = logging.getLogger(__name__)

class PolicyView(APIView):
    def post(self, request):
        logger.info(f"[PolicyView.post] 정책 생성 요청 - 사용자: {request.user.username}")
        
        try:
            # 비즈니스 로직
            logger.info(f"[PolicyView.post] 정책 생성 성공 - ID: {policy.id}")
        except ValidationError as e:
            logger.warning(f"[PolicyView.post] 검증 실패 - {str(e)}")
        except Exception as e:
            logger.error(f"[PolicyView.post] 예상치 못한 오류 - {str(e)}", exc_info=True)
```

### JavaScript 로깅
```javascript
// 개발 환경에서만 로깅
const isDev = process.env.NODE_ENV === 'development';

const log = {
    info: (message, ...args) => isDev && console.log(`[INFO] ${message}`, ...args),
    warn: (message, ...args) => isDev && console.warn(`[WARN] ${message}`, ...args),
    error: (message, ...args) => console.error(`[ERROR] ${message}`, ...args),
};

// 사용 예시
log.info('API 호출 시작', { endpoint: '/api/policies/' });
```

## 🧪 테스트 규칙

### Django 테스트
```python
# tests/test_models.py
from django.test import TestCase
from ..models import Policy

class PolicyModelTest(TestCase):
    def setUp(self):
        """테스트 데이터 설정"""
        self.policy = Policy.objects.create(
            title="테스트 정책",
            description="테스트 설명"
        )
    
    def test_policy_creation(self):
        """정책 생성 테스트"""
        self.assertEqual(self.policy.title, "테스트 정책")
    
    def test_rebate_calculation(self):
        """리베이트 계산 테스트"""
        rebate = self.policy.calculate_rebate()
        self.assertGreater(rebate, 0)
```

### React 테스트
```javascript
// PolicyList.test.js
import { render, screen, waitFor } from '@testing-library/react';
import PolicyList from './PolicyList';

test('정책 목록이 표시됨', async () => {
    render(<PolicyList />);
    
    await waitFor(() => {
        expect(screen.getByText('정책 목록')).toBeInTheDocument();
    });
});
```

## 🚫 금지 사항

### 절대 하지 말아야 할 것들
1. **민감정보 평문 저장 금지**
2. **console.log에 민감정보 출력 금지**
3. **하드코딩된 비밀번호/API 키 금지**
4. **동기적 긴 작업 금지** (Celery 사용)
5. **N+1 쿼리 문제 방치 금지**
6. **try-except로 모든 예외 잡기 금지**
7. **테스트 없이 배포 금지**
8. **마이그레이션 없이 모델 수정 금지**

### 피해야 할 안티패턴
```python
# ❌ 나쁜 예
def bad_function():
    try:
        # 모든 코드
        pass
    except:  # 모든 예외 잡기
        pass

# ✅ 좋은 예
def good_function():
    try:
        # 특정 코드
        pass
    except ValidationError as e:
        logger.warning(f"검증 오류: {e}")
        raise
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise
```

## 📊 성능 최적화 체크리스트

### Django 최적화
- [ ] select_related() 사용 (1:1, FK)
- [ ] prefetch_related() 사용 (M:N, reverse FK)
- [ ] only(), defer() 로 필드 제한
- [ ] 인덱스 추가
- [ ] 캐시 활용
- [ ] 페이지네이션 적용
- [ ] 불필요한 쿼리 제거

### React 최적화
- [ ] React.memo() 사용
- [ ] useMemo(), useCallback() 활용
- [ ] 코드 스플리팅
- [ ] 이미지 최적화
- [ ] 불필요한 리렌더링 방지
- [ ] Virtual Scrolling (대량 목록)

## 🔐 보안 체크리스트

### Backend 보안
- [ ] SQL Injection 방지 (ORM 사용)
- [ ] XSS 방지 (템플릿 이스케이핑)
- [ ] CSRF 토큰 사용
- [ ] 민감정보 암호화
- [ ] Rate Limiting 적용
- [ ] 입력값 검증
- [ ] 권한 체크

### Frontend 보안
- [ ] XSS 방지 (dangerouslySetInnerHTML 주의)
- [ ] 민감정보 localStorage 저장 금지
- [ ] HTTPS 사용
- [ ] Content Security Policy
- [ ] 입력값 검증

## 📝 Git 커밋 메시지 규칙

### 커밋 메시지 형식
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type
- **feat**: 새로운 기능 추가
- **fix**: 버그 수정
- **docs**: 문서 수정
- **style**: 코드 포맷팅
- **refactor**: 코드 리팩토링
- **test**: 테스트 추가
- **chore**: 빌드 업무, 패키지 매니저 설정

### 예시
```
feat(policies): 리베이트 매트릭스 기능 추가

- RebateMatrix 모델 생성
- 요금제별 리베이트 계산 로직 구현
- API 엔드포인트 추가

Closes #123
```

## 🔄 작업 흐름

### 1. 기능 개발 흐름
```bash
# 1. 브랜치 생성
git checkout -b feat/rebate-matrix

# 2. 개발 작업
# - 모델 수정
# - 마이그레이션 생성
# - API 개발
# - 테스트 작성

# 3. 테스트 실행
python manage.py test

# 4. 커밋
git add .
git commit -m "feat(policies): 리베이트 매트릭스 추가"

# 5. 푸시
git push origin feat/rebate-matrix
```

### 2. 리뷰 체크리스트
- [ ] 코드 스타일 준수
- [ ] 테스트 통과
- [ ] 문서 업데이트
- [ ] 마이그레이션 파일 확인
- [ ] 성능 영향 검토
- [ ] 보안 이슈 확인

---

**문서 버전**: 1.0
**작성일**: 2024-12-24
**목적**: 개발 환경 설정 및 코딩 규칙 정의

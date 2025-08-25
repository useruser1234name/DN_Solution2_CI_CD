# 동적 필터링 시스템 사용 가이드

## Phase 5-3: 사용자별 맞춤 필터링 시스템

### 개요
정산 시스템에 사용자 권한과 회사 유형에 따른 동적 필터링 시스템이 구현되었습니다. 이 시스템은 각 사용자가 접근 가능한 데이터만 조회할 수 있도록 하며, 다양한 필터 옵션을 제공합니다.

### 주요 기능

#### 1. 사용자 권한 기반 필터링
- **본사**: 모든 정산 데이터 조회 가능
- **협력사**: 자신과 하위 판매점의 정산만 조회 가능
- **판매점**: 자신의 정산만 조회 가능

#### 2. 다양한 필터 옵션
- 기간별 필터링 (오늘, 주간, 월간, 분기, 연간, 사용자 지정)
- 회사 유형별 필터링
- 정산 상태별 필터링
- 정책별 필터링
- 금액 범위별 필터링
- 통신사별 필터링
- 그레이드 달성 여부별 필터링

### API 엔드포인트

#### 1. 필터 옵션 조회
```
GET /api/settlements/dynamic/filter_options/
```

**응답 예시:**
```json
{
  "period_types": [
    {"value": "today", "label": "오늘"},
    {"value": "week", "label": "최근 7일"},
    {"value": "month", "label": "이번 달"}
  ],
  "statuses": [
    {"value": "pending", "label": "정산 대기"},
    {"value": "approved", "label": "정산 승인"}
  ],
  "company_types": [
    {"value": "headquarters", "label": "본사"},
    {"value": "agency", "label": "협력사"},
    {"value": "retail", "label": "판매점"}
  ],
  "policies": [...],
  "companies": [...],
  "carriers": [...],
  "amount_range": {
    "min": 0,
    "max": 1000000
  },
  "user_permissions": {
    "company_type": "agency",
    "can_view_all": false,
    "can_view_agencies": false,
    "can_view_retailers": true
  }
}
```

#### 2. 복합 필터 적용
```
POST /api/settlements/dynamic/apply_filters/
```

**요청 예시:**
```json
{
  "filters": {
    "period_type": "month",
    "statuses": ["approved", "paid"],
    "company_types": ["agency", "retail"],
    "min_amount": 10000,
    "max_amount": 100000,
    "carriers": ["KT", "SKT"],
    "has_grade_bonus": true
  },
  "page": 1,
  "page_size": 20
}
```

**응답 예시:**
```json
{
  "results": [...],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "total_count": 95,
    "page_size": 20,
    "has_next": true,
    "has_previous": false
  },
  "applied_filters": {...},
  "summary": {
    "total_statistics": {
      "count": 95,
      "total_amount": 4750000.0,
      "average_amount": 50000.0,
      "total_grade_bonus": 475000.0
    },
    "status_breakdown": {...},
    "company_type_breakdown": {...}
  }
}
```

#### 3. 요약 통계 조회
```
GET /api/settlements/dynamic/summary_stats/?period_type=month&statuses[]=approved&statuses[]=paid
```

**응답 예시:**
```json
{
  "summary": {
    "total_statistics": {
      "count": 95,
      "total_amount": 4750000.0,
      "average_amount": 50000.0,
      "total_grade_bonus": 475000.0
    },
    "status_breakdown": {
      "approved": {"count": 45, "label": "정산 승인"},
      "paid": {"count": 50, "label": "입금 완료"}
    },
    "company_type_breakdown": {
      "agency": {"count": 30, "amount": 1500000.0},
      "retail": {"count": 65, "amount": 3250000.0}
    }
  },
  "applied_filters": {...}
}
```

#### 4. GET 방식 필터링
```
GET /api/settlements/dynamic/?period_type=month&statuses[]=approved&company_types[]=retail
```

### 필터 파라미터 상세

#### 기간 필터
- `period_type`: 미리 정의된 기간 타입
  - `today`: 오늘
  - `week`: 최근 7일
  - `month`: 이번 달
  - `quarter`: 이번 분기
  - `year`: 올해
  - `last_30_days`: 최근 30일
  - `last_90_days`: 최근 90일
  - `custom`: 사용자 지정 (start_date, end_date 필요)

- `start_date`: 시작일 (YYYY-MM-DD 형식)
- `end_date`: 종료일 (YYYY-MM-DD 형식)

#### 상태 필터
- `statuses`: 정산 상태 배열
  - `pending`: 정산 대기
  - `approved`: 정산 승인
  - `paid`: 입금 완료
  - `unpaid`: 미입금
  - `cancelled`: 취소됨

#### 회사 관련 필터
- `company_types`: 회사 유형 배열
  - `headquarters`: 본사
  - `agency`: 협력사
  - `retail`: 판매점

- `company_ids`: 특정 회사 ID 배열

#### 정책 및 통신사 필터
- `policy_ids`: 정책 ID 배열
- `carriers`: 통신사 배열 (`KT`, `SKT`, `LGU+`)

#### 금액 필터
- `min_amount`: 최소 금액
- `max_amount`: 최대 금액

#### 그레이드 필터
- `has_grade_bonus`: 그레이드 보너스 여부 (true/false)

### 사용 예시

#### 1. 프론트엔드에서 필터 옵션 로드
```javascript
// 사용자가 사용할 수 있는 필터 옵션 조회
const response = await fetch('/api/settlements/dynamic/filter_options/');
const filterOptions = await response.json();

// 필터 UI 구성
buildFilterUI(filterOptions);
```

#### 2. 필터 적용
```javascript
// 사용자가 선택한 필터 적용
const filters = {
  period_type: 'month',
  statuses: ['approved', 'paid'],
  company_types: ['retail'],
  min_amount: 10000
};

const response = await fetch('/api/settlements/dynamic/apply_filters/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    filters: filters,
    page: 1,
    page_size: 20
  })
});

const result = await response.json();
displaySettlements(result.results);
displaySummary(result.summary);
```

#### 3. 실시간 통계 업데이트
```javascript
// 필터 변경 시 실시간 통계 업데이트
const updateStats = async (filters) => {
  const params = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach(v => params.append(`${key}[]`, v));
    } else {
      params.append(key, value);
    }
  });
  
  const response = await fetch(`/api/settlements/dynamic/summary_stats/?${params}`);
  const stats = await response.json();
  
  updateDashboard(stats.summary);
};
```

### 권한 시스템

#### 접근 제어
- 각 사용자는 자신의 회사 유형에 따라 접근 가능한 데이터가 제한됩니다.
- 필터링 시스템은 자동으로 사용자 권한을 확인하고 적절한 데이터만 반환합니다.

#### 권한별 접근 범위
1. **슈퍼유저**: 모든 데이터 접근 가능
2. **본사 사용자**: 모든 정산 데이터 접근 가능
3. **협력사 사용자**: 자신과 하위 판매점 데이터만 접근 가능
4. **판매점 사용자**: 자신의 데이터만 접근 가능

### 성능 최적화

#### 쿼리 최적화
- `select_related`를 사용한 관련 객체 미리 로드
- 필터링 조건에 따른 인덱스 활용
- 페이지네이션을 통한 메모리 사용량 제한

#### 캐싱 전략
- 필터 옵션은 캐싱하여 반복 조회 성능 향상
- 사용자별 권한 정보 캐싱

### 에러 처리

#### 일반적인 에러 상황
1. **잘못된 날짜 형식**: 자동으로 무시되고 로그에 기록
2. **존재하지 않는 필터 값**: 유효한 값만 필터링에 적용
3. **권한 없는 데이터 접근**: 빈 결과 반환

#### 에러 응답 형식
```json
{
  "error": "에러 메시지",
  "details": "상세 에러 정보 (개발 모드에서만)"
}
```

### 확장 가능성

#### 새로운 필터 추가
1. `DynamicSettlementFilter` 클래스에 새 메서드 추가
2. `apply_multiple_filters` 메서드에 새 필터 로직 추가
3. `get_filter_options` 메서드에 새 옵션 추가

#### 커스텀 필터 구현
```python
def filter_by_custom_field(self, custom_values: List[str]) -> QuerySet:
    """커스텀 필드별 필터링"""
    queryset = self.apply_user_permissions()
    
    if not custom_values:
        return queryset
    
    return queryset.filter(custom_field__in=custom_values)
```

이 동적 필터링 시스템을 통해 사용자는 자신의 권한 범위 내에서 다양한 조건으로 정산 데이터를 조회하고 분석할 수 있습니다.

# 엑셀 내보내기 시스템 사용 가이드

## Phase 6: 사용자별 맞춤 엑셀 템플릿

### 개요
정산 시스템에 사용자 유형별 맞춤형 엑셀 내보내기 기능이 구현되었습니다. 이 시스템은 동적 필터링과 연동되어 사용자가 원하는 조건의 데이터를 최적화된 형태로 엑셀 파일로 내보낼 수 있습니다.

### 주요 기능

#### 1. 사용자별 맞춤 템플릿
- **본사용**: 전체 정산 현황, 회사별/정책별/상태별 요약
- **협력사용**: 받을/지급할 리베이트, 그레이드 현황, 판매점별 성과
- **판매점용**: 받을 리베이트, 월별/정책별 성과, 그레이드 현황

#### 2. 동적 필터링 연동
- Phase 5-3에서 구현된 동적 필터링 시스템과 완전 연동
- 필터 조건이 그대로 엑셀 내보내기에 적용

#### 3. 대용량 데이터 처리
- 청크 단위 처리로 메모리 사용량 최적화
- 최대 5만건까지 안정적 처리
- 진행 상황 실시간 모니터링

### API 엔드포인트

#### 1. 동적 필터 적용 엑셀 내보내기
```
POST /api/settlements/excel/export_with_filters/
```

**요청 예시:**
```json
{
  "filters": {
    "period_type": "month",
    "statuses": ["approved", "paid"],
    "company_types": ["agency", "retail"],
    "min_amount": 10000,
    "max_amount": 100000
  },
  "export_type": "auto"
}
```

**export_type 옵션:**
- `auto`: 사용자 유형에 따라 자동 선택
- `headquarters`: 본사용 템플릿 강제 적용
- `agency`: 협력사용 템플릿 강제 적용
- `retail`: 판매점용 템플릿 강제 적용

#### 2. 간단한 엑셀 내보내기 (GET 방식)
```
GET /api/settlements/excel/export_simple/?period_type=month&statuses[]=approved&statuses[]=paid
```

#### 3. 대용량 데이터셋 내보내기
```
POST /api/settlements/excel/export_large_dataset/
```

**요청 예시:**
```json
{
  "filters": {
    "period_type": "quarter",
    "statuses": ["approved", "paid"]
  },
  "chunk_size": 1000,
  "max_records": 50000
}
```

#### 4. 사용 가능한 템플릿 조회
```
GET /api/settlements/excel/export_templates/
```

**응답 예시:**
```json
{
  "templates": [
    {
      "type": "headquarters",
      "name": "본사 전체 정산 현황",
      "description": "전체 정산 데이터, 회사별/정책별/상태별 요약",
      "sheets": ["전체 정산 현황", "회사별 요약", "정책별 요약", "상태별 요약"]
    }
  ],
  "user_company_type": "headquarters",
  "recommended_template": "headquarters"
}
```

#### 5. 데이터 미리보기
```
POST /api/settlements/excel/preview_data/
```

**요청 예시:**
```json
{
  "filters": {
    "period_type": "month"
  },
  "preview_limit": 100
}
```

**응답 예시:**
```json
{
  "preview_data": [...],
  "total_count": 1250,
  "preview_count": 100,
  "summary": {...},
  "estimated_file_size": "1.2MB",
  "processing_time_estimate": "30초"
}
```

### 템플릿별 상세 구성

#### 본사용 템플릿 (HeadquartersExcelExporter)

**시트 구성:**
1. **전체 정산 현황**: 모든 정산 데이터의 상세 목록
2. **회사별 요약**: 회사별 정산 건수, 총액, 평균액, 보너스
3. **정책별 요약**: 정책별 성과 분석
4. **상태별 요약**: 정산 상태별 통계

**포함 정보:**
- 정산ID, 생성일, 회사명, 회사유형, 고객명
- 정책명, 통신사, 정산금액, 그레이드보너스, 총금액
- 상태, 승인자, 승인일, 메모

#### 협력사용 템플릿 (AgencyExcelExporter)

**시트 구성:**
1. **받을 리베이트**: 협력사가 받을 정산 내역
2. **지급할 리베이트**: 하위 판매점에 지급할 리베이트
3. **그레이드 현황**: 그레이드 달성 현황 및 예상 보너스
4. **판매점별 성과**: 하위 판매점 성과 분석 및 순위

**특화 기능:**
- 받을 금액 vs 지급할 금액 구분
- 판매점별 성장률 분석
- 그레이드 달성률 및 남은 목표

#### 판매점용 템플릿 (RetailExcelExporter)

**시트 구성:**
1. **받을 리베이트**: 판매점이 받을 정산 내역
2. **월별 성과**: 최근 12개월 성과 추이
3. **정책별 성과**: 정책별 성과 분석
4. **그레이드 현황**: 그레이드 달성 현황

**특화 기능:**
- 지급예정일 정보 포함
- 월별 성과 트렌드 분석
- 개인 그레이드 달성 전략

### 대용량 데이터 처리 (LargeDatasetExcelExporter)

#### 최적화 기능
1. **청크 단위 처리**: 1000건씩 나누어 처리
2. **메모리 최적화**: `constant_memory` 모드 사용
3. **진행 상황 모니터링**: 실시간 로그 출력
4. **자동 메모리 정리**: 청크 처리 후 메모리 해제

#### 처리 한계
- **최대 레코드**: 50,000건
- **권장 청크 크기**: 1,000건
- **메모리 사용량**: 약 100MB 이하 유지

#### 성능 가이드라인
| 데이터 크기 | 처리 방식 | 예상 시간 | 권장사항 |
|------------|----------|----------|----------|
| ~1,000건 | 표준 | 10초 이내 | 일반 내보내기 |
| ~10,000건 | 표준 | 1분 이내 | 일반 내보내기 |
| ~50,000건 | 청크 | 5분 이내 | 대용량 내보내기 |
| 50,000건+ | 분할 | - | 기간 분할 요청 |

### 사용 예시

#### 1. 프론트엔드에서 템플릿 선택
```javascript
// 사용 가능한 템플릿 조회
const templatesResponse = await fetch('/api/settlements/excel/export_templates/');
const templates = await templatesResponse.json();

// 템플릿 선택 UI 구성
buildTemplateSelector(templates);
```

#### 2. 필터 적용 엑셀 내보내기
```javascript
const exportData = {
  filters: {
    period_type: 'month',
    statuses: ['approved', 'paid'],
    company_types: ['retail']
  },
  export_type: 'auto'
};

const response = await fetch('/api/settlements/excel/export_with_filters/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(exportData)
});

// 파일 다운로드 처리
if (response.ok) {
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = response.headers.get('Content-Disposition').split('filename=')[1];
  a.click();
}
```

#### 3. 대용량 데이터 미리보기
```javascript
const previewData = {
  filters: {
    period_type: 'quarter'
  },
  preview_limit: 50
};

const response = await fetch('/api/settlements/excel/preview_data/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(previewData)
});

const preview = await response.json();

// 사용자에게 예상 정보 표시
showExportPreview({
  totalCount: preview.total_count,
  estimatedSize: preview.estimated_file_size,
  estimatedTime: preview.processing_time_estimate
});
```

#### 4. 대용량 데이터 내보내기
```javascript
const largeExportData = {
  filters: {
    period_type: 'year',
    statuses: ['approved', 'paid']
  },
  chunk_size: 1000,
  max_records: 30000
};

// 진행 상황 표시
showProgressDialog();

const response = await fetch('/api/settlements/excel/export_large_dataset/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(largeExportData)
});

hideProgressDialog();

if (response.ok) {
  downloadFile(response);
} else {
  showError('대용량 데이터 내보내기 실패');
}
```

### 에러 처리

#### 일반적인 에러 상황
1. **데이터 크기 초과**: 50,000건 초과 시 분할 요청 안내
2. **메모리 부족**: 청크 크기 조정 또는 필터 조건 세분화
3. **권한 없음**: 사용자 유형에 맞지 않는 템플릿 요청
4. **필터 오류**: 잘못된 필터 조건 검증 및 수정

#### 에러 응답 형식
```json
{
  "error": "데이터가 너무 많습니다. 기간을 나누어 요청해주세요.",
  "error_code": "DATA_TOO_LARGE",
  "suggestions": [
    "기간을 월 단위로 나누어 요청",
    "추가 필터 조건 적용",
    "대용량 내보내기 API 사용"
  ]
}
```

### 성능 최적화 팁

#### 1. 필터 최적화
- 기간 필터를 최우선으로 적용
- 상태 필터로 불필요한 데이터 제외
- 회사 유형 필터로 범위 축소

#### 2. 데이터 크기 관리
- 3개월 이내 데이터 권장
- 필요시 여러 번 나누어 내보내기
- 미리보기로 데이터 크기 확인

#### 3. 서버 리소스 고려
- 피크 시간대 대용량 내보내기 자제
- 청크 크기는 1000건 유지 권장
- 동시 내보내기 요청 제한

### 확장 가능성

#### 새로운 템플릿 추가
1. `BaseExcelExporter`를 상속한 새 클래스 생성
2. `generate_excel()` 메서드 구현
3. `SettlementExcelExporter`에 새 템플릿 추가

#### 커스텀 시트 추가
```python
def _write_custom_sheet(self, worksheet):
    """커스텀 시트 작성"""
    # 헤더 작성
    headers = ['컬럼1', '컬럼2', '컬럼3']
    
    # 데이터 작성
    for row, data in enumerate(custom_data, 1):
        for col, value in enumerate(data):
            worksheet.write(row, col, value, self.styles['left'])
```

#### 새로운 필터 연동
```python
def apply_custom_filters(self, custom_filters):
    """커스텀 필터 적용"""
    queryset = self.base_queryset
    
    if 'custom_field' in custom_filters:
        queryset = queryset.filter(custom_field=custom_filters['custom_field'])
    
    return queryset
```

이 엑셀 내보내기 시스템을 통해 사용자는 자신의 권한과 필요에 맞는 최적화된 형태로 정산 데이터를 엑셀 파일로 내보낼 수 있습니다.

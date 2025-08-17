"""
Company API 문서화

drf-spectacular를 사용한 OpenAPI 스키마 커스터마이징
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import status


# Company ViewSet 문서화
company_list_docs = extend_schema(
    summary="업체 목록 조회",
    description="""
    계층별 권한에 따라 접근 가능한 업체 목록을 조회합니다.
    
    **권한 규칙:**
    - 본사: 모든 하위 업체 조회 가능
    - 협력사: 자신과 하위 판매점만 조회 가능  
    - 판매점: 자신만 조회 가능
    
    **필터링 옵션:**
    - type: 업체 유형 (headquarters, agency, dealer, retail)
    - status: 운영 상태 (true/false)
    - search: 업체명 또는 코드로 검색
    """,
    parameters=[
        OpenApiParameter(
            name='type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='업체 유형',
            enum=['headquarters', 'agency', 'dealer', 'retail']
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='운영 상태'
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='업체명 또는 코드로 검색'
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='페이지 번호'
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='페이지 크기 (최대 50)'
        ),
    ],
    examples=[
        OpenApiExample(
            'Basic Usage',
            value={
                "count": 25,
                "total_pages": 3,
                "current_page": 1,
                "page_size": 10,
                "next": "http://api.example.com/companies/?page=2",
                "previous": None,
                "results": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "code": "A-241205-01",
                        "name": "메인 본사",
                        "type": "headquarters",
                        "parent_company": None,
                        "parent_company_name": None,
                        "status": True,
                        "child_companies_count": 5,
                        "users_count": 12,
                        "created_at": "2024-12-05T10:30:00Z"
                    }
                ]
            }
        )
    ],
    tags=['Company']
)

company_create_docs = extend_schema(
    summary="업체 생성",
    description="""
    새로운 업체를 생성합니다.
    
    **비즈니스 규칙:**
    - 본사: 상위 업체 없음
    - 협력사/대리점: 본사를 상위 업체로 설정
    - 판매점: 협력사 또는 대리점을 상위 업체로 설정
    
    **자동 생성 항목:**
    - 업체 코드: {타입접두사}-{YYMMDD}-{순번} 형식
    """,
    examples=[
        OpenApiExample(
            'Create Agency',
            value={
                "name": "서울 협력사",
                "type": "agency",
                "parent_company": "123e4567-e89b-12d3-a456-426614174000",
                "status": True
            }
        )
    ],
    tags=['Company']
)

company_retrieve_docs = extend_schema(
    summary="업체 상세 조회",
    description="""
    특정 업체의 상세 정보를 조회합니다.
    캐시를 활용하여 성능을 최적화합니다.
    """,
    tags=['Company']
)

company_stats_docs = extend_schema(
    summary="업체 통계",
    description="""
    사용자가 접근 가능한 업체들의 통계 정보를 제공합니다.
    
    **포함 정보:**
    - 전체 업체 수
    - 활성 업체 수
    - 승인 대기 사용자 수
    - 유형별 업체 수
    """,
    examples=[
        OpenApiExample(
            'Stats Response',
            value={
                "total_companies": 25,
                "active_companies": 23,
                "pending_approvals": 3,
                "by_type": {
                    "headquarters": 1,
                    "agency": 8,
                    "dealer": 5,
                    "retail": 11
                },
                "last_updated": "2024-12-05T15:30:00Z"
            }
        )
    ],
    tags=['Company']
)

company_hierarchy_docs = extend_schema(
    summary="업체 계층 구조",
    description="""
    특정 업체의 계층 구조를 조회합니다.
    상위 업체들과 하위 업체들을 모두 포함합니다.
    """,
    examples=[
        OpenApiExample(
            'Hierarchy Response',
            value={
                "company": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "서울 협력사",
                    "type": "agency",
                    "code": "B-241205-01"
                },
                "ancestors": [
                    {
                        "id": "456e7890-e89b-12d3-a456-426614174000",
                        "name": "메인 본사",
                        "type": "headquarters",
                        "code": "A-241201-01"
                    }
                ],
                "children": [
                    {
                        "id": "789e1234-e89b-12d3-a456-426614174000",
                        "name": "강남 판매점",
                        "type": "retail",
                        "code": "C-241206-01",
                        "status": True
                    }
                ]
            }
        )
    ],
    tags=['Company']
)

# CompanyUser ViewSet 문서화
user_list_docs = extend_schema(
    summary="업체 사용자 목록 조회",
    description="""
    계층별 권한에 따라 접근 가능한 사용자 목록을 조회합니다.
    
    **필터링 옵션:**
    - role: 사용자 역할 (admin, staff)
    - status: 승인 상태 (pending, approved, rejected)
    - company_id: 특정 업체의 사용자만 조회
    """,
    parameters=[
        OpenApiParameter(
            name='role',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='사용자 역할',
            enum=['admin', 'staff']
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='승인 상태',
            enum=['pending', 'approved', 'rejected']
        ),
        OpenApiParameter(
            name='company_id',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description='업체 ID'
        ),
    ],
    tags=['Company User']
)

user_approve_docs = extend_schema(
    summary="사용자 승인",
    description="""
    승인 대기 중인 사용자를 승인합니다.
    
    **승인 권한:**
    - 슈퍼유저: 모든 사용자 승인 가능
    - 본사 관리자: 모든 하위 업체 사용자 승인 가능
    - 협력사 관리자: 하위 판매점 사용자만 승인 가능
    - 판매점 관리자: 같은 업체 직원만 승인 가능
    """,
    responses={
        200: {
            "description": "승인 성공",
            "examples": {
                "application/json": {
                    "success": True,
                    "message": "사용자가 승인되었습니다."
                }
            }
        },
        403: {
            "description": "승인 권한 없음",
            "examples": {
                "application/json": {
                    "success": False,
                    "message": "해당 사용자를 승인할 권한이 없습니다."
                }
            }
        }
    },
    tags=['Company User']
)

user_pending_docs = extend_schema(
    summary="승인 대기 사용자 목록",
    description="""
    승인 대기 중인 사용자 목록을 조회합니다.
    캐시를 활용하여 빠른 응답을 제공합니다.
    """,
    examples=[
        OpenApiExample(
            'Pending Users',
            value=[
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "newuser",
                    "company_name": "서울 협력사",
                    "company_type": "agency",
                    "role": "staff",
                    "status": "pending",
                    "created_at": "2024-12-05T14:30:00Z"
                }
            ]
        )
    ],
    tags=['Company User']
)

# Authentication 문서화
login_docs = extend_schema(
    summary="JWT 로그인",
    description="""
    사용자 인증 후 JWT 토큰을 발급합니다.
    
    **보안 기능:**
    - 로그인 시도 제한 (5회 실패 시 30분 잠금)
    - 토큰 지문 생성 (탈취 방지)
    - 보안 감사 로깅
    
    **응답 토큰:**
    - access: 1시간 유효
    - refresh: 7일 유효
    """,
    examples=[
        OpenApiExample(
            'Login Request',
            value={
                "username": "admin",
                "password": "securepass123!"
            }
        ),
        OpenApiExample(
            'Login Response',
            value={
                "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "company": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "code": "A-241201-01",
                    "name": "메인 본사",
                    "type": "headquarters"
                },
                "role": "admin",
                "user_id": "456e7890-e89b-12d3-a456-426614174000"
            }
        )
    ],
    tags=['Authentication']
)

signup_admin_docs = extend_schema(
    summary="관리자 회원가입",
    description="""
    새로운 업체와 함께 관리자 계정을 생성합니다.
    
    **생성 프로세스:**
    1. 업체 생성 (코드 자동 생성)
    2. Django User 생성
    3. CompanyUser 생성 (승인 대기 상태)
    
    **승인 대기:**
    생성된 관리자는 상위 업체 관리자의 승인이 필요합니다.
    """,
    examples=[
        OpenApiExample(
            'Admin Signup',
            value={
                "username": "newadmin",
                "password": "SecurePass123!",
                "company_name": "새로운 협력사",
                "company_type": "agency",
                "parent_code": "A-241201-01",
                "email": "admin@newcompany.com"
            }
        )
    ],
    responses={
        201: {
            "description": "회원가입 성공",
            "examples": {
                "application/json": {
                    "success": True,
                    "message": "회원가입이 완료되었습니다. 상위 업체 관리자 승인 후 로그인할 수 있습니다.",
                    "company_code": "B-241205-01"
                }
            }
        }
    },
    tags=['Authentication']
)

signup_staff_docs = extend_schema(
    summary="직원 회원가입",
    description="""
    기존 본사에 직원 계정을 생성합니다.
    본사만 직원 가입이 가능합니다.
    """,
    examples=[
        OpenApiExample(
            'Staff Signup',
            value={
                "username": "newstaff",
                "password": "SecurePass123!",
                "company_code": "A-241201-01",
                "email": "staff@company.com"
            }
        )
    ],
    tags=['Authentication']
)

# Dashboard 문서화
dashboard_stats_docs = extend_schema(
    summary="대시보드 통계",
    description="""
    대시보드용 요약 통계를 제공합니다.
    사용자 권한에 따라 접근 가능한 데이터만 포함됩니다.
    """,
    examples=[
        OpenApiExample(
            'Dashboard Stats',
            value={
                "total_companies": 25,
                "pending_approvals": 3,
                "today_orders": 0,
                "active_companies": 23,
                "by_type": {
                    "headquarters": 1,
                    "agency": 8,
                    "dealer": 5,
                    "retail": 11
                }
            }
        )
    ],
    tags=['Dashboard']
)

dashboard_activities_docs = extend_schema(
    summary="대시보드 활동 내역",
    description="""
    최근 사용자 활동 내역을 제공합니다.
    기본적으로 24시간 이내 활동을 조회합니다.
    """,
    parameters=[
        OpenApiParameter(
            name='hours',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='조회할 시간 범위 (시간 단위)',
            default=24
        ),
    ],
    examples=[
        OpenApiExample(
            'Activity List',
            value=[
                {
                    "type": "user",
                    "message": "admin님이 로그인했습니다.",
                    "time": "2024-12-05 15:30",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000"
                },
                {
                    "type": "system",
                    "message": "시스템이 정상적으로 실행 중입니다.",
                    "time": "2024-12-05 16:00"
                }
            ]
        )
    ],
    tags=['Dashboard']
)

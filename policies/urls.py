# policies/urls.py
import logging
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PolicyViewSet, PolicyAssignmentViewSet

logger = logging.getLogger('policies')

# DefaultRouter를 사용하여 ViewSet 자동 등록
router = DefaultRouter()

# 각 ViewSet을 라우터에 등록
# 정책 관리 API 엔드포인트
router.register(r'policies', PolicyViewSet, basename='policy')

# 정책 배정 관리 API 엔드포인트
router.register(r'assignments', PolicyAssignmentViewSet, basename='policyassignment')

# URL 패턴 설정
urlpatterns = [
    # DRF Router가 자동 생성한 URL들을 포함
    path('', include(router.urls)),
]

logger.info("Policies 앱 URL 패턴이 성공적으로 등록되었습니다")

# 생성되는 URL 패턴들:
#
# 정책 관리 (policies/):
# - GET /api/policies/ - 정책 목록 조회
# - POST /api/policies/ - 새 정책 생성
# - GET /api/policies/{id}/ - 특정 정책 상세 조회
# - PUT /api/policies/{id}/ - 정책 정보 전체 수정
# - PATCH /api/policies/{id}/ - 정책 정보 부분 수정
# - DELETE /api/policies/{id}/ - 정책 삭제
# - POST /api/policies/{id}/generate_html/ - 정책 HTML 생성/재생성
# - POST /api/policies/{id}/toggle_expose/ - 정책 노출 상태 전환
# - POST /api/policies/bulk_delete/ - 정책 일괄 삭제
# - GET /api/policies/{id}/assignments/ - 특정 정책의 배정 목록 조회
# - POST /api/policies/{id}/bulk_assign/ - 정책을 여러 업체에 일괄 배정
#
# 정책 배정 관리 (assignments/):
# - GET /api/policies/assignments/ - 정책 배정 목록 조회
# - POST /api/policies/assignments/ - 새 정책 배정 생성
# - GET /api/policies/assignments/{id}/ - 특정 배정 상세 조회
# - PUT /api/policies/assignments/{id}/ - 배정 정보 전체 수정
# - PATCH /api/policies/assignments/{id}/ - 배정 정보 부분 수정
# - DELETE /api/policies/assignments/{id}/ - 정책 배정 해제
# - GET /api/policies/assignments/by_company/ - 특정 업체에 배정된 정책 목록 조회
# - GET /api/policies/assignments/by_policy/ - 특정 정책이 배정된 업체 목록 조회
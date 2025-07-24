# companies/urls.py
import logging
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, CompanyUserViewSet, CompanyMessageViewSet, model_test_ui

logger = logging.getLogger('companies')

# DefaultRouter를 사용하여 ViewSet 자동 등록
router = DefaultRouter()

# 각 ViewSet을 라우터에 등록
# 업체 관리 API 엔드포인트
router.register(r'companies', CompanyViewSet, basename='company')

# 업체 사용자 관리 API 엔드포인트  
router.register(r'users', CompanyUserViewSet, basename='companyuser')

# 업체 메시지 관리 API 엔드포인트
router.register(r'messages', CompanyMessageViewSet, basename='companymessage')

# URL 패턴 설정
urlpatterns = [
    # DRF Router가 자동 생성한 URL들을 포함
    path('', include(router.urls)),
    path('model-test/', model_test_ui, name='model_test_ui'),
]

logger.info("Companies 앱 URL 패턴이 성공적으로 등록되었습니다")

# 생성되는 URL 패턴들:
# 
# 업체 관리 (companies/):
# - GET /api/companies/ - 업체 목록 조회
# - POST /api/companies/ - 새 업체 생성
# - GET /api/companies/{id}/ - 특정 업체 상세 조회
# - PUT /api/companies/{id}/ - 업체 정보 전체 수정
# - PATCH /api/companies/{id}/ - 업체 정보 부분 수정
# - DELETE /api/companies/{id}/ - 업체 삭제
# - POST /api/companies/bulk_delete/ - 업체 일괄 삭제
# - POST /api/companies/{id}/toggle_status/ - 업체 상태 전환
# - GET /api/companies/{id}/users/ - 특정 업체의 사용자 목록 조회
#
# 업체 사용자 관리 (users/):
# - GET /api/companies/users/ - 업체 사용자 목록 조회
# - POST /api/companies/users/ - 새 업체 사용자 생성
# - GET /api/companies/users/{id}/ - 특정 사용자 상세 조회
# - PUT /api/companies/users/{id}/ - 사용자 정보 전체 수정
# - PATCH /api/companies/users/{id}/ - 사용자 정보 부분 수정
# - DELETE /api/companies/users/{id}/ - 사용자 삭제
#
# 업체 메시지 관리 (messages/):
# - GET /api/companies/messages/ - 메시지 목록 조회
# - POST /api/companies/messages/ - 새 메시지 발송
# - GET /api/companies/messages/{id}/ - 특정 메시지 상세 조회
# - PUT /api/companies/messages/{id}/ - 메시지 정보 수정
# - PATCH /api/companies/messages/{id}/ - 메시지 정보 부분 수정
# - DELETE /api/companies/messages/{id}/ - 메시지 삭제
# - POST /api/companies/messages/send_bulk_message/ - 일괄 메시지 발송
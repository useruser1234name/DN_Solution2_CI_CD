# orders/urls.py
import logging
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, OrderMemoViewSet, InvoiceViewSet

logger = logging.getLogger('orders')

# DefaultRouter를 사용하여 ViewSet 자동 등록
router = DefaultRouter()

# 각 ViewSet을 라우터에 등록
# 주문서 관리 API 엔드포인트
router.register(r'orders', OrderViewSet, basename='order')

# 주문 메모 관리 API 엔드포인트
router.register(r'memos', OrderMemoViewSet, basename='ordermemo')

# 송장 정보 관리 API 엔드포인트
router.register(r'invoices', InvoiceViewSet, basename='invoice')

# URL 패턴 설정
urlpatterns = [
    # DRF Router가 자동 생성한 URL들을 포함
    path('', include(router.urls)),
]

logger.info("Orders 앱 URL 패턴이 성공적으로 등록되었습니다")

# 생성되는 URL 패턴들:
#
# 주문서 관리 (orders/):
# - GET /api/orders/ - 주문서 목록 조회
#   * 필터링: status, apply_type, carrier, company, policy, created_by
#   * 검색: customer_name, customer_phone, model_name, memo
#   * 추가 필터: start_date, end_date, has_invoice
# - POST /api/orders/ - 새 주문서 생성
# - GET /api/orders/{id}/ - 특정 주문서 상세 조회
# - PUT /api/orders/{id}/ - 주문서 정보 전체 수정
# - PATCH /api/orders/{id}/ - 주문서 정보 부분 수정
# - DELETE /api/orders/{id}/ - 주문서 삭제
# - POST /api/orders/{id}/update_status/ - 주문 상태 업데이트
# - POST /api/orders/bulk_status_update/ - 주문 일괄 상태 업데이트
# - POST /api/orders/bulk_delete/ - 주문 일괄 삭제
# - GET /api/orders/{id}/memos/ - 특정 주문의 메모 목록 조회
# - GET /api/orders/statistics/ - 주문 통계 조회
#
# 주문 메모 관리 (memos/):
# - GET /api/orders/memos/ - 주문 메모 목록 조회
#   * 필터링: order, created_by
#   * 검색: memo, order__customer_name
# - POST /api/orders/memos/ - 새 주문 메모 생성
# - GET /api/orders/memos/{id}/ - 특정 메모 상세 조회
# - PUT /api/orders/memos/{id}/ - 메모 정보 전체 수정
# - PATCH /api/orders/memos/{id}/ - 메모 정보 부분 수정
# - DELETE /api/orders/memos/{id}/ - 메모 삭제
#
# 송장 정보 관리 (invoices/):
# - GET /api/orders/invoices/ - 송장 목록 조회
#   * 필터링: courier, order__company, order__status
#   * 검색: invoice_number, order__customer_name, recipient_name
#   * 추가 필터: is_delivered
# - POST /api/orders/invoices/ - 새 송장 생성
# - GET /api/orders/invoices/{id}/ - 특정 송장 상세 조회
# - PUT /api/orders/invoices/{id}/ - 송장 정보 전체 수정
# - PATCH /api/orders/invoices/{id}/ - 송장 정보 부분 수정
# - DELETE /api/orders/invoices/{id}/ - 송장 삭제
# - POST /api/orders/invoices/{id}/mark_delivered/ - 배송 완료 처리
# - GET /api/orders/invoices/delivery_statistics/ - 배송 통계 조회
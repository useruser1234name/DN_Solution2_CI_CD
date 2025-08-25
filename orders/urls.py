"""
통신사 주문 관리 시스템 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .order_views import OrderViewSet, OrderMemoViewSet, InvoiceViewSet

# DRF 라우터 설정
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-memos', OrderMemoViewSet, basename='order-memo')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

# app_name = 'orders'

urlpatterns = [
    # DRF ViewSet 라우트 (직접 노출)
    path('', include(router.urls)),
    
    # 주문서 양식 조회
    path('form-template/<uuid:policy_id>/', views.OrderFormTemplateView.as_view(), name='order_form_template'),
]
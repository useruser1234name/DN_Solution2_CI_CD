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
    
    # 통신사 주문 관리 (기존 TelecomOrder)
    path('telecom-orders/', views.TelecomOrderCreateView.as_view(), name='telecom_order_create'),
    path('telecom-orders/<uuid:order_id>/', views.TelecomOrderDetailView.as_view(), name='telecom_order_detail'),
    path('telecom-orders/<uuid:order_id>/status/', views.TelecomOrderStatusUpdateView.as_view(), name='telecom_order_status_update'),
    path('telecom-orders/list/', views.TelecomOrderListView.as_view(), name='telecom_order_list'),
]
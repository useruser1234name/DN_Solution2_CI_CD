"""
통신사 주문 관리 시스템 URL 설정
"""

from django.urls import path
from . import views

# app_name = 'orders'

urlpatterns = [
    # 주문 생성
    path('api/orders/', views.TelecomOrderCreateView.as_view(), name='order_create'),
    
    # 주문 상세 조회
    path('api/orders/<uuid:order_id>/', views.TelecomOrderDetailView.as_view(), name='order_detail'),
    
    # 주문 상태 업데이트 (본사 전용)
    path('api/orders/<uuid:order_id>/status/', views.TelecomOrderStatusUpdateView.as_view(), name='order_status_update'),
    
    # 주문 목록 조회
    path('api/orders/list/', views.TelecomOrderListView.as_view(), name='order_list'),
]
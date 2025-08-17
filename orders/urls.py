from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.OrderViewSet)  # 빈 문자열로 변경하여 /api/orders/로 직접 접근 가능
router.register(r'memos', views.OrderMemoViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'requests', views.OrderRequestViewSet)

app_name = 'orders'

urlpatterns = [
    path('', include(router.urls)),
] 
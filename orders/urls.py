from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet)
router.register(r'memos', views.OrderMemoViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'requests', views.OrderRequestViewSet)

app_name = 'orders'

urlpatterns = [
    path('', include(router.urls)),
] 
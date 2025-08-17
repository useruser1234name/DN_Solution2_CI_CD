"""
정산 관리 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SettlementViewSet, SettlementBatchViewSet

router = DefaultRouter()
router.register(r'', SettlementViewSet, basename='settlement')
router.register(r'batches', SettlementBatchViewSet, basename='settlementbatch')

urlpatterns = [
    path('', include(router.urls)),
]
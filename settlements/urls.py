"""
정산 관리 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SettlementViewSet,
    SettlementBatchViewSet,
    CommissionGradeTrackingViewSet,
    GradeAchievementHistoryViewSet,
    GradeBonusSettlementViewSet
)

router = DefaultRouter()
router.register(r'', SettlementViewSet, basename='settlement')
router.register(r'batches', SettlementBatchViewSet, basename='settlementbatch')
router.register(r'grade-trackings', CommissionGradeTrackingViewSet, basename='gradetracking')
router.register(r'grade-histories', GradeAchievementHistoryViewSet, basename='gradehistory')
router.register(r'grade-bonus-settlements', GradeBonusSettlementViewSet, basename='gradebonussettlement')

urlpatterns = [
    path('', include(router.urls)),
]
"""
정산 관리 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SettlementViewSet,
    SettlementBatchViewSet,
    DynamicFilteredSettlementViewSet,
    AdvancedExcelExportViewSet
)
from .data_warehouse_views import (
    CommissionFactViewSet,
    CommissionGradeTrackingViewSet as GradeTrackingViewSet,
    GradeBonusSettlementViewSet as CommissionGradeBonusSettlementViewSet
)
from .dashboard_views import (
    HeadquartersSettlementDashboard,
    AgencySettlementDashboard,
    RetailSettlementDashboard,
    SettlementAnalyticsDashboard
)
from .agency_advanced_views import AgencyAdvancedDashboard
from .retail_advanced_views import RetailAdvancedDashboard, RetailAnalyticsAPI

router = DefaultRouter()
router.register(r'', SettlementViewSet, basename='settlement')
router.register(r'batches', SettlementBatchViewSet, basename='settlementbatch')
router.register(r'commission-facts', CommissionFactViewSet, basename='commissionfact')
router.register(r'grade-trackings', GradeTrackingViewSet, basename='gradetracking')
router.register(r'grade-bonus-settlements', CommissionGradeBonusSettlementViewSet, basename='gradebonussettlement')
router.register(r'dynamic', DynamicFilteredSettlementViewSet, basename='dynamic-settlement')
router.register(r'excel', AdvancedExcelExportViewSet, basename='excel-export')

urlpatterns = [
    path('', include(router.urls)),
    
    # 대시보드 엔드포인트
    path('dashboard/headquarters/', HeadquartersSettlementDashboard.as_view(), name='headquarters-dashboard'),
    path('dashboard/agency/', AgencySettlementDashboard.as_view(), name='agency-dashboard'),
    path('dashboard/retail/', RetailSettlementDashboard.as_view(), name='retail-dashboard'),
    path('dashboard/analytics/', SettlementAnalyticsDashboard.as_view(), name='analytics-dashboard'),
    
    # 고급 협력사 대시보드 엔드포인트
    path('dashboard/agency/advanced/', AgencyAdvancedDashboard.as_view(), name='agency-advanced-dashboard'),
    
    # 고급 소매점 대시보드 엔드포인트  
    path('dashboard/retail/advanced/', RetailAdvancedDashboard.as_view(), name='retail-advanced-dashboard'),
    path('analytics/retail/', RetailAnalyticsAPI.as_view(), name='retail-analytics'),
]
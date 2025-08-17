from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .viewsets import CompanyViewSet, CompanyUserViewSet
from .auth_views import (
    CustomTokenObtainPairView,
    SignupChoiceView,
    AdminSignupView,
    StaffSignupView
)

# ViewSet 라우터 설정
router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'users', CompanyUserViewSet, basename='company-user')

urlpatterns = [
    # ViewSet URL 포함
    path('', include(router.urls)),
    
    # 레거시 호환성을 위한 URL들
    path('users/<uuid:user_id>/approval/', views.UserApprovalView.as_view(), name='user-approval'),
    path('api/child-companies/', views.ChildCompaniesView.as_view(), name='child_companies'),
    
    # 대시보드 관련 URL
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard_stats'),
    path('dashboard/activities/', views.DashboardActivitiesView.as_view(), name='dashboard_activities'),
    
    # 회원가입 관련 URL
    path('signup/', SignupChoiceView.as_view(), name='signup_choice'),
    path('signup/admin/', AdminSignupView.as_view(), name='admin_signup'),
    path('signup/staff/', StaffSignupView.as_view(), name='staff_signup'),
    
    # JWT 인증 URL
    path('auth/jwt/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] 
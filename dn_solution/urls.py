"""
URL configuration for dn_solution project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from companies import views
from policies.viewsets import PolicyViewSet
from dn_solution.cache_views import (
    CacheStatusView, clear_cache, warm_up_cache, cache_performance_test,
    cache_keys_list, health_check, cache_dashboard, invalidate_cache_pattern
)
from dn_solution.auth_views import (
    EnhancedTokenObtainPairView, EnhancedTokenRefreshView, LogoutView,
    TokenInfoView, generate_api_token, revoke_tokens
)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

# REST Framework Router 설정
router = routers.DefaultRouter()
router.register(r'policies', PolicyViewSet, basename='policy')

@csrf_exempt
@require_http_methods(["GET"])
def simple_health_check(request):
    """간단한 헬스체크 (Docker용, 인증 불필요)"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'DN_SOLUTION2',
        'timestamp': '2025-08-12T11:58:00Z'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', simple_health_check, name='simple-health-check'),  # Docker health check용
    path('api/', include(router.urls)),  # REST API Router (policies viewset) - 기본 CRUD를 먼저
    path('api/companies/', include('companies.urls')),
    path('api/policies/', include('policies.urls', namespace='api-policies')),  # 추가 정책 관련 API들 (리베이트 매트릭스 등)
    path('policies/', include('policies.urls', namespace='frontend-policies')),  # 프론트엔드 호환성을 위한 추가 경로
    path('orders/', include('orders.urls')),  # 프론트엔드 호환성을 위한 추가 경로
    path('api/orders/', include('orders.urls')),
    path('settlements/', include('settlements.urls')),  # 프론트엔드 호환성을 위한 추가 경로
    path('api/settlements/', include('settlements.urls')),
    # path('api/inventory/', include('inventory.urls')),  # 제거 - MVP에 불필요
    # path('api/messaging/', include('messaging.urls')),  # 제거 - MVP에 불필요
    # Dashboard API 경로 직접 정의
    path('api/dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/dashboard/activities/', views.DashboardActivitiesView.as_view(), name='dashboard-activities'),
    
    # JWT 인증 API
    path('api/auth/login/', EnhancedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', EnhancedTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/token-info/', TokenInfoView.as_view(), name='token-info'),
    path('api/auth/generate-api-token/', generate_api_token, name='generate-api-token'),
    path('api/auth/revoke-tokens/', revoke_tokens, name='revoke-tokens'),
    
    # 캐시 관리 API
    path('api/admin/cache/status/', CacheStatusView.as_view(), name='cache-status'),
    path('api/admin/cache/clear/', clear_cache, name='cache-clear'),
    path('api/admin/cache/warm-up/', warm_up_cache, name='cache-warm-up'),
    path('api/admin/cache/performance/', cache_performance_test, name='cache-performance'),
    path('api/admin/cache/keys/', cache_keys_list, name='cache-keys-list'),
    path('api/admin/cache/invalidate/', invalidate_cache_pattern, name='cache-invalidate'),
    path('api/admin/cache/dashboard/', cache_dashboard, name='cache-dashboard'),
    path('api/health/cache/', health_check, name='cache-health-check'),  # 인증 필요
    
    # React 앱 서빙 (모든 다른 경로는 React 앱으로 라우팅)
    path('', TemplateView.as_view(template_name='index.html'), name='react-app'),
]

# 정적 파일 서빙 (개발 환경)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

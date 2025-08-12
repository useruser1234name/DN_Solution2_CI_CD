from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    # 정책 목록 및 관리
    path('', views.PolicyListView.as_view(), name='policy_list'),
    path('create/', views.PolicyCreateView.as_view(), name='policy_create'),
    path('<uuid:pk>/', views.PolicyDetailView.as_view(), name='policy_detail'),
    path('<uuid:pk>/edit/', views.PolicyUpdateView.as_view(), name='policy_update'),
    path('<uuid:pk>/delete/', views.PolicyDeleteView.as_view(), name='policy_delete'),
    
    # 정책 배포 관리
    path('<uuid:pk>/deploy/', views.policy_deploy, name='policy_deploy'),
    path('<uuid:pk>/bulk-deploy/', views.policy_bulk_deploy, name='policy_bulk_deploy'),
    path('<uuid:pk>/bulk-remove/', views.policy_bulk_remove, name='policy_bulk_remove'),
    path('available-companies/', views.get_available_companies, name='get_available_companies'),
    
    # 정책 상태 토글 API
    path('<uuid:pk>/toggle-expose/', views.toggle_policy_expose, name='toggle_expose'),
    path('<uuid:pk>/toggle-premium-expose/', views.toggle_premium_market_expose, name='toggle_premium_expose'),
    path('<uuid:pk>/regenerate-html/', views.regenerate_html, name='regenerate_html'),
    
    # 정책별 안내사항 및 배정 관리
    path('<uuid:policy_pk>/notices/', views.policy_notice_list, name='policy_notices'),
    path('<uuid:policy_pk>/assignments/', views.policy_assignment_list, name='policy_assignments'),
    
    # 정책 노출 및 리베이트 관리 (새로 추가)
    path('<uuid:policy_id>/exposure/', views.PolicyExposureView.as_view(), name='policy_exposure'),
    path('agency/rebate/', views.AgencyRebateView.as_view(), name='agency_rebate'),
    path('<uuid:policy_id>/order-form/', views.OrderFormBuilderView.as_view(), name='order_form_builder'),
    
    # API 엔드포인트
    path('api/list/', views.policy_api_list, name='api_list'),
    path('api/create/', views.PolicyApiCreateView.as_view(), name='api_create'),
    path('api/check-duplicate/', views.check_duplicate_policy, name='check_duplicate'),
    
    # 통계 및 대시보드
    path('statistics/', views.policy_statistics, name='statistics'),
] 
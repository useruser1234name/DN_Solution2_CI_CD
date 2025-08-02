from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet)
router.register(r'users', views.CompanyUserViewSet)

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/activities/', views.DashboardActivitiesView.as_view(), name='dashboard-activities'),
    path('users/<uuid:user_id>/approval/', views.UserApprovalView.as_view(), name='user-approval'),
    path('', include(router.urls)),
] 
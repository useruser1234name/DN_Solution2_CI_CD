from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet)
router.register(r'users', views.CompanyUserViewSet)

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/csrf/', views.CSRFTokenView.as_view(), name='csrf_token'),
    path('users/<uuid:user_id>/approval/', views.UserApprovalView.as_view(), name='user-approval'),
    # 회원가입 관련 URL
    path('signup/', views.SignupChoiceView.as_view(), name='signup_choice'),
    path('signup/admin/', views.AdminSignupView.as_view(), name='admin_signup'),
    path('signup/staff/', views.StaffSignupView.as_view(), name='staff_signup'),
    path('', include(router.urls)),
] 
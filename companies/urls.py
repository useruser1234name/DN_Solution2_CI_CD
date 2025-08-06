from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .views import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet)
router.register(r'users', views.CompanyUserViewSet)

urlpatterns = [
    path('users/<uuid:user_id>/approval/', views.UserApprovalView.as_view(), name='user-approval'),
    # 회원가입 관련 URL
    path('signup/', views.SignupChoiceView.as_view(), name='signup_choice'),
    path('signup/admin/', views.AdminSignupView.as_view(), name='admin_signup'),
    path('signup/staff/', views.StaffSignupView.as_view(), name='staff_signup'),
    path('', include(router.urls)),
]

urlpatterns += [
    path('auth/jwt/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] 
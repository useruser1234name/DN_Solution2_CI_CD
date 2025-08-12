import logging
import json
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Company, CompanyUser
from .serializers import CompanySerializer, CompanyUserSerializer
from core.filters import CompanyFilter, CompanyUserFilter
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.http import JsonResponse

# 로거 설정
logger = logging.getLogger('companies')

# Create your views here.

from .utils import get_visible_companies, get_visible_users

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]
    filterset_class = CompanyFilter
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at', 'type']
    ordering = ['-created_at']

    def get_queryset(self):
        # 계층별 권한 필터링이 적용된 회사 목록 반환
        queryset = get_visible_companies(self.request.user)
        # N+1 쿼리 방지를 위한 select_related/prefetch_related 추가
        queryset = queryset.select_related('parent_company').prefetch_related(
            'child_companies',
            'users',
            'users__django_user'
        )
        return queryset

class CompanyUserViewSet(viewsets.ModelViewSet):
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CompanyUserFilter
    search_fields = ['username', 'django_user__email']
    ordering_fields = ['username', 'created_at', 'role']
    ordering = ['-created_at']

    def get_queryset(self):
        # 계층별 권한 필터링이 적용된 사용자 목록 반환
        queryset = get_visible_users(self.request.user)
        # N+1 쿼리 방지를 위한 select_related/prefetch_related 추가
        queryset = queryset.select_related(
            'company',
            'company__parent_company',
            'django_user'
        )
        return queryset

class UserApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """사용자 승인/거부 API - 계층 구조에 따른 권한 제한"""
        approver_user = request.user
        action = request.data.get('action')

        try:
            target_user = CompanyUser.objects.get(id=user_id)
        except CompanyUser.DoesNotExist:
            return Response({'error': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if not self._can_approve_user(approver_user, target_user):
            return Response({'error': '해당 사용자를 승인할 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        if action == 'approve':
            target_user.status = 'approved'
            target_user.is_approved = True
        elif action == 'reject':
            target_user.status = 'rejected'
            target_user.is_approved = False
        else:
            return Response({'error': '잘못된 액션입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        target_user.save()
        return Response({'message': f'사용자가 {action}되었습니다.'}, status=status.HTTP_200_OK)

    def _can_approve_user(self, approver_user, target_user):
        """승인 권한 검증: 상위 관리자만 하위 사용자 승인 가능"""
        if approver_user.is_superuser:
            return True

        try:
            approver_company_user = CompanyUser.objects.get(django_user=approver_user)
        except CompanyUser.DoesNotExist:
            return False

        # 승인자는 관리자여야 함
        if approver_company_user.role != 'admin':
            return False

        # 대상 사용자의 회사가 승인자 회사의 하위 회사여야 함
        approver_company = approver_company_user.company
        target_company = target_user.company
        
        # 자기 자신 또는 같은 회사 직원은 승인 가능
        if approver_company == target_company:
            return True

        # 하위 회사인지 확인
        parent = target_company.parent_company
        while parent:
            if parent == approver_company:
                return True
            parent = parent.parent_company

        return False

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.authtoken.models import Token

# LoginView, CSRFTokenView 등 세션/CSRF 기반 인증 관련 APIView 제거

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    커스텀 JWT 로그인 뷰
    승인된 CompanyUser만 로그인 가능
    """
    serializer_class = CustomTokenObtainPairSerializer

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """대시보드 통계 데이터를 반환합니다."""
        user = request.user
        visible_companies = get_visible_companies(user)
        visible_users = get_visible_users(user)

        stats = {
            'total_companies': visible_companies.count(),
            'pending_approvals': visible_users.filter(status='pending').count(),
            'today_orders': 0,  # TODO: orders 앱에서 실제 주문 수 계산
        }
        return Response(stats)

class DashboardActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """대시보드 활동 내역을 반환합니다."""
        user = request.user
        visible_users = get_visible_users(user)

        recent_logins = visible_users.filter(
            last_login__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-last_login')[:5]

        activities = [
            {
                'type': 'user',
                'message': f'{u.username}님이 로그인했습니다.',
                'time': u.last_login.strftime('%Y-%m-%d %H:%M')
            }
            for u in recent_logins
        ]

        activities.append({
            'type': 'system',
            'message': '시스템이 정상적으로 실행 중입니다.',
            'time': timezone.now().strftime('%Y-%m-%d %H:%M')
        })

        return Response(activities)

class SignupChoiceView(APIView):
    """회원가입 유형 선택 페이지"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """회원가입 유형 선택 페이지 렌더링"""
        return render(request, 'companies/signup_choice.html')

class AdminSignupView(APIView):
    """관리자 회원가입"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """관리자 회원가입 페이지 렌더링"""
        return render(request, 'companies/admin_signup.html')
    
    def post(self, request):
        """관리자 회원가입 처리"""
        logger.info(f"[AdminSignupView] 관리자 회원가입 요청 - IP: {request.META.get('REMOTE_ADDR')}")
        
        try:
            # 필수 필드 검증
            required_fields = ['username', 'password', 'company_name', 'company_type']
            for field in required_fields:
                if not request.data.get(field):
                    return Response(
                        {'error': f'{field}는 필수 입력 사항입니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            username = request.data.get('username')
            password = request.data.get('password')
            company_name = request.data.get('company_name')
            company_type = request.data.get('company_type')
            parent_code = request.data.get('parent_code', '')  # 부모 코드 (선택적)
            
            # 사용자명 중복 검사
            if User.objects.filter(username=username).exists():
                return Response(
                    {'error': '이미 사용 중인 사용자명입니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 본사가 아닌 경우 부모 코드 필수
            if company_type != 'headquarters' and not parent_code:
                return Response(
                    {'error': '본사가 아닌 경우 상위 업체 코드를 입력해야 합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 부모 업체 검증 (본사가 아닌 경우)
            parent_company = None
            if company_type != 'headquarters':
                try:
                    parent_company = Company.objects.get(code=parent_code, status=True)
                    # 부모 업체 타입 검증
                    if company_type == 'agency' and parent_company.type != 'headquarters':
                        return Response(
                            {'error': '협력사는 본사 하위에만 생성할 수 있습니다.'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    elif company_type == 'dealer' and parent_company.type != 'headquarters':
                        return Response(
                            {'error': '대리점은 본사 하위에만 생성할 수 있습니다.'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    elif company_type == 'retail' and parent_company.type not in ['agency', 'dealer']:
                        return Response(
                            {'error': '판매점은 협력사 또는 대리점 하위에만 생성할 수 있습니다.'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except Company.DoesNotExist:
                    return Response(
                        {'error': '유효하지 않은 상위 업체 코드입니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Django User 생성
            django_user = User.objects.create_user(
                username=username,
                password=password
            )
            
            # 업체 생성 (코드는 자동 생성됨)
            company_data = {
                'name': company_name,
                'type': company_type,
                'status': True,
                'visible': True
            }
            
            # 부모 업체 설정
            if parent_company:
                company_data['parent_company'] = parent_company
            
            company = Company.objects.create(**company_data)
            
            # CompanyUser 생성 (승인 대기 상태)
            company_user = CompanyUser.objects.create(
                company=company,
                django_user=django_user,
                username=username,
                role='admin',
                status='pending',
                is_approved=False
            )
            
            logger.info(f"[AdminSignupView] 관리자 회원가입 성공 - 사용자: {username}, 업체: {company.name}, 코드: {company.code}")
            
            return Response({
                'success': True,
                'message': '회원가입이 완료되었습니다. 상위 업체 관리자 승인 후 로그인할 수 있습니다.',
                'company_code': company.code
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[AdminSignupView] 관리자 회원가입 실패: {str(e)}")
            return Response(
                {'error': '회원가입 중 오류가 발생했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# CSRFTokenView 제거

# 직원 회원가입 기능 비활성화 - 요구사항에 따라 제거
# class StaffSignupView(APIView):
#     """직원 회원가입"""
#     permission_classes = [AllowAny]
#     
#     def get(self, request):
#         """직원 회원가입 페이지 렌더링"""
#         return render(request, 'companies/staff_signup.html')
#     
#     def post(self, request):
#         """직원 회원가입 처리"""
#         logger.info(f"[StaffSignupView] 직원 회원가입 요청 - IP: {request.META.get('REMOTE_ADDR')}")
#         
#         try:
#             # 필수 필드 검증
#             required_fields = ['username', 'password', 'company_code']
#             for field in required_fields:
#                 if not request.data.get(field):
#                     return Response(
#                         {'error': f'{field}는 필수 입력 사항입니다.'}, 
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
#             
#             username = request.data.get('username')
#             password = request.data.get('password')
#             company_code = request.data.get('company_code')
#             
#             # 사용자명 중복 검사
#             if User.objects.filter(username=username).exists():
#                 return Response(
#                     {'error': '이미 사용 중인 사용자명입니다.'}, 
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             
#             # 업체 코드 검증
#             try:
#                 company = Company.objects.get(code=company_code, status=True)
#             except Company.DoesNotExist:
#                 return Response(
#                     {'error': '유효하지 않은 업체 코드입니다.'}, 
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             
#             # Django User 생성
#             django_user = User.objects.create_user(
#                 username=username,
#                 password=password
#             )
#             
#             # CompanyUser 생성 (승인 대기 상태)
#             company_user = CompanyUser.objects.create(
#                 company=company,
#                 django_user=django_user,
#                 username=username,
#                 role='staff',
#                 status='pending',
#                 is_approved=False
#             )
#             
#             logger.info(f"[StaffSignupView] 직원 회원가입 성공 - 사용자: {username}, 업체: {company.name}")
#             
#             return Response({
#                 'success': True,
#                 'message': '회원가입이 완료되었습니다. 해당 업체 관리자 승인 후 로그인할 수 있습니다.',
#                 'company_name': company.name
#             }, status=status.HTTP_201_CREATED)
#             
#         except Exception as e:
#             logger.error(f"[StaffSignupView] 직원 회원가입 실패: {str(e)}")
#             return Response(
#                 {'error': '회원가입 중 오류가 발생했습니다.'}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class ChildCompaniesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            company_user = CompanyUser.objects.get(django_user=user)
            child_companies = Company.objects.filter(parent_company=company_user.company)
            data = [{'id': company.id, 'name': company.name} for company in child_companies]
            return Response({'success': True, 'data': data}, status=status.HTTP_200_OK)
        except CompanyUser.DoesNotExist:
            return Response({'success': False, 'message': '사용자 정보가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'자식 회사 목록 조회 실패: {str(e)}')
            return Response({'success': False, 'message': '자식 회사 목록 조회에 실패했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

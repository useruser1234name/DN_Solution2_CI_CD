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

# 로거 설정
logger = logging.getLogger('companies')

# Create your views here.

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        logger.info(f"[CompanyViewSet] 목록 조회 요청 - IP: {request.META.get('REMOTE_ADDR')}")
        try:
            response = super().list(request, *args, **kwargs)
            logger.info(f"[CompanyViewSet] 목록 조회 성공 - 결과 수: {len(response.data)}")
            return response
        except Exception as e:
            logger.error(f"[CompanyViewSet] 목록 조회 실패: {str(e)}")
            raise

    def create(self, request, *args, **kwargs):
        logger.info(f"[CompanyViewSet] 생성 요청 - IP: {request.META.get('REMOTE_ADDR')} - 데이터: {request.data}")
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(f"[CompanyViewSet] 생성 성공 - ID: {response.data.get('id')}")
            return response
        except Exception as e:
            logger.error(f"[CompanyViewSet] 생성 실패: {str(e)}")
            raise

class CompanyUserViewSet(viewsets.ModelViewSet):
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        logger.info(f"[CompanyUserViewSet] 목록 조회 요청 - IP: {request.META.get('REMOTE_ADDR')}")
        try:
            response = super().list(request, *args, **kwargs)
            logger.info(f"[CompanyUserViewSet] 목록 조회 성공 - 결과 수: {len(response.data)}")
            return response
        except Exception as e:
            logger.error(f"[CompanyUserViewSet] 목록 조회 실패: {str(e)}")
            raise

class UserApprovalView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        """사용자 승인/거부 API"""
        logger.info(f"[UserApprovalView] 사용자 승인/거부 요청 - 사용자 ID: {user_id}, IP: {request.META.get('REMOTE_ADDR')}")
        
        try:
            action = request.data.get('action')  # 'approve' 또는 'reject'
            logger.info(f"[UserApprovalView] 액션: {action}")
            
            try:
                user = CompanyUser.objects.get(id=user_id)
                logger.info(f"[UserApprovalView] 사용자 찾음: {user.username}")
            except CompanyUser.DoesNotExist:
                logger.error(f"[UserApprovalView] 사용자를 찾을 수 없음: {user_id}")
                return Response(
                    {'error': '사용자를 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if action == 'approve':
                user.status = 'approved'
                user.is_approved = True
                logger.info(f"[UserApprovalView] 사용자 승인: {user.username}")
            elif action == 'reject':
                user.status = 'rejected'
                user.is_approved = False
                logger.info(f"[UserApprovalView] 사용자 거부: {user.username}")
            else:
                logger.error(f"[UserApprovalView] 잘못된 액션: {action}")
                return Response(
                    {'error': '잘못된 액션입니다. (approve 또는 reject)'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.save()
            
            response_data = {
                'id': str(user.id),
                'username': user.username,
                'status': user.status,
                'message': f'사용자가 {action}되었습니다.'
            }
            
            logger.info(f"[UserApprovalView] 사용자 상태 변경 완료: {user.username} -> {user.status}")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[UserApprovalView] 사용자 승인/거부 처리 중 오류: {str(e)}", exc_info=True)
            return Response(
                {'error': '사용자 승인/거부 처리 중 오류가 발생했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """로그인 API"""
        logger.info(f"[LoginView] 로그인 요청 - IP: {request.META.get('REMOTE_ADDR')} - User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
        
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            
            logger.info(f"[LoginView] 로그인 시도 - 사용자명: {username}")
            
            # Django 인증 시스템 사용
            from django.contrib.auth import authenticate
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # CompanyUser 조회
                try:
                    company_user = CompanyUser.objects.get(django_user=user)
                    
                    # 승인된 사용자만 로그인 허용
                    if not company_user.is_approved:
                        logger.warning(f"[LoginView] 승인되지 않은 사용자 로그인 시도: {username}")
                        return Response(
                            {'error': '승인되지 않은 사용자입니다. 관리자에게 문의하세요.'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
                    
                    # 마지막 로그인 시간 업데이트
                    company_user.last_login = timezone.now()
                    company_user.save()
                    
                    response_data = {
                        'id': str(company_user.id),
                        'username': company_user.username,
                        'role': company_user.role,
                        'status': company_user.status,
                        'company_name': company_user.company.name,
                        'company_type': company_user.company.get_type_display(),
                        'message': '로그인 성공'
                    }
                    
                    logger.info(f"[LoginView] 로그인 성공 - 사용자: {username}")
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                except CompanyUser.DoesNotExist:
                    logger.warning(f"[LoginView] CompanyUser가 존재하지 않음: {username}")
                    return Response(
                        {'error': '사용자 정보를 찾을 수 없습니다.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            else:
                logger.warning(f"[LoginView] 로그인 실패 - 잘못된 인증 정보: {username}")
                return Response(
                    {'error': '아이디 또는 비밀번호가 올바르지 않습니다.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except Exception as e:
            logger.error(f"[LoginView] 로그인 처리 오류: {str(e)}", exc_info=True)
            return Response(
                {'error': '로그인 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardStatsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """대시보드 통계 데이터를 반환합니다."""
        logger.info(f"[DashboardStatsView] 통계 요청 - IP: {request.META.get('REMOTE_ADDR')} - User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
        
        try:
            # 실제 데이터베이스에서 통계 계산
            logger.info("[DashboardStatsView] 데이터베이스 조회 시작")
            
            # 모든 회사 조회
            all_companies = Company.objects.all()
            total_companies = all_companies.count()
            logger.info(f"[DashboardStatsView] 모든 회사 조회 - 총 {total_companies}개")
            
            # 회사 목록 로깅
            for company in all_companies:
                logger.info(f"[DashboardStatsView] 회사 정보: ID={company.id}, 이름={company.name}, 상태={company.status}")
            
            # 대기 중인 승인 조회
            pending_approvals = CompanyUser.objects.filter(status='pending').count()
            logger.info(f"[DashboardStatsView] 대기 중인 승인: {pending_approvals}")
            
            # 오늘 날짜 계산
            today = timezone.now().date()
            today_orders = 0  # TODO: orders 앱에서 실제 주문 수 계산
            logger.info(f"[DashboardStatsView] 오늘 주문 수: {today_orders}")
            
            # 재고 부족 상품 수 (TODO: inventory 앱에서 계산)
            low_stock_items = 0
            logger.info(f"[DashboardStatsView] 재고 부족 상품 수: {low_stock_items}")
            
            stats = {
                'total_companies': total_companies,
                'pending_approvals': pending_approvals,
                'today_orders': today_orders,
                'low_stock_items': low_stock_items
            }
            
            logger.info(f"[DashboardStatsView] 통계 데이터 생성 완료: {json.dumps(stats, ensure_ascii=False)}")
            return Response(stats)
        except Exception as e:
            logger.error(f"[DashboardStatsView] 통계 계산 오류: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardActivitiesView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """대시보드 활동 내역을 반환합니다."""
        logger.info(f"[DashboardActivitiesView] 활동 요청 - IP: {request.META.get('REMOTE_ADDR')} - User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
        
        try:
            activities = []
            logger.info("[DashboardActivitiesView] 활동 데이터 수집 시작")
            
            # 최근 로그인한 사용자들
            recent_users = CompanyUser.objects.filter(
                last_login__gte=timezone.now() - timedelta(hours=24)
            ).order_by('-last_login')[:5]
            
            logger.info(f"[DashboardActivitiesView] 최근 로그인 사용자 수: {recent_users.count()}")
            
            for user in recent_users:
                activity = {
                    'type': 'user',
                    'message': f'{user.username}님이 로그인했습니다.',
                    'time': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '방금 전'
                }
                activities.append(activity)
                logger.info(f"[DashboardActivitiesView] 사용자 활동 추가: {activity}")
            
            # 시스템 상태
            system_activity = {
                'type': 'system',
                'message': '시스템이 정상적으로 실행 중입니다.',
                'time': timezone.now().strftime('%Y-%m-%d %H:%M')
            }
            activities.append(system_activity)
            logger.info(f"[DashboardActivitiesView] 시스템 활동 추가: {system_activity}")
            
            logger.info(f"[DashboardActivitiesView] 활동 데이터 수집 완료 - 총 {len(activities)}개")
            return Response(activities)
        except Exception as e:
            logger.error(f"[DashboardActivitiesView] 활동 데이터 수집 오류: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

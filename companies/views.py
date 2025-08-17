"""
Company Views

대시보드 및 기타 API Views를 포함합니다.
ViewSet은 viewsets.py로, 인증 관련 뷰는 auth_views.py로 분리되었습니다.
"""

import logging
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta

from .models import CompanyUser
from .services import CompanyService, CompanyUserService

# 로거 설정
logger = logging.getLogger('companies')

class UserApprovalView(APIView):
    """
    사용자 승인/거부 API (레거시 호환성을 위해 유지)
    새로운 코드에서는 CompanyUserViewSet의 approve/reject 액션을 사용하세요.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """사용자 승인/거부 API - 계층 구조에 따른 권한 제한"""
        action = request.data.get('action')
        
        try:
            result = CompanyUserService.approve_user(
                user_id=user_id,
                approver=request.user,
                action=action
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'사용자 승인/거부 실패: {str(e)}')
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class DashboardStatsView(APIView):
    """대시보드 통계 데이터 API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """대시보드 통계 데이터를 반환합니다."""
        try:
            stats = CompanyService.get_company_stats(request.user)
            # TODO: orders 앱에서 실제 주문 수 계산
            stats['today_orders'] = 0
            return Response(stats)
        except Exception as e:
            logger.error(f'대시보드 통계 조회 실패: {str(e)}')
            return Response(
                {'error': '통계 정보 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardActivitiesView(APIView):
    """대시보드 활동 내역 API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """대시보드 활동 내역을 반환합니다."""
        try:
            hours = int(request.query_params.get('hours', 24))
            activities = CompanyUserService.get_user_activities(request.user, hours)
            
            # 시스템 활동 추가
            activities.append({
                'type': 'system',
                'message': '시스템이 정상적으로 실행 중입니다.',
                'time': timezone.now().strftime('%Y-%m-%d %H:%M')
            })
            
            return Response(activities)
        except Exception as e:
            logger.error(f'활동 내역 조회 실패: {str(e)}')
            return Response(
                {'error': '활동 내역 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChildCompaniesView(APIView):
    """하위 업체 목록 API (레거시 호환성을 위해 유지)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            company_user = CompanyUser.objects.get(django_user=user)
            child_companies = company_user.company.child_companies.all()
            data = [
                {
                    'id': str(company.id), 
                    'name': company.name,
                    'type': company.type,
                    'code': company.code,
                    'status': company.status
                } 
                for company in child_companies
            ]
            return Response({'success': True, 'data': data}, status=status.HTTP_200_OK)
        except CompanyUser.DoesNotExist:
            return Response(
                {'success': False, 'message': '사용자 정보가 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f'하위 업체 목록 조회 실패: {str(e)}')
            return Response(
                {'success': False, 'message': '하위 업체 목록 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

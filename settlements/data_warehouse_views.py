"""
데이터 웨어하우스 API 뷰

수수료 팩트 테이블 및 그레이드 시스템 데이터에 대한 API 엔드포인트를 제공합니다.
"""

import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from .models import (
    CommissionFact, CommissionGradeTracking, GradeBonusSettlement
)
from .serializers import (
    CommissionGradeTrackingSerializer, GradeBonusSettlementSerializer,
    GradeTargetSetupSerializer
)
from .analysis_tools import CommissionAnalyzer, GradeAnalyzer
from core.permissions import IsHeadquarters, IsHeadquartersOrAgency

logger = logging.getLogger(__name__)


class CommissionFactViewSet(viewsets.ReadOnlyModelViewSet):
    """
    수수료 팩트 테이블 ViewSet (읽기 전용)
    
    데이터 웨어하우스의 팩트 테이블 데이터를 조회하는 API
    """
    
    queryset = CommissionFact.objects.all()
    permission_classes = [IsAuthenticated, IsHeadquartersOrAgency]
    
    def get_queryset(self):
        """사용자별 접근 권한에 따른 데이터 필터링"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=self.request.user)
            user_company = company_user.company
            
            # 본사는 모든 데이터 조회 가능
            if user_company.type == 'headquarters':
                return self.queryset.select_related('company', 'policy', 'order')
            
            # 협력사는 자신과 하위 판매점 데이터만
            elif user_company.type == 'agency':
                return self.queryset.filter(
                    Q(company=user_company) |
                    Q(company__parent_company=user_company)
                ).select_related('company', 'policy', 'order')
            
            # 판매점은 자신의 데이터만
            else:
                return self.queryset.filter(
                    company=user_company
                ).select_related('company', 'policy', 'order')
                
        except Exception as e:
            logger.error(f"팩트 데이터 조회 권한 확인 실패: {str(e)}")
            return self.queryset.none()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """수수료 요약 통계"""
        try:
            # 날짜 파라미터 처리
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            queryset = self.get_queryset()
            
            if start_date:
                queryset = queryset.filter(date_key__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_key__lte=end_date)
            
            # 요약 통계 계산
            summary_stats = queryset.aggregate(
                total_commission=Sum('total_commission'),
                total_base_commission=Sum('base_commission'),
                total_grade_bonus=Sum('grade_bonus'),
                total_orders=Count('order', distinct=True),
                total_companies=Count('company', distinct=True),
                avg_commission=Avg('total_commission')
            )
            
            # 상태별 분포
            status_distribution = queryset.values('settlement_status').annotate(
                count=Count('id'),
                amount=Sum('total_commission')
            )
            
            # 그레이드별 분포
            grade_distribution = queryset.values('achieved_grade_level').annotate(
                count=Count('id'),
                total_bonus=Sum('grade_bonus')
            ).order_by('achieved_grade_level')
            
            return Response({
                'period': {
                    'start_date': start_date or '전체',
                    'end_date': end_date or '현재'
                },
                'summary': summary_stats,
                'status_distribution': list(status_distribution),
                'grade_distribution': list(grade_distribution)
            })
            
        except Exception as e:
            logger.error(f"수수료 요약 통계 조회 실패: {str(e)}")
            return Response(
                {'error': '요약 통계 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def company_ranking(self, request):
        """업체별 수수료 순위"""
        try:
            limit = int(request.query_params.get('limit', 20))
            company_type = request.query_params.get('company_type')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # 분석기를 사용하여 순위 데이터 조회
            analyzer = CommissionAnalyzer()
            
            # 날짜 변환
            start_dt = None
            end_dt = None
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            ranking_data = analyzer.get_company_performance_ranking(
                start_date=start_dt,
                end_date=end_dt,
                limit=limit,
                company_type=company_type
            )
            
            return Response({
                'ranking': ranking_data,
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'company_type': company_type,
                    'limit': limit
                }
            })
            
        except Exception as e:
            logger.error(f"업체별 순위 조회 실패: {str(e)}")
            return Response(
                {'error': '순위 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommissionGradeTrackingViewSet(viewsets.ModelViewSet):
    """
    수수료 그레이드 추적 ViewSet
    
    그레이드 시스템의 목표 설정 및 달성 현황을 관리합니다.
    """
    
    queryset = CommissionGradeTracking.objects.all()
    serializer_class = CommissionGradeTrackingSerializer
    permission_classes = [IsAuthenticated, IsHeadquartersOrAgency]
    
    def get_queryset(self):
        """사용자별 접근 권한에 따른 데이터 필터링"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=self.request.user)
            user_company = company_user.company
            
            # 본사는 모든 그레이드 추적 데이터 조회 가능
            if user_company.type == 'headquarters':
                return self.queryset.select_related('company', 'policy')
            
            # 협력사는 자신과 하위 판매점 데이터만
            elif user_company.type == 'agency':
                return self.queryset.filter(
                    Q(company=user_company) |
                    Q(company__parent_company=user_company)
                ).select_related('company', 'policy')
            
            # 판매점은 자신의 데이터만
            else:
                return self.queryset.filter(
                    company=user_company
                ).select_related('company', 'policy')
                
        except Exception as e:
            logger.error(f"그레이드 추적 데이터 조회 권한 확인 실패: {str(e)}")
            return self.queryset.none()
    
    @action(detail=False, methods=['post'])
    def setup_target(self, request):
        """그레이드 목표 설정"""
        serializer = GradeTargetSetupSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = serializer.validated_data
            
            # 업체와 정책 조회
            from companies.models import Company
            from policies.models import Policy
            
            company = Company.objects.get(id=data['company'])
            policy = Policy.objects.get(id=data['policy'])
            
            # 그레이드 추적 생성
            if data['period_type'] == 'monthly':
                tracking = CommissionGradeTracking.create_monthly_tracking(
                    company=company,
                    policy=policy,
                    year=data['year'],
                    month=data['month'],
                    target_orders=data['target_orders']
                )
            elif data['period_type'] == 'quarterly':
                tracking = CommissionGradeTracking.create_quarterly_tracking(
                    company=company,
                    policy=policy,
                    year=data['year'],
                    quarter=data['quarter'],
                    target_orders=data['target_orders']
                )
            else:
                return Response(
                    {'error': '현재 월별, 분기별 추적만 지원됩니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = CommissionGradeTrackingSerializer(tracking)
            return Response({
                'message': '그레이드 목표가 설정되었습니다.',
                'tracking': serializer.data
            })
            
        except Exception as e:
            logger.error(f"그레이드 목표 설정 실패: {str(e)}")
            return Response(
                {'error': '목표 설정 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """그레이드 대시보드 데이터"""
        try:
            company_type = request.query_params.get('company_type')
            period_type = request.query_params.get('period_type', 'monthly')
            
            analyzer = GradeAnalyzer()
            dashboard_data = analyzer.get_grade_dashboard_data(
                company_type=company_type,
                period_type=period_type
            )
            
            return Response(dashboard_data)
            
        except Exception as e:
            logger.error(f"그레이드 대시보드 데이터 조회 실패: {str(e)}")
            return Response(
                {'error': '대시보드 데이터 조회 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GradeBonusSettlementViewSet(viewsets.ModelViewSet):
    """
    그레이드 보너스 정산 ViewSet
    
    그레이드 달성에 따른 보너스 수수료 정산을 관리합니다.
    """
    
    queryset = GradeBonusSettlement.objects.all()
    serializer_class = GradeBonusSettlementSerializer
    permission_classes = [IsAuthenticated, IsHeadquarters]  # 본사만 접근 가능
    
    def get_queryset(self):
        """본사만 모든 보너스 정산 조회 가능"""
        return self.queryset.select_related(
            'grade_tracking__company',
            'grade_tracking__policy'
        )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """보너스 정산 승인"""
        try:
            bonus_settlement = self.get_object()
            bonus_settlement.approve(request.user)
            
            serializer = self.get_serializer(bonus_settlement)
            return Response({
                'message': '보너스 정산이 승인되었습니다.',
                'settlement': serializer.data
            })
            
        except Exception as e:
            logger.error(f"보너스 정산 승인 실패: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """보너스 지급 완료 처리"""
        try:
            bonus_settlement = self.get_object()
            bonus_settlement.mark_as_paid(request.user)
            
            serializer = self.get_serializer(bonus_settlement)
            return Response({
                'message': '보너스 지급이 완료되었습니다.',
                'settlement': serializer.data
            })
            
        except Exception as e:
            logger.error(f"보너스 지급 완료 처리 실패: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """승인 대기 중인 보너스 정산 목록"""
        pending_settlements = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_settlements, many=True)
        
        return Response({
            'count': pending_settlements.count(),
            'results': serializer.data
        })

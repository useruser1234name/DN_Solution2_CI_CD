"""
정산 대시보드 뷰
사용자별 맞춤 대시보드 제공
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsHeadquartersUser, IsHeadquartersOrAgency, HierarchyPermission
from companies.models import Company
from policies.models import Policy
from .models import Settlement, CommissionGradeTracking, GradeBonusSettlement

logger = logging.getLogger(__name__)


class HeadquartersSettlementDashboard(APIView):
    """본사용 정산 대시보드"""
    permission_classes = [IsAuthenticated, IsHeadquartersUser]
    
    def get(self, request):
        """본사 대시보드 데이터 반환"""
        try:
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            dashboard_data = {
                'summary': self._get_summary_stats(start_date),
                'settlement_trends': self._get_settlement_trends(start_date),
                'company_performance': self._get_company_performance(start_date),
                'policy_performance': self._get_policy_performance(start_date),
                'payment_status': self._get_payment_status(),
                'grade_overview': self._get_grade_overview(),
                'recent_activities': self._get_recent_activities()
            }
            
            return Response(dashboard_data)
        except Exception as e:
            logger.error(f"본사 대시보드 데이터 조회 실패: {str(e)}")
            return Response(
                {'error': '대시보드 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_summary_stats(self, start_date):
        """요약 통계"""
        settlements = Settlement.objects.filter(created_at__gte=start_date)
        
        total_stats = settlements.aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            pending_count=Count('id', filter=Q(status='pending')),
            approved_count=Count('id', filter=Q(status='approved')),
            paid_count=Count('id', filter=Q(status='paid')),
            unpaid_count=Count('id', filter=Q(status='unpaid')),
            cancelled_count=Count('id', filter=Q(status='cancelled'))
        )
        
        # None 값 처리
        for key, value in total_stats.items():
            if value is None:
                total_stats[key] = 0
        
        return total_stats
    
    def _get_settlement_trends(self, start_date):
        """정산 트렌드"""
        daily_stats = Settlement.objects.filter(
            created_at__gte=start_date
        ).extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            daily_amount=Sum('rebate_amount'),
            daily_count=Count('id')
        ).order_by('date')
        
        return list(daily_stats)
    
    def _get_company_performance(self, start_date):
        """업체별 성과 분석"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'company__name',
            'company__type'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id')
        ).order_by('-total_amount')[:20])
    
    def _get_policy_performance(self, start_date):
        """정책별 성과 분석"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'order__policy__title'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id')
        ).order_by('-total_amount')[:15])
    
    def _get_payment_status(self):
        """입금 현황"""
        return {
            'pending_payments': Settlement.objects.filter(status='approved').aggregate(
                count=Count('id'), amount=Sum('rebate_amount')
            ),
            'unpaid_settlements': Settlement.objects.filter(status='unpaid').aggregate(
                count=Count('id'), amount=Sum('rebate_amount')
            )
        }
    
    def _get_grade_overview(self):
        """그레이드 현황"""
        active_trackings = CommissionGradeTracking.objects.filter(is_active=True)
        
        grade_distribution = {}
        for level in range(6):
            count = active_trackings.filter(achieved_grade_level=level).count()
            grade_distribution[f'level_{level}'] = count
        
        return {
            'total_companies': active_trackings.values('company').distinct().count(),
            'distribution': grade_distribution
        }
    
    def _get_recent_activities(self):
        """최근 활동"""
        activities = []
        
        # 최근 승인 내역
        recent_approvals = Settlement.objects.filter(
            approved_at__isnull=False
        ).select_related('company', 'approved_by').order_by('-approved_at')[:10]
        
        for settlement in recent_approvals:
            activities.append({
                'type': 'settlement_approved',
                'timestamp': settlement.approved_at,
                'description': f"{settlement.company.name} 정산 승인 ({settlement.rebate_amount:,}원)",
                'user': settlement.approved_by.username if settlement.approved_by else 'System'
            })
        
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:15]


class AgencySettlementDashboard(APIView):
    """협력사용 정산 대시보드"""
    permission_classes = [IsAuthenticated, IsHeadquartersOrAgency]
    
    def get(self, request):
        """협력사 대시보드 데이터"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            if company.type == 'headquarters':
                base_queryset = Settlement.objects.all()
            else:
                base_queryset = Settlement.objects.filter(
                    Q(company=company) | Q(company__parent_company=company)
                )
            
            dashboard_data = {
                'company_info': {
                    'name': company.name,
                    'type': company.get_type_display()
                },
                'receivables': self._get_receivables(company, base_queryset, start_date),
                'payables': self._get_payables(company, base_queryset, start_date),
                'grade_status': self._get_grade_status(company),
                'subordinate_performance': self._get_subordinate_performance(company, start_date)
            }
            
            return Response(dashboard_data)
        except Exception as e:
            logger.error(f"협력사 대시보드 오류: {str(e)}")
            return Response(
                {'error': '대시보드 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_receivables(self, company, base_queryset, start_date):
        """받을 수수료"""
        return base_queryset.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            pending_amount=Sum('rebate_amount', filter=Q(status='pending')),
            approved_amount=Sum('rebate_amount', filter=Q(status='approved')),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
        )
    
    def _get_payables(self, company, base_queryset, start_date):
        """지급할 수수료 (하위 업체가 있는 경우)"""
        if company.type == 'agency':
            return base_queryset.filter(
                company__parent_company=company,
                created_at__gte=start_date
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                pending_amount=Sum('rebate_amount', filter=Q(status='pending')),
                approved_amount=Sum('rebate_amount', filter=Q(status='approved')),
                paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
            )
        return {}
    
    def _get_grade_status(self, company):
        """그레이드 상태"""
        current_tracking = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True,
            period_start__lte=timezone.now().date(),
            period_end__gte=timezone.now().date()
        ).first()
        
        if current_tracking:
            return current_tracking.get_grade_status()
        return None
    
    def _get_subordinate_performance(self, company, start_date):
        """하위 업체 성과 (협력사인 경우)"""
        if company.type == 'agency':
            return list(Settlement.objects.filter(
                company__parent_company=company,
                created_at__gte=start_date
            ).values(
                'company__name'
            ).annotate(
                total_amount=Sum('rebate_amount'),
                total_count=Count('id')
            ).order_by('-total_amount'))
        return []


class RetailSettlementDashboard(APIView):
    """판매점용 정산 대시보드"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """판매점 대시보드 데이터"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type not in ['retail', 'agency', 'headquarters']:
                return Response(
                    {'error': '권한이 없습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            dashboard_data = {
                'company_info': {
                    'name': company.name,
                    'type': company.get_type_display()
                },
                'settlement_summary': self._get_settlement_summary(company, start_date),
                'monthly_trends': self._get_monthly_trends(company),
                'grade_progress': self._get_grade_progress(company),
                'recent_settlements': self._get_recent_settlements(company)
            }
            
            return Response(dashboard_data)
        except Exception as e:
            logger.error(f"판매점 대시보드 오류: {str(e)}")
            return Response(
                {'error': '대시보드 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_settlement_summary(self, company, start_date):
        """정산 요약"""
        return Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            pending_amount=Sum('rebate_amount', filter=Q(status='pending')),
            approved_amount=Sum('rebate_amount', filter=Q(status='approved')),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
        )
    
    def _get_monthly_trends(self, company):
        """월별 트렌드 (최근 6개월)"""
        from django.db.models import TruncMonth
        
        six_months_ago = timezone.now() - timedelta(days=180)
        
        monthly_data = Settlement.objects.filter(
            company=company,
            created_at__gte=six_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            monthly_amount=Sum('rebate_amount'),
            monthly_count=Count('id')
        ).order_by('month')
        
        return list(monthly_data)
    
    def _get_grade_progress(self, company):
        """그레이드 진행 상황"""
        current_tracking = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True,
            period_start__lte=timezone.now().date(),
            period_end__gte=timezone.now().date()
        ).first()
        
        if current_tracking:
            return current_tracking.get_grade_status()
        return None
    
    def _get_recent_settlements(self, company):
        """최근 정산 내역"""
        recent_settlements = Settlement.objects.filter(
            company=company
        ).select_related('order', 'order__policy').order_by('-created_at')[:10]
        
        return [{
            'id': str(settlement.id),
            'amount': settlement.rebate_amount,
            'status': settlement.status,
            'status_display': settlement.get_status_display(),
            'created_at': settlement.created_at,
            'policy_title': settlement.order.policy.title if settlement.order.policy else 'N/A'
        } for settlement in recent_settlements]


class SettlementAnalyticsDashboard(APIView):
    """정산 분석 대시보드"""
    permission_classes = [IsAuthenticated, IsHeadquartersUser]
    
    def get(self, request):
        """분석 대시보드 데이터"""
        try:
            period = request.query_params.get('period', '90')
            days = int(period) if period.isdigit() else 90
            start_date = timezone.now() - timedelta(days=days)
            
            dashboard_data = {
                'revenue_analysis': self._get_revenue_analysis(start_date),
                'company_rankings': self._get_company_rankings(start_date),
                'policy_effectiveness': self._get_policy_effectiveness(start_date),
                'grade_impact_analysis': self._get_grade_impact_analysis(start_date),
                'payment_patterns': self._get_payment_patterns(start_date)
            }
            
            return Response(dashboard_data)
        except Exception as e:
            logger.error(f"분석 대시보드 오류: {str(e)}")
            return Response(
                {'error': '분석 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_revenue_analysis(self, start_date):
        """수익 분석"""
        settlements = Settlement.objects.filter(created_at__gte=start_date)
        
        # 업체 타입별 분석
        type_analysis = settlements.values('company__type').annotate(
            total_amount=Sum('rebate_amount'),
            count=Count('id'),
            avg_amount=Avg('rebate_amount')
        )
        
        # 월별 트렌드
        from django.db.models import TruncMonth
        monthly_trend = settlements.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            monthly_amount=Sum('rebate_amount'),
            monthly_count=Count('id')
        ).order_by('month')
        
        return {
            'by_company_type': list(type_analysis),
            'monthly_trend': list(monthly_trend)
        }
    
    def _get_company_rankings(self, start_date):
        """업체 순위"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'company__name',
            'company__type'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            avg_amount=Avg('rebate_amount')
        ).order_by('-total_amount')[:50])
    
    def _get_policy_effectiveness(self, start_date):
        """정책 효과성 분석"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'order__policy__title',
            'order__policy__carrier'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            avg_amount=Avg('rebate_amount'),
            unique_companies=Count('company', distinct=True)
        ).order_by('-total_amount')[:30])
    
    def _get_grade_impact_analysis(self, start_date):
        """그레이드 영향 분석"""
        # 그레이드별 보너스 분석
        grade_bonus = GradeBonusSettlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'grade_tracking__achieved_grade_level'
        ).annotate(
            total_bonus=Sum('bonus_amount'),
            count=Count('id'),
            avg_bonus=Avg('bonus_amount')
        ).order_by('grade_tracking__achieved_grade_level')
        
        return list(grade_bonus)
    
    def _get_payment_patterns(self, start_date):
        """입금 패턴 분석"""
        settlements = Settlement.objects.filter(created_at__gte=start_date)
        
        # 상태별 분포
        status_distribution = settlements.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('rebate_amount')
        )
        
        # 입금까지 걸리는 평균 시간 (승인 후 입금까지)
        paid_settlements = settlements.filter(
            status='paid',
            approved_at__isnull=False,
            paid_at__isnull=False
        )
        
        payment_delays = []
        for settlement in paid_settlements:
            if settlement.approved_at and settlement.paid_at:
                delay_days = (settlement.paid_at.date() - settlement.approved_at.date()).days
                payment_delays.append(delay_days)
        
        avg_payment_delay = sum(payment_delays) / len(payment_delays) if payment_delays else 0
        
        return {
            'status_distribution': list(status_distribution),
            'avg_payment_delay_days': round(avg_payment_delay, 1),
            'total_analyzed_payments': len(payment_delays)
        }

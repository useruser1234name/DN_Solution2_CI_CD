"""
정산 대시보드 뷰
사용자별(본사/협력사/판매점) 맞춤 대시보드 제공
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import (
    Sum, Count, Avg, Q, F, Case, When, Value, IntegerField, DecimalField
)
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Settlement, CommissionGradeTracking, GradeBonusSettlement, CommissionFact
from companies.models import Company
from core.permissions import HierarchyPermission

logger = logging.getLogger(__name__)


class HeadquartersSettlementDashboard(APIView):
    """본사용 정산 대시보드"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """본사 대시보드 데이터 조회"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            if company_user.company.type != 'headquarters':
                return Response(
                    {'error': '본사 권한이 필요합니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            # 대시보드 데이터 생성
            dashboard_data = {
                'overview': self._get_overview_stats(start_date),
                'payment_status': self._get_payment_status(),
                'policy_performance': self._get_policy_performance(start_date),
                'company_ranking': self._get_company_ranking(start_date),
                'grade_summary': self._get_grade_summary(),
                'recent_trends': self._get_recent_trends(),
                'alerts': self._get_alerts()
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            logger.error(f"본사 대시보드 오류: {str(e)}")
            return Response(
                {'error': '대시보드 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_overview_stats(self, start_date):
        """전체 개요 통계"""
        return Settlement.objects.filter(
            created_at__gte=start_date
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            pending_amount=Sum('rebate_amount', filter=Q(status='pending')),
            approved_amount=Sum('rebate_amount', filter=Q(status='approved')),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            unpaid_amount=Sum('rebate_amount', filter=Q(status='unpaid')),
            avg_amount=Avg('rebate_amount')
        )
    
    def _get_payment_status(self):
        """입금 현황"""
        pending_payments = Settlement.objects.filter(
            status='approved'
        ).aggregate(
            count=Count('id'),
            amount=Sum('rebate_amount')
        )
        
        unpaid_settlements = Settlement.objects.filter(
            status='unpaid'
        ).aggregate(
            count=Count('id'),
            amount=Sum('rebate_amount')
        )
        
        return {
            'pending_payments': pending_payments,
            'unpaid_settlements': unpaid_settlements,
            'overdue_count': Settlement.objects.filter(
                status__in=['approved', 'unpaid'],
                expected_payment_date__lt=timezone.now().date()
            ).count()
        }
    
    def _get_policy_performance(self, start_date):
        """정책별 성과"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).values(
            'order__policy__title'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            avg_amount=Avg('rebate_amount')
        ).order_by('-total_amount')[:10])
    
    def _get_company_ranking(self, start_date):
        """업체별 순위"""
        return list(Settlement.objects.filter(
            created_at__gte=start_date
        ).exclude(
            company__type='headquarters'
        ).values(
            'company__name', 'company__type'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            payment_rate=Case(
                When(total_count__gt=0, then=F('paid_count') * 100.0 / F('total_count')),
                default=Value(0),
                output_field=DecimalField()
            ),
            paid_count=Count('id', filter=Q(status='paid'))
        ).order_by('-total_amount')[:10])
    
    def _get_grade_summary(self):
        """그레이드 요약"""
        grade_stats = CommissionGradeTracking.objects.filter(
            is_active=True
        ).aggregate(
            active_companies=Count('company', distinct=True),
            total_bonus=Sum('total_bonus'),
            avg_achievement=Avg('current_orders') * 100.0 / Avg('target_orders')
        )
        
        # 보너스 정산 현황
        bonus_stats = GradeBonusSettlement.objects.aggregate(
            pending_bonus=Sum('bonus_amount', filter=Q(status='pending')),
            paid_bonus=Sum('bonus_amount', filter=Q(status='paid'))
        )
        
        return {
            **grade_stats,
            **bonus_stats
        }
    
    def _get_recent_trends(self):
        """최근 트렌드 (일주일)"""
        trends = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            day_stats = Settlement.objects.filter(
                created_at__date=date
            ).aggregate(
                amount=Sum('rebate_amount'),
                count=Count('id')
            )
            
            trends.append({
                'date': date.isoformat(),
                'amount': day_stats['amount'] or 0,
                'count': day_stats['count'] or 0
            })
        
        trends.reverse()
        return trends
    
    def _get_alerts(self):
        """알림사항"""
        alerts = []
        
        # 미입금 건수
        unpaid_count = Settlement.objects.filter(status='unpaid').count()
        if unpaid_count > 0:
            alerts.append({
                'type': 'warning',
                'message': f'미입금 정산 {unpaid_count}건이 있습니다.',
                'count': unpaid_count
            })
        
        # 연체 건수
        overdue_count = Settlement.objects.filter(
            status__in=['approved', 'unpaid'],
            expected_payment_date__lt=timezone.now().date()
        ).count()
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'message': f'입금 예정일이 지난 정산 {overdue_count}건이 있습니다.',
                'count': overdue_count
            })
        
        return alerts


class AgencySettlementDashboard(APIView):
    """협력사용 정산 대시보드 - 고도화된 기능 포함"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """협력사 대시보드 데이터"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'agency':
                return Response(
                    {'error': '협력사 권한이 필요합니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            base_queryset = Settlement.objects.select_related(
                'company', 'order__policy'
            )
            
            dashboard_data = {
                'company_info': {
                    'name': company.name,
                    'type': company.get_type_display(),
                    'parent_company': company.parent_company.name if company.parent_company else None,
                    'subordinate_count': Company.objects.filter(parent_company=company).count()
                },
                'financial_summary': self._get_financial_summary(company, base_queryset, start_date),
                'receivables': self._get_receivables(company, base_queryset, start_date),
                'payables': self._get_payables(company, base_queryset, start_date),
                'cash_flow': self._get_cash_flow_analysis(company, start_date),
                'grade_status': self._get_grade_status(company),
                'subordinate_performance': self._get_subordinate_performance(company, start_date),
                'monthly_performance': self._get_monthly_performance(company),
                'policy_effectiveness': self._get_policy_effectiveness(company, start_date),
                'payment_schedule': self._get_payment_schedule(company),
                'performance_alerts': self._get_performance_alerts(company)
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
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            unpaid_amount=Sum('rebate_amount', filter=Q(status='unpaid'))
        )
    
    def _get_payables(self, company, base_queryset, start_date):
        """지급할 수수료"""
        payable_settlements = base_queryset.filter(
            company__parent_company=company,
            created_at__gte=start_date
        )
        
        return payable_settlements.aggregate(
            total_amount=Sum('rebate_amount'),
            pending_amount=Sum('rebate_amount', filter=Q(status='pending')),
            approved_amount=Sum('rebate_amount', filter=Q(status='approved')),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            unpaid_amount=Sum('rebate_amount', filter=Q(status='unpaid'))
        )
    
    def _get_grade_status(self, company):
        """그레이드 현황"""
        trackings = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        ).select_related('policy')
        
        grade_data = []
        for tracking in trackings:
            grade_status = tracking.get_grade_status()
            grade_data.append({
                'policy_title': tracking.policy.title,
                'period_type': tracking.get_period_type_display(),
                **grade_status
            })
        
        return {
            'trackings': grade_data,
            'total_bonus': sum(t['total_bonus'] for t in grade_data)
        }
    
    def _get_subordinate_performance(self, company, start_date):
        """하위 판매점 성과"""
        subordinates = Company.objects.filter(parent_company=company)
        
        performance_data = []
        for sub in subordinates:
            stats = Settlement.objects.filter(
                company=sub,
                created_at__gte=start_date
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_count=Count('id'),
                paid_count=Count('id', filter=Q(status='paid'))
            )
            
            payment_rate = 0
            if stats['total_count'] > 0:
                payment_rate = (stats['paid_count'] / stats['total_count']) * 100
            
            performance_data.append({
                'company_name': sub.name,
                'total_amount': stats['total_amount'] or 0,
                'total_count': stats['total_count'] or 0,
                'payment_rate': round(payment_rate, 2)
            })
        
        performance_data.sort(key=lambda x: x['total_amount'], reverse=True)
        return performance_data
    
    def _get_monthly_performance(self, company):
        """월별 성과 (최근 6개월)"""
        performance = []
        
        for i in range(6):
            target_date = timezone.now() - timedelta(days=30*i)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            receivable_stats = Settlement.objects.filter(
                company=company,
                created_at__gte=month_start,
                created_at__lt=next_month
            ).aggregate(
                receivable_amount=Sum('rebate_amount'),
                receivable_paid=Sum('rebate_amount', filter=Q(status='paid'))
            )
            
            payable_stats = Settlement.objects.filter(
                company__parent_company=company,
                created_at__gte=month_start,
                created_at__lt=next_month
            ).aggregate(
                payable_amount=Sum('rebate_amount'),
                payable_paid=Sum('rebate_amount', filter=Q(status='paid'))
            )
            
            performance.append({
                'year_month': month_start.strftime('%Y-%m'),
                'receivable_amount': receivable_stats['receivable_amount'] or 0,
                'receivable_paid': receivable_stats['receivable_paid'] or 0,
                'payable_amount': payable_stats['payable_amount'] or 0,
                'payable_paid': payable_stats['payable_paid'] or 0
            })
        
        performance.reverse()
        return performance
    
    def _get_financial_summary(self, company, base_queryset, start_date):
        """재무 요약 - 수익성 및 현금 흐름 분석"""
        # 받을 수수료 데이터
        receivables = base_queryset.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total=Sum('rebate_amount'),
            paid=Sum('rebate_amount', filter=Q(status='paid')),
            pending=Sum('rebate_amount', filter=Q(status__in=['pending', 'approved', 'unpaid']))
        )
        
        # 지급할 수수료 데이터
        payables = base_queryset.filter(
            company__parent_company=company,
            created_at__gte=start_date
        ).aggregate(
            total=Sum('rebate_amount'),
            paid=Sum('rebate_amount', filter=Q(status='paid')),
            pending=Sum('rebate_amount', filter=Q(status__in=['pending', 'approved', 'unpaid']))
        )
        
        # 순수익 계산
        net_income = (receivables['total'] or 0) - (payables['total'] or 0)
        net_cash_flow = (receivables['paid'] or 0) - (payables['paid'] or 0)
        
        # 수익성 비율
        profit_margin = 0
        if receivables['total'] and receivables['total'] > 0:
            profit_margin = (net_income / receivables['total']) * 100
        
        return {
            'receivables': receivables,
            'payables': payables,
            'net_income': net_income,
            'net_cash_flow': net_cash_flow,
            'profit_margin': round(profit_margin, 2),
            'cash_conversion_rate': self._calculate_cash_conversion_rate(receivables, payables)
        }
    
    def _calculate_cash_conversion_rate(self, receivables, payables):
        """현금 전환율 계산"""
        total_expected = (receivables.get('total', 0) or 0) - (payables.get('total', 0) or 0)
        total_realized = (receivables.get('paid', 0) or 0) - (payables.get('paid', 0) or 0)
        
        if total_expected > 0:
            return round((total_realized / total_expected) * 100, 2)
        return 0
    
    def _get_cash_flow_analysis(self, company, start_date):
        """현금 흐름 분석 - 주별 기간단위로 분석"""
        cash_flow_data = []
        
        for i in range(12):  # 12주 간
            week_start = timezone.now().date() - timedelta(weeks=i+1)
            week_end = timezone.now().date() - timedelta(weeks=i)
            
            # 받은 돈
            inflow = Settlement.objects.filter(
                company=company,
                paid_at__date__gte=week_start,
                paid_at__date__lt=week_end
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            # 지급한 돈
            outflow = Settlement.objects.filter(
                company__parent_company=company,
                paid_at__date__gte=week_start,
                paid_at__date__lt=week_end
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            cash_flow_data.append({
                'week': f"{week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}",
                'inflow': inflow,
                'outflow': outflow,
                'net_flow': inflow - outflow
            })
        
        cash_flow_data.reverse()
        return cash_flow_data
    
    def _get_policy_effectiveness(self, company, start_date):
        """정책별 효과성 분석"""
        from orders.models import Order
        
        # 정책별 주문 수 및 정산 분석
        subordinate_companies = Company.objects.filter(parent_company=company)
        all_companies = [company] + list(subordinate_companies)
        
        policies_data = Settlement.objects.filter(
            company__in=all_companies,
            created_at__gte=start_date
        ).values(
            'order__policy__id',
            'order__policy__title'
        ).annotate(
            order_count=Count('order', distinct=True),
            total_commission=Sum('rebate_amount'),
            avg_commission=Avg('rebate_amount'),
            completion_rate=Count('id', filter=Q(status__in=['paid', 'approved'])) * 100.0 / Count('id')
        ).order_by('-total_commission')
        
        policy_performance = []
        for policy_data in policies_data:
            # 그레이드 달성 데이터
            grade_info = CommissionGradeTracking.objects.filter(
                company=company,
                policy__id=policy_data['order__policy__id'],
                is_active=True
            ).first()
            
            grade_status = None
            if grade_info:
                grade_status = grade_info.get_grade_status()
            
            policy_performance.append({
                'policy_title': policy_data['order__policy__title'],
                'order_count': policy_data['order_count'],
                'total_commission': policy_data['total_commission'],
                'avg_commission': policy_data['avg_commission'],
                'completion_rate': round(policy_data['completion_rate'], 2),
                'grade_status': grade_status
            })
        
        return policy_performance[:10]  # Top 10
    
    def _get_payment_schedule(self, company):
        """입금 예정 스케줄"""
        # 다음 30일 내 예정된 입금
        upcoming_payments = Settlement.objects.filter(
            company=company,
            status__in=['approved', 'unpaid'],
            expected_payment_date__lte=timezone.now().date() + timedelta(days=30)
        ).values(
            'expected_payment_date'
        ).annotate(
            amount=Sum('rebate_amount'),
            count=Count('id')
        ).order_by('expected_payment_date')
        
        # 지급할 예정인 금액 (하위 판매점에게)
        outgoing_payments = Settlement.objects.filter(
            company__parent_company=company,
            status__in=['approved', 'unpaid'],
            expected_payment_date__lte=timezone.now().date() + timedelta(days=30)
        ).values(
            'expected_payment_date'
        ).annotate(
            amount=Sum('rebate_amount'),
            count=Count('id')
        ).order_by('expected_payment_date')
        
        return {
            'incoming': list(upcoming_payments),
            'outgoing': list(outgoing_payments)
        }
    
    def _get_performance_alerts(self, company):
        """성과 및 주의사항 알림"""
        alerts = []
        
        # 1. 미입금 알림
        unpaid_count = Settlement.objects.filter(
            company=company,
            status='unpaid'
        ).count()
        
        if unpaid_count > 0:
            alerts.append({
                'type': 'warning',
                'category': 'payment',
                'message': f'미입금 정산 {unpaid_count}건이 있습니다.',
                'count': unpaid_count,
                'priority': 'medium'
            })
        
        # 2. 연체 알림
        overdue_count = Settlement.objects.filter(
            company=company,
            status__in=['approved', 'unpaid'],
            expected_payment_date__lt=timezone.now().date()
        ).count()
        
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'category': 'overdue',
                'message': f'예정일을 지난 정산 {overdue_count}건이 있습니다.',
                'count': overdue_count,
                'priority': 'high'
            })
        
        # 3. 그레이드 달성 알림
        near_target_grades = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        )
        
        for grade in near_target_grades:
            achievement_rate = grade.calculate_achievement_rate()
            remaining_days = (grade.period_end - timezone.now().date()).days
            
            if 80 <= achievement_rate < 100 and remaining_days <= 7:
                alerts.append({
                    'type': 'info',
                    'category': 'grade',
                    'message': f'{grade.policy.title} 그레이드 달성까지 얼마 남지 않았습니다. ({achievement_rate:.1f}% 달성)',
                    'remaining_days': remaining_days,
                    'achievement_rate': achievement_rate,
                    'priority': 'medium'
                })
        
        # 4. 하위 판매점 성과 알림
        poor_performers = Settlement.objects.filter(
            company__parent_company=company,
            created_at__gte=timezone.now().date() - timedelta(days=30)
        ).values(
            'company__name'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid')),
            payment_rate=Case(
                When(total_amount__gt=0, then=F('paid_amount') * 100.0 / F('total_amount')),
                default=Value(0),
                output_field=DecimalField()
            )
        ).filter(payment_rate__lt=50)  # 50% 이하 성과
        
        if poor_performers.exists():
            poor_count = poor_performers.count()
            alerts.append({
                'type': 'warning',
                'category': 'performance',
                'message': f'{poor_count}개 판매점이 저조한 성과를 보이고 있습니다.',
                'count': poor_count,
                'details': list(poor_performers.values('company__name', 'payment_rate'))[:5],
                'priority': 'medium'
            })
        
        # 우선순위로 정렬
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return alerts


class RetailSettlementDashboard(APIView):
    """판매점용 정산 대시보드 - 고도화된 기능 포함"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """판매점 대시보드 데이터"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response(
                    {'error': '판매점 권한이 필요합니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            period = request.query_params.get('period', '30')
            days = int(period) if period.isdigit() else 30
            start_date = timezone.now() - timedelta(days=days)
            
            dashboard_data = {
                'company_info': {
                    'name': company.name,
                    'type': company.get_type_display(),
                    'parent_company': company.parent_company.name if company.parent_company else None,
                    'member_since': company.created_at.strftime('%Y-%m-%d') if hasattr(company, 'created_at') else None
                },
                'earnings_summary': self._get_earnings_summary(company, start_date),
                'receivables': self._get_receivables(company, start_date),
                'grade_status': self._get_grade_status(company),
                'performance_insights': self._get_performance_insights(company),
                'monthly_performance': self._get_monthly_performance(company),
                'policy_breakdown': self._get_policy_breakdown(company, start_date),
                'optimization_tips': self._get_optimization_tips(company),
                'achievement_milestones': self._get_achievement_milestones(company),
                'competitor_benchmark': self._get_competitor_benchmark(company, start_date)
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            logger.error(f"판매점 대시보드 오류: {str(e)}")
            return Response(
                {'error': '대시보드 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_receivables(self, company, start_date):
        """받을 수수료"""
        return Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            pending_count=Count('id', filter=Q(status='pending')),
            approved_count=Count('id', filter=Q(status='approved')),
            paid_count=Count('id', filter=Q(status='paid')),
            unpaid_count=Count('id', filter=Q(status='unpaid'))
        )
    
    def _get_grade_status(self, company):
        """그레이드 현황"""
        trackings = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        ).select_related('policy')
        
        grade_data = []
        for tracking in trackings:
            grade_status = tracking.get_grade_status()
            grade_data.append({
                'policy_title': tracking.policy.title,
                'period_type': tracking.get_period_type_display(),
                **grade_status
            })
        
        return {
            'trackings': grade_data,
            'total_bonus': sum(t['total_bonus'] for t in grade_data)
        }
    
    def _get_monthly_performance(self, company):
        """월별 성과"""
        performance = []
        
        for i in range(6):
            target_date = timezone.now() - timedelta(days=30*i)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            from orders.models import Order
            orders = Order.objects.filter(
                company=company,
                created_at__gte=month_start,
                created_at__lt=next_month
            )
            
            settlements = Settlement.objects.filter(
                company=company,
                created_at__gte=month_start,
                created_at__lt=next_month
            )
            
            order_stats = orders.aggregate(
                order_count=Count('id'),
                completed_orders=Count('id', filter=Q(status__in=['completed', 'final_approved']))
            )
            
            settlement_stats = settlements.aggregate(
                settlement_amount=Sum('rebate_amount'),
                paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
            )
            
            performance.append({
                'year_month': month_start.strftime('%Y-%m'),
                'order_count': order_stats['order_count'] or 0,
                'completed_orders': order_stats['completed_orders'] or 0,
                'settlement_amount': settlement_stats['settlement_amount'] or 0,
                'paid_amount': settlement_stats['paid_amount'] or 0
            })
        
        performance.reverse()
        return performance
    
    def _get_policy_breakdown(self, company, start_date):
        """정책별 분석"""
        return list(Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).values(
            'order__policy__title'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
        ).order_by('-total_amount'))
    
    def _get_earnings_summary(self, company, start_date):
        """수익 요약 - 판매점 특화 수익 분석"""
        # 기본 수익 정보
        base_earnings = Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total_earnings=Sum('rebate_amount'),
            confirmed_earnings=Sum('rebate_amount', filter=Q(status='paid')),
            pending_earnings=Sum('rebate_amount', filter=Q(status__in=['pending', 'approved', 'unpaid'])),
            avg_per_settlement=Avg('rebate_amount')
        )
        
        # 그레이드 보너스 수익
        bonus_earnings = GradeBonusSettlement.objects.filter(
            grade_tracking__company=company,
            created_at__gte=start_date
        ).aggregate(
            total_bonus=Sum('bonus_amount'),
            paid_bonus=Sum('bonus_amount', filter=Q(status='paid'))
        )
        
        # 월별 성장률 계산
        last_month_start = start_date - timedelta(days=30)
        last_month_earnings = Settlement.objects.filter(
            company=company,
            created_at__gte=last_month_start,
            created_at__lt=start_date
        ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
        
        current_earnings = base_earnings['total_earnings'] or 0
        growth_rate = 0
        if last_month_earnings > 0:
            growth_rate = ((current_earnings - last_month_earnings) / last_month_earnings) * 100
        
        return {
            **base_earnings,
            **bonus_earnings,
            'growth_rate': round(growth_rate, 2),
            'total_with_bonus': (current_earnings + (bonus_earnings['total_bonus'] or 0)),
            'earnings_efficiency': self._calculate_earnings_efficiency(company, start_date)
        }
    
    def _calculate_earnings_efficiency(self, company, start_date):
        """수익 효율성 계산 (주문당 평균 수익)"""
        from orders.models import Order
        
        orders_count = Order.objects.filter(
            company=company,
            created_at__gte=start_date,
            status__in=['completed', 'final_approved']
        ).count()
        
        total_earnings = Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
        
        if orders_count > 0:
            return round(total_earnings / orders_count, 2)
        return 0
    
    def _get_performance_insights(self, company):
        """성과 인사이트 - 판매점 성과 분석 및 개선 방향"""
        insights = []
        
        # 1. 그레이드 달성률 분석
        active_grades = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        )
        
        for grade in active_grades:
            achievement_rate = grade.calculate_achievement_rate()
            remaining_days = (grade.period_end - timezone.now().date()).days
            
            if achievement_rate >= 90:
                insights.append({
                    'type': 'success',
                    'category': 'grade_achievement',
                    'message': f'{grade.policy.title} 그레이드 목표 달성 진행률이 매우 우수합니다! ({achievement_rate:.1f}%)',
                    'action': f'남은 {grade.target_orders - grade.current_orders}건 달성하면 최고 그레이드 달성입니다.',
                    'priority': 'high'
                })
            elif 70 <= achievement_rate < 90:
                insights.append({
                    'type': 'info',
                    'category': 'grade_opportunity',
                    'message': f'{grade.policy.title} 그레이드 목표까지 얼마 남지 않았습니다. ({achievement_rate:.1f}%)',
                    'action': f'남은 {remaining_days}일 동안 {grade.target_orders - grade.current_orders}건만 더 달성하세요!',
                    'priority': 'medium'
                })
            elif achievement_rate < 50 and remaining_days <= 10:
                insights.append({
                    'type': 'warning',
                    'category': 'grade_risk',
                    'message': f'{grade.policy.title} 그레이드 목표 달성이 어려울 수 있습니다.',
                    'action': f'다음 기간에는 더 적극적으로 참여해보세요.',
                    'priority': 'low'
                })
        
        # 2. 수익 패턴 분석
        recent_settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=timezone.now().date() - timedelta(days=60)
        ).order_by('-created_at')[:10]
        
        if recent_settlements.count() >= 5:
            amounts = [s.rebate_amount for s in recent_settlements]
            avg_amount = sum(amounts) / len(amounts)
            recent_avg = sum(amounts[:3]) / 3
            
            if recent_avg > avg_amount * 1.2:
                insights.append({
                    'type': 'success',
                    'category': 'earning_trend',
                    'message': '최근 수익이 증가 추세를 보이고 있습니다!',
                    'action': '현재의 전략을 유지하세요.',
                    'priority': 'medium'
                })
            elif recent_avg < avg_amount * 0.8:
                insights.append({
                    'type': 'warning',
                    'category': 'earning_decline',
                    'message': '최근 수익이 전부 대비 감소했습니다.',
                    'action': '수익성이 높은 정책에 집중해보세요.',
                    'priority': 'medium'
                })
        
        # 3. 결제 상태 분석
        payment_stats = Settlement.objects.filter(
            company=company,
            created_at__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(
            total_count=Count('id'),
            paid_count=Count('id', filter=Q(status='paid')),
            unpaid_count=Count('id', filter=Q(status='unpaid'))
        )
        
        if payment_stats['unpaid_count'] > 0:
            insights.append({
                'type': 'warning',
                'category': 'payment_issue',
                'message': f'미입금 정산이 {payment_stats["unpaid_count"]}건 있습니다.',
                'action': '협력사에 문의하여 입금 상황을 확인해보세요.',
                'priority': 'high'
            })
        
        return insights
    
    def _get_optimization_tips(self, company):
        """최적화 팁 - 수익 그및 성과 향상 제안"""
        tips = []
        
        # 정책별 수익성 분석
        policy_performance = Settlement.objects.filter(
            company=company,
            created_at__gte=timezone.now().date() - timedelta(days=60)
        ).values(
            'order__policy__title'
        ).annotate(
            avg_amount=Avg('rebate_amount'),
            total_count=Count('id')
        ).order_by('-avg_amount')
        
        if policy_performance.count() >= 2:
            best_policy = policy_performance.first()
            tips.append({
                'category': 'high_value_policy',
                'title': '고수익 정책 집중',
                'description': f'"{best_policy["order__policy__title"]}"이 가장 높은 평균 수융을 발생시키고 있습니다.',
                'action': f'평균 {best_policy["avg_amount"]:,.0f}원의 수익을 얻을 수 있는 이 정책에 더 집중해보세요.',
                'impact': 'high',
                'difficulty': 'easy'
            })
        
        # 그레이드 및 보너스 최적화
        near_achievement_grades = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        ).annotate(
            achievement_rate=F('current_orders') * 100.0 / F('target_orders')
        ).filter(achievement_rate__gte=60, achievement_rate__lt=100)
        
        for grade in near_achievement_grades:
            remaining = grade.target_orders - grade.current_orders
            remaining_days = (grade.period_end - timezone.now().date()).days
            
            if remaining_days > 0:
                daily_target = remaining / remaining_days
                tips.append({
                    'category': 'grade_optimization',
                    'title': f'{grade.policy.title} 그레이드 달성 전략',
                    'description': f'하루 평균 {daily_target:.1f}건만 더 달성하면 그레이드 보너스를 받을 수 있습니다.',
                    'action': f'남은 {remaining_days}일 동안 {remaining}건 달성 목표',
                    'impact': 'high',
                    'difficulty': 'medium'
                })
        
        # 결제 속도 개선
        avg_payment_days = Settlement.objects.filter(
            company=company,
            status='paid',
            paid_at__isnull=False,
            created_at__gte=timezone.now().date() - timedelta(days=90)
        ).annotate(
            days_to_payment=F('paid_at__date') - F('created_at__date')
        ).aggregate(
            avg_days=Avg('days_to_payment')
        )['avg_days']
        
        if avg_payment_days and avg_payment_days > 10:
            tips.append({
                'category': 'payment_optimization',
                'title': '빠른 결제 처리를 위한 팁',
                'description': f'평균 결제까지 {avg_payment_days:.0f}일이 소요되고 있습니다.',
                'action': '협력사와 자동 이체 설정을 논의해보세요.',
                'impact': 'medium',
                'difficulty': 'easy'
            })
        
        return tips
    
    def _get_achievement_milestones(self, company):
        """달성 마일스톤 - 판매점의 성과 이정표"""
        milestones = []
        
        # 현재 총 수익 계산
        total_earnings = Settlement.objects.filter(
            company=company,
            status='paid'
        ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
        
        # 수익 마일스톤 정의
        earning_milestones = [
            {'threshold': 1000000, 'title': '첫 100만원 달성', 'tier': 'Bronze'},
            {'threshold': 5000000, 'title': '500만원 달성', 'tier': 'Silver'},
            {'threshold': 10000000, 'title': '1천만원 달성', 'tier': 'Gold'},
            {'threshold': 25000000, 'title': '2천5백만원 달성', 'tier': 'Platinum'},
            {'threshold': 50000000, 'title': '5천만원 달성', 'tier': 'Diamond'}
        ]
        
        for milestone in earning_milestones:
            threshold = milestone['threshold']
            progress = min(100, (total_earnings / threshold) * 100)
            
            milestones.append({
                'category': 'earnings',
                'title': milestone['title'],
                'tier': milestone['tier'],
                'current_value': total_earnings,
                'target_value': threshold,
                'progress_percentage': round(progress, 1),
                'is_achieved': total_earnings >= threshold,
                'remaining_amount': max(0, threshold - total_earnings)
            })
        
        # 그레이드 달성 마일스톤
        grade_milestones = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        )
        
        for grade in grade_milestones:
            achievement_rate = grade.calculate_achievement_rate()
            milestones.append({
                'category': 'grade',
                'title': f'{grade.policy.title} {grade.get_period_type_display()} 그레이드',
                'tier': f'Level {grade.achieved_grade_level}',
                'current_value': grade.current_orders,
                'target_value': grade.target_orders,
                'progress_percentage': round(achievement_rate, 1),
                'is_achieved': achievement_rate >= 100,
                'remaining_amount': max(0, grade.target_orders - grade.current_orders),
                'bonus_amount': grade.bonus_per_order
            })
        
        # 연속 달성 기록
        from orders.models import Order
        recent_months_performance = []
        
        for i in range(6):
            target_date = timezone.now() - timedelta(days=30*i)
            month_start = target_date.replace(day=1)
            
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            month_orders = Order.objects.filter(
                company=company,
                created_at__gte=month_start,
                created_at__lt=next_month,
                status__in=['completed', 'final_approved']
            ).count()
            
            recent_months_performance.append(month_orders > 0)
        
        consecutive_months = 0
        for has_orders in recent_months_performance:
            if has_orders:
                consecutive_months += 1
            else:
                break
        
        if consecutive_months > 0:
            milestones.append({
                'category': 'consistency',
                'title': '연속 활동 기록',
                'tier': f'{consecutive_months}개월 연속',
                'current_value': consecutive_months,
                'target_value': 12,
                'progress_percentage': round((consecutive_months / 12) * 100, 1),
                'is_achieved': consecutive_months >= 12,
                'description': f'{consecutive_months}개월 연속으로 주문을 처리했습니다.'
            })
        
        return sorted(milestones, key=lambda x: x['progress_percentage'], reverse=True)
    
    def _get_competitor_benchmark(self, company, start_date):
        """경쟁사 벤치마킹 - 같은 협력사 내 다른 판매점들과 비교"""
        if not company.parent_company:
            return {'message': '벤치마킹 데이터를 사용할 수 없습니다.'}
        
        # 같은 협력사 하위의 다른 판매점들
        peer_companies = Company.objects.filter(
            parent_company=company.parent_company,
            type='retail'
        ).exclude(id=company.id)
        
        if not peer_companies.exists():
            return {'message': '비교할 판매점이 없습니다.'}
        
        # 내 성과
        my_performance = Settlement.objects.filter(
            company=company,
            created_at__gte=start_date
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            avg_amount=Avg('rebate_amount')
        )
        
        # 동료 판매점들의 성과
        peer_performances = []
        for peer in peer_companies:
            peer_stats = Settlement.objects.filter(
                company=peer,
                created_at__gte=start_date
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_count=Count('id'),
                avg_amount=Avg('rebate_amount')
            )
            
            if peer_stats['total_count'] and peer_stats['total_count'] > 0:
                peer_performances.append({
                    'company_name': peer.name[:10] + '***',  # 개인정보 보호
                    'total_amount': peer_stats['total_amount'] or 0,
                    'total_count': peer_stats['total_count'] or 0,
                    'avg_amount': peer_stats['avg_amount'] or 0
                })
        
        if not peer_performances:
            return {'message': '비교할 데이터가 충분하지 않습니다.'}
        
        # 순위 계산
        all_performances = peer_performances + [{
            'company_name': '내 성과',
            'total_amount': my_performance['total_amount'] or 0,
            'total_count': my_performance['total_count'] or 0,
            'avg_amount': my_performance['avg_amount'] or 0,
            'is_me': True
        }]
        
        # 총액 기준 순위
        amount_ranking = sorted(all_performances, key=lambda x: x['total_amount'], reverse=True)
        my_amount_rank = next((i+1 for i, p in enumerate(amount_ranking) if p.get('is_me')), len(amount_ranking))
        
        # 건수 기준 순위
        count_ranking = sorted(all_performances, key=lambda x: x['total_count'], reverse=True)
        my_count_rank = next((i+1 for i, p in enumerate(count_ranking) if p.get('is_me')), len(count_ranking))
        
        # 평균 기준 순위
        avg_ranking = sorted(all_performances, key=lambda x: x['avg_amount'] or 0, reverse=True)
        my_avg_rank = next((i+1 for i, p in enumerate(avg_ranking) if p.get('is_me')), len(avg_ranking))
        
        # 상위 3위 공개 (개인정보 보호)
        top3_amount = [p for p in amount_ranking[:3] if not p.get('is_me')]
        
        return {
            'total_peers': len(peer_performances),
            'my_rankings': {
                'amount_rank': my_amount_rank,
                'count_rank': my_count_rank,
                'avg_rank': my_avg_rank,
                'total_participants': len(all_performances)
            },
            'my_performance': my_performance,
            'top_performers': top3_amount[:3],
            'percentile': {
                'amount': round((1 - (my_amount_rank - 1) / len(all_performances)) * 100, 1),
                'count': round((1 - (my_count_rank - 1) / len(all_performances)) * 100, 1),
                'avg': round((1 - (my_avg_rank - 1) / len(all_performances)) * 100, 1)
            },
            'improvement_suggestions': self._get_improvement_suggestions(my_amount_rank, len(all_performances))
        }
    
    def _get_improvement_suggestions(self, rank, total):
        """순위에 따른 개선 제안"""
        percentile = (1 - (rank - 1) / total) * 100
        
        if percentile >= 80:
            return [
                "훌륭한 성과를 보이고 있습니다!",
                "현재의 전략을 유지하면서 꾸준히 활동해보세요.",
                "다른 판매점들에게 노하우를 공유해보는 것은 어떨까요?"
            ]
        elif percentile >= 60:
            return [
                "상위권 성과를 보이고 있습니다.",
                "그레이드 달성에 더 집중해서 보너스를 노려보세요.",
                "고수익 정책들을 더 적극 활용해보세요."
            ]
        elif percentile >= 40:
            return [
                "평균적인 성과를 보이고 있습니다.",
                "상위 성과자들의 전략을 벤치마킹해보세요.",
                "그레이드 시스템을 적극 활용하면 수익을 늘릴 수 있습니다."
            ]
        else:
            return [
                "더 많은 기회를 잡을 수 있습니다!",
                "협력사에 성과 향상 방법을 문의해보세요.",
                "꾸준한 활동이 성과 향상의 핵심입니다."
            ]


class SettlementAnalyticsDashboard(APIView):
    """정산 분석 대시보드 (공통 분석 기능)"""
    permission_classes = [IsAuthenticated, HierarchyPermission]
    
    def get(self, request):
        """분석 데이터 반환"""
        try:
            analysis_type = request.query_params.get('type', 'overview')
            
            if analysis_type == 'overview':
                return self._get_overview_analysis(request)
            elif analysis_type == 'trends':
                return self._get_trend_analysis(request)
            elif analysis_type == 'comparison':
                return self._get_comparison_analysis(request)
            else:
                return Response(
                    {'error': '지원되지 않는 분석 타입입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"정산 분석 데이터 조회 실패: {str(e)}")
            return Response(
                {'error': '분석 데이터를 불러올 수 없습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_overview_analysis(self, request):
        """개요 분석"""
        queryset = self._get_filtered_queryset(request)
        
        period = request.query_params.get('period', '90')
        days = int(period) if period.isdigit() else 90
        start_date = timezone.now() - timedelta(days=days)
        
        filtered_queryset = queryset.filter(created_at__gte=start_date)
        
        analysis = {
            'total_stats': self._calculate_total_stats(filtered_queryset),
            'daily_trends': self._calculate_daily_trends(filtered_queryset),
            'status_distribution': self._calculate_status_distribution(filtered_queryset),
            'company_ranking': self._calculate_company_ranking(filtered_queryset),
        }
        
        return Response(analysis)
    
    def _get_filtered_queryset(self, request):
        """사용자 권한에 따른 쿼리셋 필터링"""
        user = request.user
        
        if user.is_superuser:
            return Settlement.objects.all()
        
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
            
            if company.type == 'headquarters':
                return Settlement.objects.all()
            elif company.type == 'agency':
                return Settlement.objects.filter(
                    Q(company=company) |
                    Q(company__parent_company=company)
                )
            else:
                return Settlement.objects.filter(company=company)
                
        except:
            return Settlement.objects.none()
    
    def _calculate_total_stats(self, queryset):
        """총계 통계"""
        return queryset.aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            avg_amount=Avg('rebate_amount'),
            pending_count=Count('id', filter=Q(status='pending')),
            approved_count=Count('id', filter=Q(status='approved')),
            paid_count=Count('id', filter=Q(status='paid')),
            unpaid_count=Count('id', filter=Q(status='unpaid')),
            cancelled_count=Count('id', filter=Q(status='cancelled'))
        )
    
    def _calculate_daily_trends(self, queryset):
        """일별 트렌드"""
        return list(queryset.extra(
            select={'date': 'DATE(created_at)'}
        ).values('date').annotate(
            amount=Sum('rebate_amount'),
            count=Count('id')
        ).order_by('date'))

    def _calculate_status_distribution(self, queryset):
        """상태별 분포"""
        return queryset.values('status').annotate(
            count=Count('id'),
            amount=Sum('rebate_amount')
        ).order_by('-amount')
    
    def _calculate_company_ranking(self, queryset):
        """업체별 순위"""
        return list(queryset.values(
            'company__name', 'company__type'
        ).annotate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            paid_amount=Sum('rebate_amount', filter=Q(status='paid'))
        ).order_by('-total_amount')[:10])

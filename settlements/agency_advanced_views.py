"""
Phase 5-2: 협력사용 정산 대시보드 고도화
추가된 전문 기능들
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import (
    Sum, Count, Avg, Q, F, Case, When, Value, IntegerField, DecimalField
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Settlement, CommissionGradeTracking
from companies.models import Company
from .dashboard_views import AgencySettlementDashboard

logger = logging.getLogger(__name__)


class AgencyAdvancedDashboard(APIView):
    """협력사 전문 대시보드 - 추가 기능들"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """고급 대시보드 데이터 - 쿼리 파라미터로 기능 선택"""
        feature = request.query_params.get('feature', 'cash_flow_forecast')
        
        if feature == 'cash_flow_forecast':
            return self.cash_flow_forecast(request)
        elif feature == 'profitability_analysis':
            return self.profitability_analysis(request)
        elif feature == 'subordinate_ranking':
            return self.subordinate_ranking(request)
        else:
            return Response({'error': '지원하지 않는 기능입니다.'}, status=400)
    
    def cash_flow_forecast(self, request):
        """현금 흐름 예측 - 다음 3개월"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'agency':
                return Response({'error': '협력사만 접근 가능합니다.'}, status=403)
            
            forecast_data = self._generate_cash_flow_forecast(company)
            return Response(forecast_data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def profitability_analysis(self, request):
        """수익성 분석 - 정책별/판매점별 수익률"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'agency':
                return Response({'error': '협력사만 접근 가능합니다.'}, status=403)
            
            analysis_data = self._generate_profitability_analysis(company)
            return Response(analysis_data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def subordinate_ranking(self, request):
        """하위 판매점 순위 및 성과 평가"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'agency':
                return Response({'error': '협력사만 접근 가능합니다.'}, status=403)
            
            ranking_period = request.query_params.get('period', '30')
            ranking_data = self._generate_subordinate_ranking(company, int(ranking_period))
            return Response(ranking_data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def _generate_cash_flow_forecast(self, company):
        """현금 흐름 예측 로직"""
        from django.utils import timezone
        from datetime import timedelta
        import statistics
        
        # 지난 6개월 데이터를 기반으로 예측
        historical_data = []
        for i in range(6):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            inflow = Settlement.objects.filter(
                company=company,
                paid_at__gte=month_start,
                paid_at__lt=next_month
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            outflow = Settlement.objects.filter(
                company__parent_company=company,
                paid_at__gte=month_start,
                paid_at__lt=next_month
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            historical_data.append({
                'inflow': inflow,
                'outflow': outflow,
                'net_flow': inflow - outflow
            })
        
        # 평균을 기반으로 향후 3개월 예측
        avg_inflow = statistics.mean([d['inflow'] for d in historical_data])
        avg_outflow = statistics.mean([d['outflow'] for d in historical_data])
        
        forecast = []
        for i in range(3):
            future_month = timezone.now().replace(day=1) + timedelta(days=32*(i+1))
            forecast.append({
                'month': future_month.strftime('%Y-%m'),
                'predicted_inflow': round(avg_inflow, 2),
                'predicted_outflow': round(avg_outflow, 2),
                'predicted_net_flow': round(avg_inflow - avg_outflow, 2)
            })
        
        return {
            'historical_average': {
                'avg_inflow': round(avg_inflow, 2),
                'avg_outflow': round(avg_outflow, 2),
                'avg_net_flow': round(avg_inflow - avg_outflow, 2)
            },
            'forecast': forecast
        }
    
    def _generate_profitability_analysis(self, company):
        """수익성 분석 로직"""
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=90)
        
        # 정책별 수익성
        policy_profitability = Settlement.objects.filter(
            Q(company=company) | Q(company__parent_company=company),
            created_at__gte=start_date
        ).values(
            'order__policy__title'
        ).annotate(
            total_revenue=Sum('rebate_amount', filter=Q(company=company)),
            total_cost=Sum('rebate_amount', filter=Q(company__parent_company=company)),
            net_profit=F('total_revenue') - F('total_cost'),
            margin=Case(
                When(total_revenue__gt=0, then=F('net_profit') * 100.0 / F('total_revenue')),
                default=Value(0),
                output_field=DecimalField()
            )
        ).order_by('-net_profit')
        
        # 판매점별 수익성
        subordinate_profitability = []
        subordinates = Company.objects.filter(parent_company=company)
        
        for sub in subordinates:
            revenue = Settlement.objects.filter(
                company=company,
                order__company=sub,
                created_at__gte=start_date
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            cost = Settlement.objects.filter(
                company=sub,
                created_at__gte=start_date
            ).aggregate(amount=Sum('rebate_amount'))['amount'] or 0
            
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            subordinate_profitability.append({
                'company_name': sub.name,
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'margin': round(margin, 2)
            })
        
        subordinate_profitability.sort(key=lambda x: x['profit'], reverse=True)
        
        return {
            'policy_profitability': list(policy_profitability),
            'subordinate_profitability': subordinate_profitability
        }
    
    def _generate_subordinate_ranking(self, company, period_days):
        """하위 판매점 순위 생성"""
        from datetime import timedelta
        
        start_date = timezone.now().date() - timedelta(days=period_days)
        subordinates = Company.objects.filter(parent_company=company)
        
        ranking_data = []
        for sub in subordinates:
            stats = Settlement.objects.filter(
                company=sub,
                created_at__date__gte=start_date
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_count=Count('id'),
                paid_count=Count('id', filter=Q(status='paid')),
                avg_amount=Avg('rebate_amount')
            )
            
            payment_rate = 0
            if stats['total_count'] > 0:
                payment_rate = (stats['paid_count'] / stats['total_count']) * 100
            
            # 그레이드 현황
            grade_info = CommissionGradeTracking.objects.filter(
                company=sub,
                is_active=True
            ).aggregate(
                avg_achievement=Avg('current_orders') * 100.0 / Avg('target_orders'),
                total_bonus=Sum('total_bonus')
            )
            
            ranking_data.append({
                'company_name': sub.name,
                'rank': 0,  # 임시, 아래에서 계산
                'total_amount': stats['total_amount'] or 0,
                'total_count': stats['total_count'] or 0,
                'avg_amount': stats['avg_amount'] or 0,
                'payment_rate': round(payment_rate, 2),
                'grade_achievement': round(grade_info['avg_achievement'] or 0, 2),
                'total_bonus': grade_info['total_bonus'] or 0,
                'performance_score': self._calculate_performance_score(stats, payment_rate, grade_info)
            })
        
        # 성과 점수로 순위 매기기
        ranking_data.sort(key=lambda x: x['performance_score'], reverse=True)
        for i, data in enumerate(ranking_data):
            data['rank'] = i + 1
        
        return ranking_data
    
    def _calculate_performance_score(self, stats, payment_rate, grade_info):
        """성과 점수 계산 (0-100점)"""
        # 가중치: 총액 40%, 결제율 30%, 그레이드달성률 30%
        amount_score = min((stats['total_amount'] or 0) / 1000000 * 40, 40)  # 100만원당 40점까지
        payment_score = payment_rate * 0.3  # 결제율 30%까지
        grade_score = (grade_info['avg_achievement'] or 0) * 0.3  # 그레이드달성률 30%까지
        
        return round(amount_score + payment_score + grade_score, 2)

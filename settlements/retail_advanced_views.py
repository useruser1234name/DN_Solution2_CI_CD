"""
Phase 5-2: 소매점용 정산 대시보드 고도화
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
from .dashboard_views import RetailSettlementDashboard

logger = logging.getLogger(__name__)


class RetailAdvancedDashboard(APIView):
    """소매점 전문 대시보드 - 추가 기능들"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """고급 대시보드 데이터 - 쿼리 파라미터로 기능 선택"""
        feature = request.query_params.get('feature', 'performance_insights')
        
        if feature == 'performance_insights':
            return self.performance_insights(request)
        elif feature == 'seasonal_analysis':
            return self.seasonal_analysis(request)
        elif feature == 'optimization_tips':
            return self.optimization_tips(request)
        elif feature == 'grade_strategy':
            return self.grade_strategy(request)
        else:
            return Response({'error': '지원하지 않는 기능입니다.'}, status=400)
    
    def performance_insights(self, request):
        """성과 인사이트 - AI 기반 분석 및 개선 제안"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response({'error': '소매점만 접근 가능합니다.'}, status=403)
            
            insights = self._generate_performance_insights(company)
            return Response(insights)
            
        except Exception as e:
            logger.error(f"성과 인사이트 생성 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
    def seasonal_analysis(self, request):
        """계절별 분석 - 월별/계절별 성과 패턴"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response({'error': '소매점만 접근 가능합니다.'}, status=403)
            
            analysis = self._generate_seasonal_analysis(company)
            return Response(analysis)
            
        except Exception as e:
            logger.error(f"계절별 분석 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
    def optimization_tips(self, request):
        """최적화 팁 - 데이터 기반 개선 제안"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response({'error': '소매점만 접근 가능합니다.'}, status=403)
            
            tips = self._generate_optimization_tips(company)
            return Response(tips)
            
        except Exception as e:
            logger.error(f"최적화 팁 생성 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
    def grade_strategy(self, request):
        """그레이드 달성 전략"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response({'error': '소매점만 접근 가능합니다.'}, status=403)
            
            strategies = self._get_grade_strategies(company)
            return Response({'strategies': strategies})
            
        except Exception as e:
            logger.error(f"그레이드 전략 생성 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
    def _generate_performance_insights(self, company):
        """성과 인사이트 생성"""
        insights = {
            'overall_score': 0,
            'strengths': [],
            'improvements': [],
            'recommendations': [],
            'trends': {}
        }
        
        # 최근 3개월 데이터 분석
        three_months_ago = timezone.now() - timedelta(days=90)
        settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=three_months_ago
        )
        
        if not settlements.exists():
            return insights
        
        # 전체 성과 점수 계산
        total_amount = settlements.aggregate(Sum('rebate_amount'))['rebate_amount__sum'] or 0
        total_orders = settlements.count()
        avg_amount = settlements.aggregate(Avg('rebate_amount'))['rebate_amount__avg'] or 0
        
        # 점수 계산 (0-100)
        score = min(100, (total_orders * 10) + (float(avg_amount) / 1000))
        insights['overall_score'] = round(score, 1)
        
        # 강점 분석
        if total_orders > 50:
            insights['strengths'].append('높은 주문 처리량')
        if avg_amount > 50000:
            insights['strengths'].append('높은 평균 수익')
        
        # 개선점 분석
        recent_week = timezone.now() - timedelta(days=7)
        recent_orders = settlements.filter(created_at__gte=recent_week).count()
        if recent_orders < 5:
            insights['improvements'].append('최근 활동량 증대 필요')
        
        # 추천사항
        insights['recommendations'] = self._get_personalized_recommendations(company)
        
        # 트렌드 분석
        insights['trends'] = self._analyze_trends(company)
        
        return insights
    
    def _generate_seasonal_analysis(self, company):
        """계절별 분석 생성"""
        analysis = {
            'monthly_performance': [],
            'seasonal_patterns': {},
            'best_months': [],
            'opportunities': []
        }
        
        # 월별 성과
        for month in range(1, 13):
            monthly_data = Settlement.objects.filter(
                company=company,
                created_at__month=month
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_orders=Count('id'),
                avg_amount=Avg('rebate_amount')
            )
            
            analysis['monthly_performance'].append({
                'month': month,
                'month_name': self._get_month_name(month),
                'total_amount': monthly_data['total_amount'] or 0,
                'total_orders': monthly_data['total_orders'] or 0,
                'avg_amount': monthly_data['avg_amount'] or 0
            })
        
        # 계절별 패턴
        seasons = {
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'autumn': [9, 10, 11],
            'winter': [12, 1, 2]
        }
        
        for season, months in seasons.items():
            seasonal_data = Settlement.objects.filter(
                company=company,
                created_at__month__in=months
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_orders=Count('id')
            )
            
            analysis['seasonal_patterns'][season] = {
                'total_amount': seasonal_data['total_amount'] or 0,
                'total_orders': seasonal_data['total_orders'] or 0,
                'season_name': self._get_season_name(season)
            }
        
        # 최고 성과 월
        best_months = sorted(
            analysis['monthly_performance'],
            key=lambda x: x['total_amount'],
            reverse=True
        )[:3]
        analysis['best_months'] = best_months
        
        # 계절별 기회
        analysis['opportunities'] = self._get_seasonal_opportunities(company)
        
        return analysis
    
    def _generate_optimization_tips(self, company):
        """최적화 팁 생성"""
        tips = []
        
        # 최근 60일 데이터 분석
        sixty_days_ago = timezone.now() - timedelta(days=60)
        settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=sixty_days_ago
        )
        
        if not settlements.exists():
            return tips
        
        # 시간대별 분석
        hourly_patterns = settlements.extra(
            select={'hour': 'EXTRACT(hour FROM created_at)'}
        ).values('hour').annotate(
            count=Count('id'),
            avg_amount=Avg('rebate_amount')
        ).order_by('-avg_amount')
        
        if hourly_patterns:
            best_hour = list(hourly_patterns)[0]
            tips.append({
                'category': 'timing',
                'title': '최적 활동 시간',
                'tip': f'{best_hour["hour"]}시에 가장 좋은 성과를 보입니다.',
                'action': f'{best_hour["hour"]}시 전후 시간대에 집중 활동해보세요.',
                'impact_level': 'high'
            })
        
        # 요일별 분석
        daily_patterns = settlements.extra(
            select={'weekday': 'EXTRACT(dow FROM created_at)'}
        ).values('weekday').annotate(
            count=Count('id'),
            avg_amount=Avg('rebate_amount')
        ).order_by('-avg_amount')
        
        if daily_patterns:
            best_day = list(daily_patterns)[0]
            weekdays = ['일', '월', '화', '수', '목', '금', '토']
            tips.append({
                'category': 'timing',
                'title': '최적 활동 요일',
                'tip': f'{weekdays[best_day["weekday"]]}요일에 가장 좋은 성과를 보입니다.',
                'action': f'{weekdays[best_day["weekday"]]}요일 패턴을 다른 요일에도 적용해보세요.',
                'impact_level': 'medium'
            })
        
        # 고수익 정책 추천
        best_policies = Settlement.objects.filter(
            company=company,
            created_at__gte=timezone.now() - timedelta(days=60)
        ).values('order__policy__title').annotate(
            avg_amount=Avg('rebate_amount'),
            count=Count('id')
        ).filter(count__gte=2).order_by('-avg_amount')[:2]
        
        if best_policies:
            policy = list(best_policies)[0]
            tips.append({
                'category': 'policy',
                'title': '고수익 정책 집중',
                'tip': f'"{policy["order__policy__title"]}"이 평균 {policy["avg_amount"]:,.0f}원 수익',
                'action': '이 정책에 더 집중하여 활동해보세요.',
                'impact_level': 'high'
            })
        
        return tips
    
    def _get_seasonal_opportunities(self, company):
        """계절별 기회"""
        current_month = timezone.now().month
        
        seasonal_tips = {
            1: {'season': '신년', 'opportunity': '신년 특별 프로모션 활용'},
            2: {'season': '겨울', 'opportunity': '겨울 특가 상품 집중'},
            3: {'season': '봄', 'opportunity': '새학기 수요 대비'},
            12: {'season': '연말', 'opportunity': '연말 이벤트 활용'}
        }
        
        if current_month in seasonal_tips:
            return [seasonal_tips[current_month]]
        
        return [{
            'season': '일반',
            'opportunity': '꾸준한 활동으로 안정적 수익 확보'
        }]
    
    def _get_grade_strategies(self, company):
        """그레이드 달성 전략"""
        strategies = []
        
        active_grades = CommissionGradeTracking.objects.filter(
            company=company,
            is_active=True
        )
        
        for grade in active_grades:
            remaining_days = (grade.period_end - timezone.now().date()).days
            remaining_orders = grade.target_orders - grade.current_orders
            
            if remaining_days > 0 and remaining_orders > 0:
                daily_target = remaining_orders / remaining_days
                
                if daily_target <= 1:
                    difficulty = '쉬움'
                elif daily_target <= 2:
                    difficulty = '보통'
                else:
                    difficulty = '어려움'
                
                strategies.append({
                    'policy': grade.policy.title,
                    'remaining_orders': remaining_orders,
                    'remaining_days': remaining_days,
                    'daily_target': round(daily_target, 1),
                    'difficulty': difficulty,
                    'potential_bonus': grade.bonus_per_order * remaining_orders,
                    'strategy': f'하루 평균 {daily_target:.1f}건씩 달성하면 그레이드 완료'
                })
        
        return strategies
    
    def _get_personalized_recommendations(self, company):
        """개인화된 추천사항"""
        recommendations = []
        
        # 최근 활동 패턴 분석
        recent_settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        if recent_settlements.count() < 10:
            recommendations.append({
                'type': 'activity',
                'message': '활동량을 늘려 더 많은 수익 기회를 만들어보세요.',
                'priority': 'high'
            })
        
        # 평균 수익 분석
        avg_amount = recent_settlements.aggregate(Avg('rebate_amount'))['rebate_amount__avg']
        if avg_amount and avg_amount < 30000:
            recommendations.append({
                'type': 'quality',
                'message': '고수익 정책에 집중하여 건당 수익을 높여보세요.',
                'priority': 'medium'
            })
        
        return recommendations
    
    def _analyze_trends(self, company):
        """트렌드 분석"""
        trends = {}
        
        # 최근 4주 트렌드
        weeks_data = []
        for i in range(4):
            week_start = timezone.now() - timedelta(weeks=i+1)
            week_end = timezone.now() - timedelta(weeks=i)
            
            week_data = Settlement.objects.filter(
                company=company,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(
                total_amount=Sum('rebate_amount'),
                total_orders=Count('id')
            )
            
            weeks_data.append({
                'week': f'{i+1}주 전',
                'amount': week_data['total_amount'] or 0,
                'orders': week_data['total_orders'] or 0
            })
        
        trends['weekly'] = list(reversed(weeks_data))
        
        return trends
    
    def _get_month_name(self, month):
        """월 이름 반환"""
        month_names = {
            1: '1월', 2: '2월', 3: '3월', 4: '4월',
            5: '5월', 6: '6월', 7: '7월', 8: '8월',
            9: '9월', 10: '10월', 11: '11월', 12: '12월'
        }
        return month_names.get(month, f'{month}월')
    
    def _get_season_name(self, season):
        """계절 이름 반환"""
        season_names = {
            'spring': '봄',
            'summer': '여름',
            'autumn': '가을',
            'winter': '겨울'
        }
        return season_names.get(season, season)


class RetailAnalyticsAPI(APIView):
    """소매점 분석 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """종합 분석 데이터 제공"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type != 'retail':
                return Response({'error': '소매점만 접근 가능합니다.'}, status=403)
            
            analytics_data = {
                'summary': self._get_summary_stats(company),
                'performance_score': self._calculate_performance_score(company),
                'growth_metrics': self._get_growth_metrics(company),
                'efficiency_metrics': self._get_efficiency_metrics(company)
            }
            
            return Response(analytics_data)
            
        except Exception as e:
            logger.error(f"분석 데이터 조회 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
    def _get_summary_stats(self, company):
        """요약 통계"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        stats = Settlement.objects.filter(
            company=company,
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_amount=Sum('rebate_amount'),
            total_orders=Count('id'),
            avg_amount=Avg('rebate_amount')
        )
        
        return {
            'total_revenue': stats['total_amount'] or 0,
            'total_orders': stats['total_orders'] or 0,
            'average_order_value': stats['avg_amount'] or 0,
            'period': '최근 30일'
        }
    
    def _calculate_performance_score(self, company):
        """성과 점수 계산"""
        # 복합 지표를 통한 성과 점수 계산
        thirty_days_ago = timezone.now() - timedelta(days=30)
        settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=thirty_days_ago
        )
        
        if not settlements.exists():
            return 0
        
        # 활동량 점수 (40%)
        order_count = settlements.count()
        activity_score = min(40, order_count * 2)
        
        # 수익성 점수 (40%)
        avg_amount = settlements.aggregate(Avg('rebate_amount'))['rebate_amount__avg'] or 0
        profitability_score = min(40, float(avg_amount) / 1000)
        
        # 일관성 점수 (20%)
        # 매일 활동하는지 체크
        active_days = settlements.dates('created_at', 'day').count()
        consistency_score = min(20, active_days * 0.67)
        
        total_score = activity_score + profitability_score + consistency_score
        return round(total_score, 1)
    
    def _get_growth_metrics(self, company):
        """성장 지표"""
        current_month = timezone.now().replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_data = Settlement.objects.filter(
            company=company,
            created_at__gte=current_month
        ).aggregate(
            amount=Sum('rebate_amount'),
            orders=Count('id')
        )
        
        last_data = Settlement.objects.filter(
            company=company,
            created_at__gte=last_month,
            created_at__lt=current_month
        ).aggregate(
            amount=Sum('rebate_amount'),
            orders=Count('id')
        )
        
        # 성장률 계산
        amount_growth = 0
        order_growth = 0
        
        if last_data['amount'] and last_data['amount'] > 0:
            amount_growth = ((current_data['amount'] or 0) - last_data['amount']) / last_data['amount'] * 100
        
        if last_data['orders'] and last_data['orders'] > 0:
            order_growth = ((current_data['orders'] or 0) - last_data['orders']) / last_data['orders'] * 100
        
        return {
            'revenue_growth': round(amount_growth, 1),
            'order_growth': round(order_growth, 1),
            'current_month_revenue': current_data['amount'] or 0,
            'current_month_orders': current_data['orders'] or 0
        }
    
    def _get_efficiency_metrics(self, company):
        """효율성 지표"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 시간당 평균 수익
        hourly_avg = Settlement.objects.filter(
            company=company,
            created_at__gte=thirty_days_ago
        ).extra(
            select={'hour': 'EXTRACT(hour FROM created_at)'}
        ).values('hour').annotate(
            avg_amount=Avg('rebate_amount')
        ).aggregate(
            overall_avg=Avg('avg_amount')
        )
        
        # 요일별 효율성
        daily_efficiency = Settlement.objects.filter(
            company=company,
            created_at__gte=thirty_days_ago
        ).extra(
            select={'weekday': 'EXTRACT(dow FROM created_at)'}
        ).values('weekday').annotate(
            avg_amount=Avg('rebate_amount'),
            count=Count('id')
        ).order_by('-avg_amount')
        
        best_day = None
        if daily_efficiency:
            weekdays = ['일', '월', '화', '수', '목', '금', '토']
            best_day_data = list(daily_efficiency)[0]
            best_day = weekdays[best_day_data['weekday']]
        
        return {
            'hourly_average': hourly_avg['overall_avg'] or 0,
            'best_day': best_day,
            'efficiency_score': self._calculate_efficiency_score(company)
        }
    
    def _calculate_efficiency_score(self, company):
        """효율성 점수 계산"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        settlements = Settlement.objects.filter(
            company=company,
            created_at__gte=thirty_days_ago
        )
        
        if not settlements.exists():
            return 0
        
        # 평균 처리 시간 대비 수익 (가상 지표)
        avg_amount = settlements.aggregate(Avg('rebate_amount'))['rebate_amount__avg'] or 0
        order_count = settlements.count()
        
        # 효율성 = 평균 수익 * 주문 수 / 1000000 (정규화)
        efficiency = (float(avg_amount) * order_count) / 1000000 * 100
        
        return min(100, round(efficiency, 1))

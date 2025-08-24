"""
수수료 데이터 분석 도구

데이터 웨어하우스의 팩트 테이블을 활용한 분석 및 리포팅 기능을 제공합니다.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import models
from django.db.models import Sum, Count, Avg, Max, Min, F, Q
from django.utils import timezone

from settlements.models import CommissionFact, CommissionGradeTracking, Settlement
from companies.models import Company
from policies.models import Policy

logger = logging.getLogger(__name__)


class CommissionAnalyzer:
    """수수료 데이터 분석 클래스"""
    
    def __init__(self):
        self.logger = logger
    
    def get_company_performance_ranking(
        self, 
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 20,
        company_type: str = None
    ) -> List[Dict]:
        """
        업체별 성과 순위 분석
        
        Args:
            start_date: 분석 시작일
            end_date: 분석 종료일
            limit: 반환할 상위 업체 수
            company_type: 업체 타입 (agency, retail 등)
            
        Returns:
            업체별 성과 순위 리스트
        """
        queryset = CommissionFact.objects.select_related('company')
        
        # 날짜 필터링
        if start_date:
            queryset = queryset.filter(date_key__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_key__lte=end_date)
        
        # 업체 타입 필터링
        if company_type:
            queryset = queryset.filter(company__type=company_type)
        
        # 업체별 집계
        ranking = queryset.values(
            'company__id',
            'company__name',
            'company__type'
        ).annotate(
            total_commission=Sum('total_commission'),
            total_base_commission=Sum('base_commission'),
            total_grade_bonus=Sum('grade_bonus'),
            total_orders=Count('order', distinct=True),
            avg_commission_per_order=Avg('total_commission'),
            max_grade_level=Max('achieved_grade_level')
        ).order_by('-total_commission')[:limit]
        
        return [
            {
                'rank': idx + 1,
                'company_id': item['company__id'],
                'company_name': item['company__name'],
                'company_type': item['company__type'],
                'total_commission': item['total_commission'] or Decimal('0'),
                'total_base_commission': item['total_base_commission'] or Decimal('0'),
                'total_grade_bonus': item['total_grade_bonus'] or Decimal('0'),
                'total_orders': item['total_orders'],
                'avg_commission_per_order': item['avg_commission_per_order'] or Decimal('0'),
                'max_grade_level': item['max_grade_level'] or 0,
                'bonus_ratio': (
                    (item['total_grade_bonus'] or Decimal('0')) / 
                    (item['total_commission'] or Decimal('1'))
                ) * 100
            }
            for idx, item in enumerate(ranking)
        ]
    
    def export_to_excel(
        self,
        analysis_data: Dict,
        file_path: str,
        sheet_name: str = 'Commission Analysis'
    ) -> bool:
        """
        분석 결과를 엑셀로 내보내기
        
        Args:
            analysis_data: 분석 데이터
            file_path: 저장할 파일 경로
            sheet_name: 시트명
            
        Returns:
            성공 여부
        """
        try:
            import pandas as pd
            
            # 데이터프레임으로 변환
            if 'ranking' in analysis_data:
                df = pd.DataFrame(analysis_data['ranking'])
            else:
                df = pd.DataFrame([analysis_data])
            
            # 엑셀 파일로 저장
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            
            logger.info(f"분석 결과 엑셀 저장 완료: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"엑셀 내보내기 실패: {str(e)}")
            return False


class GradeAnalyzer:
    """그레이드 시스템 전용 분석 클래스"""
    
    def __init__(self):
        self.logger = logger
    
    def get_grade_dashboard_data(
        self,
        company_type: str = None,
        period_type: str = 'monthly'
    ) -> Dict:
        """
        그레이드 대시보드용 데이터
        
        Args:
            company_type: 업체 타입 필터
            period_type: 기간 타입 필터
            
        Returns:
            대시보드 데이터
        """
        queryset = CommissionGradeTracking.objects.filter(is_active=True)
        
        if company_type:
            queryset = queryset.filter(company__type=company_type)
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        # 전체 통계
        total_stats = queryset.aggregate(
            total_companies=Count('company', distinct=True),
            total_target_orders=Sum('target_orders'),
            total_current_orders=Sum('current_orders'),
            total_bonus_amount=Sum('total_bonus'),
            avg_achievement_rate=Avg(
                F('current_orders') * 100.0 / F('target_orders')
            )
        )
        
        # 그레이드별 분포
        grade_distribution = queryset.values('achieved_grade_level').annotate(
            companies_count=Count('company'),
            total_bonus=Sum('total_bonus')
        ).order_by('achieved_grade_level')
        
        return {
            'overview': total_stats,
            'grade_distribution': list(grade_distribution)
        }

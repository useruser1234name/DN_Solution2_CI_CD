"""
정산 시스템 동적 필터링
Phase 5-3: 사용자별 맞춤 필터링 시스템
"""

import logging
from datetime import datetime, timedelta
from django.db.models import Q, QuerySet, Min, Max
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional, Any

from companies.models import Company, CompanyUser
from policies.models import Policy
from .models import Settlement, CommissionGradeTracking

logger = logging.getLogger(__name__)


class DynamicSettlementFilter:
    """
    동적 정산 필터링 시스템
    사용자 권한과 회사 유형에 따른 맞춤형 필터링 제공
    """
    
    def __init__(self, user, base_queryset: Optional[QuerySet] = None):
        """
        필터 초기화
        
        Args:
            user: 현재 사용자
            base_queryset: 기본 쿼리셋 (없으면 전체 Settlement)
        """
        self.user = user
        self.base_queryset = base_queryset or Settlement.objects.all()
        self.company_user = self._get_company_user()
        self.user_company = self.company_user.company if self.company_user else None
        self.user_company_type = self.user_company.type if self.user_company else None
        
    def _get_company_user(self):
        """사용자의 회사 정보 조회"""
        try:
            return CompanyUser.objects.get(django_user=self.user)
        except CompanyUser.DoesNotExist:
            return None
    
    def apply_user_permissions(self) -> QuerySet:
        """
        사용자 권한에 따른 기본 필터링 적용
        
        Returns:
            권한이 적용된 쿼리셋
        """
        if self.user.is_superuser:
            return self.base_queryset
        
        if not self.user_company:
            return Settlement.objects.none()
        
        # 회사 유형별 접근 권한 적용
        if self.user_company_type == 'headquarters':
            # 본사: 모든 정산 조회 가능
            return self.base_queryset
        
        elif self.user_company_type == 'agency':
            # 협력사: 자신과 하위 판매점의 정산만 조회
            accessible_companies = Company.objects.filter(
                Q(id=self.user_company.id) |  # 자신의 정산
                Q(parent_company=self.user_company)  # 하위 판매점 정산
            )
            return self.base_queryset.filter(company__in=accessible_companies)
        
        elif self.user_company_type == 'retail':
            # 판매점: 자신의 정산만 조회
            return self.base_queryset.filter(company=self.user_company)
        
        return Settlement.objects.none()
    
    def filter_by_period(self, start_date: str = None, end_date: str = None, 
                        period_type: str = None) -> QuerySet:
        """
        기간별 필터링
        
        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            period_type: 기간 타입 (today, week, month, quarter, year, custom)
            
        Returns:
            기간이 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        # 미리 정의된 기간 타입 처리
        if period_type:
            now = timezone.now()
            
            if period_type == 'today':
                start_date = now.date()
                end_date = now.date()
            
            elif period_type == 'week':
                start_date = (now - timedelta(days=7)).date()
                end_date = now.date()
            
            elif period_type == 'month':
                start_date = now.replace(day=1).date()
                end_date = now.date()
            
            elif period_type == 'quarter':
                quarter_start_month = ((now.month - 1) // 3) * 3 + 1
                start_date = now.replace(month=quarter_start_month, day=1).date()
                end_date = now.date()
            
            elif period_type == 'year':
                start_date = now.replace(month=1, day=1).date()
                end_date = now.date()
            
            elif period_type == 'last_30_days':
                start_date = (now - timedelta(days=30)).date()
                end_date = now.date()
            
            elif period_type == 'last_90_days':
                start_date = (now - timedelta(days=90)).date()
                end_date = now.date()
        
        # 날짜 범위 적용
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset
    
    def filter_by_company_type(self, company_types: List[str]) -> QuerySet:
        """
        회사 유형별 필터링
        
        Args:
            company_types: 회사 유형 리스트 ['headquarters', 'agency', 'retail']
            
        Returns:
            회사 유형이 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if not company_types:
            return queryset
        
        # 사용자 권한 확인
        if self.user_company_type == 'retail':
            # 판매점은 자신의 데이터만 볼 수 있음
            return queryset
        
        elif self.user_company_type == 'agency':
            # 협력사는 자신과 하위 판매점만 볼 수 있음
            allowed_types = ['agency', 'retail']
            company_types = [ct for ct in company_types if ct in allowed_types]
        
        if company_types:
            return queryset.filter(company__type__in=company_types)
        
        return queryset
    
    def filter_by_status(self, statuses: List[str]) -> QuerySet:
        """
        정산 상태별 필터링
        
        Args:
            statuses: 상태 리스트 ['pending', 'approved', 'paid', 'unpaid', 'cancelled']
            
        Returns:
            상태가 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if not statuses:
            return queryset
        
        # 유효한 상태만 필터링
        valid_statuses = [choice[0] for choice in Settlement.STATUS_CHOICES]
        filtered_statuses = [s for s in statuses if s in valid_statuses]
        
        if filtered_statuses:
            return queryset.filter(status__in=filtered_statuses)
        
        return queryset
    
    def filter_by_policy(self, policy_ids: List[str]) -> QuerySet:
        """
        정책별 필터링
        
        Args:
            policy_ids: 정책 ID 리스트
            
        Returns:
            정책이 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if not policy_ids:
            return queryset
        
        # 사용자가 접근 가능한 정책만 필터링
        accessible_policies = self._get_accessible_policies()
        filtered_policy_ids = [pid for pid in policy_ids if pid in accessible_policies]
        
        if filtered_policy_ids:
            return queryset.filter(order__policy__id__in=filtered_policy_ids)
        
        return queryset
    
    def filter_by_company(self, company_ids: List[str]) -> QuerySet:
        """
        특정 회사별 필터링
        
        Args:
            company_ids: 회사 ID 리스트
            
        Returns:
            회사가 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if not company_ids:
            return queryset
        
        # 사용자가 접근 가능한 회사만 필터링
        accessible_companies = self._get_accessible_companies()
        filtered_company_ids = [cid for cid in company_ids if cid in accessible_companies]
        
        if filtered_company_ids:
            return queryset.filter(company__id__in=filtered_company_ids)
        
        return queryset
    
    def filter_by_amount_range(self, min_amount: float = None, 
                              max_amount: float = None) -> QuerySet:
        """
        정산 금액 범위별 필터링
        
        Args:
            min_amount: 최소 금액
            max_amount: 최대 금액
            
        Returns:
            금액 범위가 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if min_amount is not None:
            queryset = queryset.filter(rebate_amount__gte=min_amount)
        
        if max_amount is not None:
            queryset = queryset.filter(rebate_amount__lte=max_amount)
        
        return queryset
    
    def filter_by_carrier(self, carriers: List[str]) -> QuerySet:
        """
        통신사별 필터링
        
        Args:
            carriers: 통신사 리스트 ['KT', 'SKT', 'LGU+']
            
        Returns:
            통신사가 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if not carriers:
            return queryset
        
        return queryset.filter(order__policy__carrier__in=carriers)
    
    def filter_by_grade_achievement(self, has_grade_bonus: bool = None) -> QuerySet:
        """
        그레이드 달성 여부별 필터링
        
        Args:
            has_grade_bonus: 그레이드 보너스 여부
            
        Returns:
            그레이드 달성이 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        if has_grade_bonus is True:
            return queryset.filter(grade_bonus__gt=0)
        elif has_grade_bonus is False:
            return queryset.filter(Q(grade_bonus=0) | Q(grade_bonus__isnull=True))
        
        return queryset
    
    def apply_multiple_filters(self, filters: Dict[str, Any]) -> QuerySet:
        """
        여러 필터를 동시에 적용
        
        Args:
            filters: 필터 딕셔너리
            {
                'period_type': 'month',
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'statuses': ['approved', 'paid'],
                'company_types': ['agency', 'retail'],
                'policy_ids': ['policy-id-1', 'policy-id-2'],
                'company_ids': ['company-id-1'],
                'min_amount': 10000,
                'max_amount': 100000,
                'carriers': ['KT', 'SKT'],
                'has_grade_bonus': True
            }
            
        Returns:
            모든 필터가 적용된 쿼리셋
        """
        queryset = self.apply_user_permissions()
        
        # 기간 필터
        if any(key in filters for key in ['period_type', 'start_date', 'end_date']):
            queryset = self.filter_by_period(
                start_date=filters.get('start_date'),
                end_date=filters.get('end_date'),
                period_type=filters.get('period_type')
            )
        
        # 회사 유형 필터
        if 'company_types' in filters and filters['company_types']:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_company_type(filters['company_types'])
        
        # 상태 필터
        if 'statuses' in filters and filters['statuses']:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_status(filters['statuses'])
        
        # 정책 필터
        if 'policy_ids' in filters and filters['policy_ids']:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_policy(filters['policy_ids'])
        
        # 회사 필터
        if 'company_ids' in filters and filters['company_ids']:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_company(filters['company_ids'])
        
        # 금액 범위 필터
        if 'min_amount' in filters or 'max_amount' in filters:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_amount_range(
                min_amount=filters.get('min_amount'),
                max_amount=filters.get('max_amount')
            )
        
        # 통신사 필터
        if 'carriers' in filters and filters['carriers']:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_carrier(filters['carriers'])
        
        # 그레이드 달성 필터
        if 'has_grade_bonus' in filters:
            temp_filter = DynamicSettlementFilter(self.user, queryset)
            queryset = temp_filter.filter_by_grade_achievement(filters['has_grade_bonus'])
        
        return queryset
    
    def get_filter_options(self) -> Dict[str, Any]:
        """
        사용자가 사용할 수 있는 필터 옵션들을 반환
        
        Returns:
            필터 옵션 딕셔너리
        """
        accessible_queryset = self.apply_user_permissions()
        
        # 사용 가능한 정책 목록
        policies = Policy.objects.filter(
            id__in=accessible_queryset.values_list('order__policy__id', flat=True).distinct()
        ).values('id', 'title', 'carrier')
        
        # 사용 가능한 회사 목록
        companies = Company.objects.filter(
            id__in=accessible_queryset.values_list('company__id', flat=True).distinct()
        ).values('id', 'name', 'type')
        
        # 사용 가능한 상태 목록
        statuses = Settlement.STATUS_CHOICES
        
        # 사용 가능한 통신사 목록
        carriers = accessible_queryset.values_list(
            'order__policy__carrier', flat=True
        ).distinct()
        
        # 금액 범위
        amount_stats = accessible_queryset.aggregate(
            min_amount=Min('rebate_amount'),
            max_amount=Max('rebate_amount')
        )
        
        return {
            'period_types': [
                {'value': 'today', 'label': '오늘'},
                {'value': 'week', 'label': '최근 7일'},
                {'value': 'month', 'label': '이번 달'},
                {'value': 'quarter', 'label': '이번 분기'},
                {'value': 'year', 'label': '올해'},
                {'value': 'last_30_days', 'label': '최근 30일'},
                {'value': 'last_90_days', 'label': '최근 90일'},
                {'value': 'custom', 'label': '사용자 지정'}
            ],
            'statuses': [{'value': status[0], 'label': status[1]} for status in statuses],
            'company_types': [
                {'value': 'headquarters', 'label': '본사'},
                {'value': 'agency', 'label': '협력사'},
                {'value': 'retail', 'label': '판매점'}
            ],
            'policies': list(policies),
            'companies': list(companies),
            'carriers': [{'value': carrier, 'label': carrier} for carrier in carriers if carrier],
            'amount_range': {
                'min': float(amount_stats['min_amount'] or 0),
                'max': float(amount_stats['max_amount'] or 0)
            },
            'user_permissions': {
                'company_type': self.user_company_type,
                'can_view_all': self.user.is_superuser or self.user_company_type == 'headquarters',
                'can_view_agencies': self.user_company_type in ['headquarters'],
                'can_view_retailers': self.user_company_type in ['headquarters', 'agency']
            }
        }
    
    def _get_accessible_policies(self) -> List[str]:
        """사용자가 접근 가능한 정책 ID 목록"""
        accessible_queryset = self.apply_user_permissions()
        return list(accessible_queryset.values_list('order__policy__id', flat=True).distinct())
    
    def _get_accessible_companies(self) -> List[str]:
        """사용자가 접근 가능한 회사 ID 목록"""
        accessible_queryset = self.apply_user_permissions()
        return list(accessible_queryset.values_list('company__id', flat=True).distinct())


class SettlementFilterSerializer:
    """필터 파라미터 직렬화 및 검증"""
    
    @staticmethod
    def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        필터 파라미터 검증 및 정제
        
        Args:
            filters: 원본 필터 딕셔너리
            
        Returns:
            검증된 필터 딕셔너리
        """
        validated = {}
        
        # 기간 검증
        if 'start_date' in filters:
            try:
                datetime.strptime(filters['start_date'], '%Y-%m-%d')
                validated['start_date'] = filters['start_date']
            except ValueError:
                logger.warning(f"잘못된 시작일 형식: {filters['start_date']}")
        
        if 'end_date' in filters:
            try:
                datetime.strptime(filters['end_date'], '%Y-%m-%d')
                validated['end_date'] = filters['end_date']
            except ValueError:
                logger.warning(f"잘못된 종료일 형식: {filters['end_date']}")
        
        # 기간 타입 검증
        valid_period_types = ['today', 'week', 'month', 'quarter', 'year', 'last_30_days', 'last_90_days', 'custom']
        if 'period_type' in filters and filters['period_type'] in valid_period_types:
            validated['period_type'] = filters['period_type']
        
        # 리스트 타입 필터들 검증
        list_filters = ['statuses', 'company_types', 'policy_ids', 'company_ids', 'carriers']
        for filter_name in list_filters:
            if filter_name in filters:
                if isinstance(filters[filter_name], list):
                    validated[filter_name] = filters[filter_name]
                elif isinstance(filters[filter_name], str):
                    validated[filter_name] = [filters[filter_name]]
        
        # 숫자 타입 필터들 검증
        number_filters = ['min_amount', 'max_amount']
        for filter_name in number_filters:
            if filter_name in filters:
                try:
                    validated[filter_name] = float(filters[filter_name])
                except (ValueError, TypeError):
                    logger.warning(f"잘못된 숫자 형식: {filter_name}={filters[filter_name]}")
        
        # 불린 타입 필터 검증
        if 'has_grade_bonus' in filters:
            if isinstance(filters['has_grade_bonus'], bool):
                validated['has_grade_bonus'] = filters['has_grade_bonus']
            elif str(filters['has_grade_bonus']).lower() in ['true', '1', 'yes']:
                validated['has_grade_bonus'] = True
            elif str(filters['has_grade_bonus']).lower() in ['false', '0', 'no']:
                validated['has_grade_bonus'] = False
        
        return validated

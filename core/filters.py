"""
커스텀 필터 클래스

이 모듈은 API 엔드포인트에서 사용할 수 있는 커스텀 필터를 제공합니다.
성능 최적화와 유연한 검색 기능을 위해 설계되었습니다.
"""

from django_filters import rest_framework as filters
from django.db.models import Q
from companies.models import Company, CompanyUser
from policies.models import Policy
from orders.models import Order
from settlements.models import Settlement


class CompanyFilter(filters.FilterSet):
    """
    회사 필터
    
    - 회사명, 타입, 상태 기반 필터링
    - 부모 회사 기반 필터링
    """
    name = filters.CharFilter(lookup_expr='icontains')
    code = filters.CharFilter(lookup_expr='exact')
    type = filters.ChoiceFilter(choices=Company.COMPANY_TYPES)
    status = filters.BooleanFilter()
    parent_company = filters.ModelChoiceFilter(queryset=Company.objects.all())
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Company
        fields = ['name', 'code', 'type', 'status', 'parent_company']


class CompanyUserFilter(filters.FilterSet):
    """
    회사 사용자 필터
    
    - 사용자명, 역할, 상태 기반 필터링
    - 회사 기반 필터링
    """
    username = filters.CharFilter(lookup_expr='icontains')
    company = filters.ModelChoiceFilter(queryset=Company.objects.all())
    role = filters.ChoiceFilter(choices=CompanyUser.ROLES)
    status = filters.ChoiceFilter(choices=CompanyUser.STATUS_CHOICES)
    is_approved = filters.BooleanFilter()
    
    class Meta:
        model = CompanyUser
        fields = ['username', 'company', 'role', 'status', 'is_approved']


class PolicyFilter(filters.FilterSet):
    """
    정책 필터
    
    - 정책명, 타입, 상태 기반 필터링
    - 날짜 범위 기반 필터링
    """
    name = filters.CharFilter(lookup_expr='icontains')
    type = filters.ChoiceFilter(choices=Policy.TYPE_CHOICES)
    status = filters.ChoiceFilter(choices=Policy.STATUS_CHOICES)
    carrier = filters.ChoiceFilter(choices=Policy.CARRIER_CHOICES)
    start_date_after = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    class Meta:
        model = Policy
        fields = ['name', 'type', 'status', 'carrier']


class OrderFilter(filters.FilterSet):
    """
    주문 필터
    
    - 고객명, 상태, 회사 기반 필터링
    - 날짜 범위 기반 필터링
    - 가격 범위 기반 필터링
    """
    customer_name = filters.CharFilter(lookup_expr='icontains')
    customer_phone = filters.CharFilter(lookup_expr='icontains')
    status = filters.ChoiceFilter(choices=Order.STATUS_CHOICES)
    company = filters.ModelChoiceFilter(queryset=Company.objects.all())
    policy = filters.ModelChoiceFilter(queryset=Policy.objects.all())
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    min_price = filters.NumberFilter(field_name='monthly_fee', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='monthly_fee', lookup_expr='lte')
    
    # 커스텀 필터 메소드
    search = filters.CharFilter(method='search_filter')
    
    def search_filter(self, queryset, name, value):
        """통합 검색 필터"""
        return queryset.filter(
            Q(customer_name__icontains=value) |
            Q(customer_phone__icontains=value) |
            Q(order_number__icontains=value)
        )
    
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'status', 'company', 'policy']


class SettlementFilter(filters.FilterSet):
    """
    정산 필터
    
    - 회사, 상태 기반 필터링
    - 날짜 범위 기반 필터링
    - 금액 범위 기반 필터링
    """
    company = filters.ModelChoiceFilter(queryset=Company.objects.all())
    status = filters.ChoiceFilter(choices=Settlement.STATUS_CHOICES)
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    min_amount = filters.NumberFilter(field_name='rebate_amount', lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name='rebate_amount', lookup_expr='lte')
    
    class Meta:
        model = Settlement
        fields = ['company', 'status']
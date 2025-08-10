"""
최적화된 ViewSet - N+1 쿼리 문제 해결
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Count, Q, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from companies.models import Company, CompanyUser
from companies.serializers import CompanySerializer, CompanyUserSerializer
from dn_solution.cache_manager import cached_api_response
import logging

logger = logging.getLogger(__name__)


class OptimizedCompanyViewSet(viewsets.ModelViewSet):
    """
    최적화된 업체 ViewSet
    - N+1 쿼리 문제 해결
    - 효율적인 쿼리 사용
    """
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """최적화된 쿼리셋"""
        queryset = Company.objects.select_related(
            'parent_company'
        ).prefetch_related(
            # 하위 업체들 미리 로드
            Prefetch(
                'company_set',
                queryset=Company.objects.select_related('parent_company'),
                to_attr='prefetched_children'
            ),
            # 정책 배정 미리 로드
            'policy_assignments__policy',
            # 사용자 미리 로드
            'companyuser_set__django_user',
        ).annotate(
            # 집계 데이터 추가
            child_count=Count('company'),
            user_count=Count('companyuser'),
            active_policies_count=Count(
                'policy_assignments',
                filter=Q(policy_assignments__policy__expose=True)
            ),
        ).filter(status=True)  # 활성 업체만
        
        # 필터링
        company_type = self.request.query_params.get('type', None)
        if company_type:
            queryset = queryset.filter(type=company_type)
        
        # 검색
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        
        # 정렬
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    @method_decorator(cache_page(60 * 5))  # 5분 캐싱
    def list(self, request, *args, **kwargs):
        """업체 목록 조회 (캐싱 적용)"""
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """업체 계층 구조 조회"""
        company = self.get_object()
        
        # 재귀적으로 하위 업체 조회 (최적화)
        def get_hierarchy(comp):
            children = []
            if hasattr(comp, 'prefetched_children'):
                for child in comp.prefetched_children:
                    children.append({
                        'id': str(child.id),
                        'code': child.code,
                        'name': child.name,
                        'type': child.type,
                        'children': get_hierarchy(child)
                    })
            return children
        
        hierarchy_data = {
            'id': str(company.id),
            'code': company.code,
            'name': company.name,
            'type': company.type,
            'children': get_hierarchy(company)
        }
        
        return Response(hierarchy_data)
    
    @action(detail=True, methods=['get'])
    @cached_api_response(timeout=300)  # 5분 캐싱
    def statistics(self, request, pk=None):
        """업체 통계 정보"""
        company = self.get_object()
        
        # 집계 쿼리 (단일 쿼리로 처리)
        stats = Company.objects.filter(id=company.id).aggregate(
            total_children=Count('company'),
            total_users=Count('companyuser'),
            active_users=Count('companyuser', filter=Q(companyuser__is_approved=True)),
            total_orders=Count('order'),
            completed_orders=Count('order', filter=Q(order__status='completed')),
            total_revenue=Sum('order__total_amount'),
        )
        
        return Response(stats)


class OptimizedCompanyUserViewSet(viewsets.ModelViewSet):
    """
    최적화된 업체 사용자 ViewSet
    """
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """최적화된 쿼리셋"""
        queryset = CompanyUser.objects.select_related(
            'company',
            'company__parent_company',
            'django_user',
        ).prefetch_related(
            'django_user__groups',
            'django_user__user_permissions',
        ).annotate(
            order_count=Count('company__order'),
        )
        
        # 회사별 필터링
        company_id = self.request.query_params.get('company', None)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        # 상태별 필터링
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """승인 대기 중인 사용자 목록"""
        queryset = self.get_queryset().filter(
            status='pending',
            is_approved=False
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """사용자 승인"""
        user = self.get_object()
        
        try:
            # 승인 권한 체크
            approver = request.user.companyuser
            user.approve(approver)
            
            return Response(
                {'message': '사용자가 승인되었습니다.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

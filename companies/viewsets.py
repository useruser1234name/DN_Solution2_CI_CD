"""
Company ViewSets

DRF ViewSet들을 별도 파일로 분리하여 코드 구조를 개선합니다.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from .models import Company, CompanyUser
from .serializers import CompanySerializer, CompanyUserSerializer
from .services import CompanyService, CompanyUserService
from .utils import get_visible_companies, get_visible_users
from .cache_utils import CompanyCacheManager, CompanyUserCacheManager, StatsCacheManager
from .pagination import CompanyPagination, CompanyUserPagination, PerformanceOptimizedMixin
from core.filters import CompanyFilter, CompanyUserFilter

logger = logging.getLogger('companies')


class CompanyViewSet(PerformanceOptimizedMixin, viewsets.ModelViewSet):
    """
    업체 관리 ViewSet (성능 최적화됨)
    
    업체의 CRUD 작업을 처리합니다.
    계층별 권한 필터링과 캐싱이 적용됩니다.
    """
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]
    filterset_class = CompanyFilter
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at', 'type']
    ordering = ['-created_at']
    pagination_class = CompanyPagination
    
    # 성능 최적화를 위한 필드 정의
    select_related_fields = ['parent_company']
    prefetch_related_fields = ['companyuser_set']  # child_companies 대신 실제 존재하는 관계 사용

    def get_queryset(self):
        """계층별 권한 필터링이 적용된 회사 목록 반환"""
        # 캐시된 결과 사용
        if hasattr(self.request, 'user'):
            filters = self.request.query_params.dict()
            companies = CompanyCacheManager.get_company_list(self.request.user, filters)
            
            # QuerySet으로 변환 (필터링과 정렬을 위해)
            company_ids = [str(c.id) for c in companies]
            queryset = Company.objects.filter(id__in=company_ids)
        else:
            queryset = get_visible_companies(self.request.user)
        
        # N+1 쿼리 방지를 위한 select_related/prefetch_related 추가
        return queryset.select_related('parent_company').prefetch_related(
            'company_set',  # 하위 업체들 (parent_company FK의 역관계)
            'companyuser_set'  # 소속 사용자들
        )
    
    def retrieve(self, request, *args, **kwargs):
        """단일 업체 조회 (캐시 적용)"""
        company_id = kwargs.get('pk')
        company = CompanyCacheManager.get_company(company_id)
        
        if not company:
            return Response({'error': '업체를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        # 권한 확인
        accessible_ids = CompanyCacheManager.get_accessible_company_ids(request.user)
        if company_id not in accessible_ids:
            return Response({'error': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(company)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    @method_decorator(cache_page(300))  # 5분 캐시
    def child_companies(self, request, pk=None):
        """특정 업체의 하위 업체 목록 (캐시됨)"""
        try:
            # 캐시된 계층 구조 사용
            hierarchy = CompanyCacheManager.get_company_hierarchy(pk)
            if not hierarchy:
                return Response(
                    {'success': False, 'message': '업체를 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({'success': True, 'data': hierarchy['children']})
        except Exception as e:
            logger.error(f'하위 업체 목록 조회 실패: {str(e)}')
            return Response(
                {'success': False, 'message': '하위 업체 목록 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """업체 통계 정보 (캐시됨)"""
        try:
            # 캐시된 통계 사용
            stats = StatsCacheManager.get_company_stats(request.user)
            return Response(stats)
        except Exception as e:
            logger.error(f'업체 통계 조회 실패: {str(e)}')
            return Response(
                {'error': '통계 정보 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """업체 계층 구조 조회 (새로운 액션)"""
        try:
            hierarchy = CompanyCacheManager.get_company_hierarchy(pk)
            if not hierarchy:
                return Response(
                    {'error': '업체를 찾을 수 없습니다.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(hierarchy)
        except Exception as e:
            logger.error(f'업체 계층 구조 조회 실패: {str(e)}')
            return Response(
                {'error': '계층 구조 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompanyUserViewSet(PerformanceOptimizedMixin, viewsets.ModelViewSet):
    """
    업체 사용자 관리 ViewSet (성능 최적화됨)
    
    업체 사용자의 CRUD 작업을 처리합니다.
    계층별 권한 필터링과 캐싱이 적용됩니다.
    """
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = CompanyUserFilter
    search_fields = ['username', 'django_user__email']
    ordering_fields = ['username', 'created_at', 'role']
    ordering = ['-created_at']
    pagination_class = CompanyUserPagination
    
    # 성능 최적화를 위한 필드 정의
    select_related_fields = ['company', 'company__parent_company', 'django_user']

    def get_queryset(self):
        """계층별 권한 필터링이 적용된 사용자 목록 반환"""
        # 캐시된 결과 사용
        filters = self.request.query_params.dict()
        users = CompanyUserCacheManager.get_user_list(self.request.user, filters)
        
        # QuerySet으로 변환
        user_ids = [str(u.id) for u in users]
        queryset = CompanyUser.objects.filter(id__in=user_ids)
        
        # N+1 쿼리 방지
        return queryset.select_related(
            'company',
            'company__parent_company',
            'django_user'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """단일 사용자 조회 (캐시 적용)"""
        user_id = kwargs.get('pk')
        company_user = CompanyUserCacheManager.get_user(user_id)
        
        if not company_user:
            return Response({'error': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(company_user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """사용자 승인"""
        try:
            result = CompanyUserService.approve_user(
                user_id=pk,
                approver=request.user,
                action='approve'
            )
            # target_user 객체는 직렬화할 수 없으므로 제거
            if 'target_user' in result:
                user = result.pop('target_user')
                # 필요한 정보만 추가
                result['user_id'] = str(user.id)
                result['username'] = user.username
                result['status'] = user.status
            
            return Response(result)
        except Exception as e:
            logger.error(f'사용자 승인 실패: {str(e)}')
            return Response(
                {'success': False, 'message': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """사용자 거절"""
        try:
            result = CompanyUserService.approve_user(
                user_id=pk,
                approver=request.user,
                action='reject'
            )
            # target_user 객체는 직렬화할 수 없으므로 제거
            if 'target_user' in result:
                user = result.pop('target_user')
                # 필요한 정보만 추가
                result['user_id'] = str(user.id)
                result['username'] = user.username
                result['status'] = user.status
            
            return Response(result)
        except Exception as e:
            logger.error(f'사용자 거절 실패: {str(e)}')
            return Response(
                {'success': False, 'message': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(180))  # 3분 캐시
    def pending_approvals(self, request):
        """승인 대기 중인 사용자 목록 (캐시됨)"""
        try:
            # 캐시된 승인 대기 사용자 목록 사용
            pending_users = CompanyUserCacheManager.get_pending_users(request.user)
            serializer = self.get_serializer(pending_users, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'승인 대기 목록 조회 실패: {str(e)}')
            return Response(
                {'error': '승인 대기 목록 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(300))  # 5분 캐시
    def activities(self, request):
        """사용자 활동 내역 (캐시됨)"""
        try:
            hours = int(request.query_params.get('hours', 24))
            activities = CompanyUserService.get_user_activities(request.user, hours)
            return Response(activities)
        except Exception as e:
            logger.error(f'활동 내역 조회 실패: {str(e)}')
            return Response(
                {'error': '활동 내역 조회에 실패했습니다.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

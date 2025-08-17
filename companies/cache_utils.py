"""
Company 앱 캐싱 유틸리티

성능 최적화를 위한 캐싱 전략과 관련 유틸리티를 제공합니다.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import timedelta
from django.core.cache import cache
from django.db.models import QuerySet, Count
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Company, CompanyUser


class CacheKeyManager:
    """캐시 키 관리 클래스"""
    
    # 캐시 키 접두사
    COMPANY_PREFIX = "company"
    USER_PREFIX = "company_user"
    STATS_PREFIX = "stats"
    HIERARCHY_PREFIX = "hierarchy"
    
    # 캐시 만료 시간 (초)
    DEFAULT_TIMEOUT = 3600  # 1시간
    STATS_TIMEOUT = 1800    # 30분
    HIERARCHY_TIMEOUT = 7200  # 2시간
    
    @classmethod
    def get_company_key(cls, company_id: str) -> str:
        """단일 업체 캐시 키"""
        return f"{cls.COMPANY_PREFIX}:detail:{company_id}"
    
    @classmethod
    def get_company_list_key(cls, user_id: str, filters: Dict[str, Any] = None) -> str:
        """업체 목록 캐시 키"""
        key_data = f"{user_id}"
        if filters:
            # 필터를 정렬하여 일관된 키 생성
            sorted_filters = json.dumps(filters, sort_keys=True)
            key_hash = hashlib.md5(sorted_filters.encode()).hexdigest()
            key_data += f":{key_hash}"
        return f"{cls.COMPANY_PREFIX}:list:{key_data}"
    
    @classmethod
    def get_user_key(cls, user_id: str) -> str:
        """단일 사용자 캐시 키"""
        return f"{cls.USER_PREFIX}:detail:{user_id}"
    
    @classmethod
    def get_user_list_key(cls, user_id: str, filters: Dict[str, Any] = None) -> str:
        """사용자 목록 캐시 키"""
        key_data = f"{user_id}"
        if filters:
            sorted_filters = json.dumps(filters, sort_keys=True)
            key_hash = hashlib.md5(sorted_filters.encode()).hexdigest()
            key_data += f":{key_hash}"
        return f"{cls.USER_PREFIX}:list:{key_data}"
    
    @classmethod
    def get_stats_key(cls, user_id: str) -> str:
        """통계 캐시 키"""
        return f"{cls.STATS_PREFIX}:user:{user_id}"
    
    @classmethod
    def get_hierarchy_key(cls, company_id: str) -> str:
        """계층 구조 캐시 키"""
        return f"{cls.HIERARCHY_PREFIX}:company:{company_id}"
    
    @classmethod
    def get_accessible_companies_key(cls, user_id: str) -> str:
        """접근 가능한 업체 목록 캐시 키"""
        return f"{cls.HIERARCHY_PREFIX}:accessible:{user_id}"


class CompanyCacheManager:
    """업체 관련 캐싱 관리 클래스"""
    
    @staticmethod
    def get_company(company_id: str) -> Optional[Company]:
        """캐시된 업체 정보 조회"""
        cache_key = CacheKeyManager.get_company_key(company_id)
        company = cache.get(cache_key)
        
        if company is None:
            try:
                company = Company.objects.select_related('parent_company').get(id=company_id)
                cache.set(cache_key, company, CacheKeyManager.DEFAULT_TIMEOUT)
            except Company.DoesNotExist:
                return None
        
        return company
    
    @staticmethod
    def get_company_list(user: User, filters: Dict[str, Any] = None) -> List[Company]:
        """캐시된 업체 목록 조회"""
        cache_key = CacheKeyManager.get_company_list_key(str(user.id), filters)
        companies = cache.get(cache_key)
        
        if companies is None:
            from .utils import get_visible_companies
            queryset = get_visible_companies(user)
            
            # 필터 적용
            if filters:
                if 'type' in filters:
                    queryset = queryset.filter(type=filters['type'])
                if 'status' in filters:
                    queryset = queryset.filter(status=filters['status'])
                if 'search' in filters:
                    search_term = filters['search']
                    queryset = queryset.filter(
                        models.Q(name__icontains=search_term) |
                        models.Q(code__icontains=search_term)
                    )
            
            # 최적화된 쿼리 - child_companies는 property이므로 prefetch_related 사용 불가
            companies = list(queryset.select_related('parent_company').prefetch_related(
                'company_set',  # 하위 업체들 (parent_company FK의 역관계)
                'companyuser_set'  # 소속 사용자들
            ))
            
            cache.set(cache_key, companies, CacheKeyManager.DEFAULT_TIMEOUT)
        
        return companies
    
    @staticmethod
    def get_accessible_company_ids(user: User) -> List[str]:
        """캐시된 접근 가능 업체 ID 목록"""
        cache_key = CacheKeyManager.get_accessible_companies_key(str(user.id))
        company_ids = cache.get(cache_key)
        
        if company_ids is None:
            from .utils import get_accessible_company_ids
            company_ids = list(get_accessible_company_ids(user))
            cache.set(cache_key, company_ids, CacheKeyManager.HIERARCHY_TIMEOUT)
        
        return company_ids
    
    @staticmethod
    def get_company_hierarchy(company_id: str) -> Dict[str, Any]:
        """캐시된 업체 계층 구조"""
        cache_key = CacheKeyManager.get_hierarchy_key(company_id)
        hierarchy = cache.get(cache_key)
        
        if hierarchy is None:
            try:
                company = Company.objects.select_related('parent_company').get(id=company_id)
                
                # 상위 업체들
                ancestors = []
                current = company.parent_company
                while current:
                    ancestors.append({
                        'id': str(current.id),
                        'name': current.name,
                        'type': current.type,
                        'code': current.code
                    })
                    current = current.parent_company
                
                # 하위 업체들 - property 대신 직접 쿼리 사용
                children = list(Company.objects.filter(parent_company=company).values(
                    'id', 'name', 'type', 'code', 'status'
                ))
                
                hierarchy = {
                    'company': {
                        'id': str(company.id),
                        'name': company.name,
                        'type': company.type,
                        'code': company.code
                    },
                    'ancestors': ancestors,
                    'children': children
                }
                
                cache.set(cache_key, hierarchy, CacheKeyManager.HIERARCHY_TIMEOUT)
                
            except Company.DoesNotExist:
                return None
        
        return hierarchy
    
    @staticmethod
    def invalidate_company_cache(company_id: str):
        """업체 관련 캐시 무효화"""
        # 단일 업체 캐시 삭제
        cache.delete(CacheKeyManager.get_company_key(company_id))
        
        # 계층 구조 캐시 삭제
        cache.delete(CacheKeyManager.get_hierarchy_key(company_id))
        
        # 목록 캐시는 패턴 삭제가 어려우므로 버전 기반 접근
        # 실제 운영에서는 Redis의 SCAN 명령어 등을 사용할 수 있음
        CompanyCacheManager._invalidate_list_caches(CacheKeyManager.COMPANY_PREFIX)
    
    @staticmethod
    def _invalidate_list_caches(prefix: str):
        """목록 캐시 패턴 삭제 (단순 구현)"""
        # 실제 운영에서는 더 효율적인 방법 필요
        # Redis의 경우 SCAN + DELETE 패턴 사용
        pass


class CompanyUserCacheManager:
    """업체 사용자 관련 캐싱 관리 클래스"""
    
    @staticmethod
    def get_user(user_id: str) -> Optional[CompanyUser]:
        """캐시된 사용자 정보 조회"""
        cache_key = CacheKeyManager.get_user_key(user_id)
        company_user = cache.get(cache_key)
        
        if company_user is None:
            try:
                company_user = CompanyUser.objects.select_related(
                    'company', 'django_user'
                ).get(id=user_id)
                cache.set(cache_key, company_user, CacheKeyManager.DEFAULT_TIMEOUT)
            except CompanyUser.DoesNotExist:
                return None
        
        return company_user
    
    @staticmethod
    def get_user_list(user: User, filters: Dict[str, Any] = None) -> List[CompanyUser]:
        """캐시된 사용자 목록 조회"""
        cache_key = CacheKeyManager.get_user_list_key(str(user.id), filters)
        users = cache.get(cache_key)
        
        if users is None:
            from .utils import get_visible_users
            queryset = get_visible_users(user)
            
            # 필터 적용
            if filters:
                if 'role' in filters:
                    queryset = queryset.filter(role=filters['role'])
                if 'status' in filters:
                    queryset = queryset.filter(status=filters['status'])
                if 'company_id' in filters:
                    queryset = queryset.filter(company_id=filters['company_id'])
            
            # 최적화된 쿼리
            users = list(queryset.select_related(
                'company', 'company__parent_company', 'django_user'
            ))
            
            cache.set(cache_key, users, CacheKeyManager.DEFAULT_TIMEOUT)
        
        return users
    
    @staticmethod
    def get_pending_users(user: User) -> List[CompanyUser]:
        """캐시된 승인 대기 사용자 목록"""
        filters = {'status': 'pending'}
        return CompanyUserCacheManager.get_user_list(user, filters)
    
    @staticmethod
    def invalidate_user_cache(user_id: str):
        """사용자 관련 캐시 무효화"""
        cache.delete(CacheKeyManager.get_user_key(user_id))
        CompanyUserCacheManager._invalidate_list_caches(CacheKeyManager.USER_PREFIX)
    
    @staticmethod
    def _invalidate_list_caches(prefix: str):
        """목록 캐시 패턴 삭제"""
        pass


class StatsCacheManager:
    """통계 정보 캐싱 관리 클래스"""
    
    @staticmethod
    def get_company_stats(user: User) -> Dict[str, Any]:
        """캐시된 업체 통계"""
        cache_key = CacheKeyManager.get_stats_key(str(user.id))
        stats = cache.get(cache_key)
        
        if stats is None:
            # 실시간 통계 계산
            accessible_company_ids = CompanyCacheManager.get_accessible_company_ids(user)
            
            total_companies = len(accessible_company_ids)
            active_companies = Company.objects.filter(
                id__in=accessible_company_ids, 
                status=True
            ).count()
            
            # 타입별 통계
            company_counts = Company.objects.filter(
                id__in=accessible_company_ids
            ).values('type').annotate(count=Count('id'))
            
            by_type = {item['type']: item['count'] for item in company_counts}
            
            # 승인 대기 사용자 수
            pending_users = CompanyUser.objects.filter(
                company_id__in=accessible_company_ids,
                status='pending'
            ).count()
            
            stats = {
                'total_companies': total_companies,
                'active_companies': active_companies,
                'pending_approvals': pending_users,
                'by_type': by_type,
                'last_updated': timezone.now().isoformat()
            }
            
            cache.set(cache_key, stats, CacheKeyManager.STATS_TIMEOUT)
        
        return stats
    
    @staticmethod
    def invalidate_stats_cache(user_id: str = None):
        """통계 캐시 무효화"""
        if user_id:
            cache.delete(CacheKeyManager.get_stats_key(user_id))
        else:
            # 모든 통계 캐시 무효화
            pass


class CacheDecorator:
    """캐싱 데코레이터 클래스"""
    
    @staticmethod
    def cache_result(timeout: int = CacheKeyManager.DEFAULT_TIMEOUT, 
                    key_func: Optional[Callable] = None):
        """함수 결과 캐싱 데코레이터"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # 기본 키 생성 (함수명 + 인자 해시)
                    key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()
                
                # 캐시에서 조회
                result = cache.get(cache_key)
                if result is None:
                    result = func(*args, **kwargs)
                    cache.set(cache_key, result, timeout)
                
                return result
            return wrapper
        return decorator


# 캐시 무효화 신호 처리
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Company)
def invalidate_company_cache_on_save(sender, instance, **kwargs):
    """업체 저장 시 캐시 무효화"""
    CompanyCacheManager.invalidate_company_cache(str(instance.id))
    
    # 부모 업체의 계층 구조도 무효화
    if instance.parent_company:
        CompanyCacheManager.invalidate_company_cache(str(instance.parent_company.id))

@receiver(post_delete, sender=Company)
def invalidate_company_cache_on_delete(sender, instance, **kwargs):
    """업체 삭제 시 캐시 무효화"""
    CompanyCacheManager.invalidate_company_cache(str(instance.id))

@receiver(post_save, sender=CompanyUser)
def invalidate_user_cache_on_save(sender, instance, **kwargs):
    """사용자 저장 시 캐시 무효화"""
    CompanyUserCacheManager.invalidate_user_cache(str(instance.id))
    
    # 통계 캐시도 무효화
    StatsCacheManager.invalidate_stats_cache()

@receiver(post_delete, sender=CompanyUser)
def invalidate_user_cache_on_delete(sender, instance, **kwargs):
    """사용자 삭제 시 캐시 무효화"""
    CompanyUserCacheManager.invalidate_user_cache(str(instance.id))
    StatsCacheManager.invalidate_stats_cache()

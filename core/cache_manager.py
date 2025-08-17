"""
캐시 전략 매니저
효율적인 캐시 관리를 위한 전략 패턴 구현
"""

import logging
from typing import Any, Optional, List, Callable
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheStrategy:
    """캐시 전략 기본 클래스"""
    
    # 캐시 태그 정의
    CACHE_TAGS = {
        'company': ['company_list', 'company_detail', 'company_hierarchy'],
        'policy': ['policy_list', 'policy_detail', 'policy_assignment'],
        'order': ['order_list', 'order_detail', 'order_stats'],
        'user': ['user_permissions', 'user_profile', 'user_company'],
        'dashboard': ['dashboard_stats', 'dashboard_activities'],
        'settlement': ['settlement_list', 'settlement_detail', 'settlement_stats']
    }
    
    # 기본 TTL (초 단위)
    DEFAULT_TTLS = {
        'company': 3600,      # 1시간
        'policy': 1800,       # 30분
        'order': 300,         # 5분
        'user': 3600,         # 1시간
        'dashboard': 60,      # 1분
        'settlement': 600     # 10분
    }
    
    @classmethod
    def get_cache_key(cls, tag: str, identifier: Any = None) -> str:
        """
        캐시 키 생성
        
        Args:
            tag: 캐시 태그
            identifier: 추가 식별자
            
        Returns:
            캐시 키
        """
        if identifier:
            return f"{tag}:{identifier}"
        return tag
    
    @classmethod
    def get_or_set(cls, key: str, func: Callable, timeout: int = None) -> Any:
        """
        캐시에서 가져오거나 설정
        
        Args:
            key: 캐시 키
            func: 캐시 미스 시 실행할 함수
            timeout: 캐시 타임아웃
            
        Returns:
            캐시된 값 또는 함수 실행 결과
        """
        cached_value = cache.get(key)
        if cached_value is not None:
            logger.debug(f"캐시 히트: {key}")
            return cached_value
            
        logger.debug(f"캐시 미스: {key}")
        value = func()
        
        if value is not None:
            cache.set(key, value, timeout or cls._get_default_timeout(key))
            
        return value
    
    @classmethod
    def invalidate_tag(cls, tag_type: str) -> None:
        """
        특정 태그의 모든 캐시 무효화
        
        Args:
            tag_type: 태그 타입 (company, policy, order 등)
        """
        tags = cls.CACHE_TAGS.get(tag_type, [])
        for tag in tags:
            pattern = f"{tag}:*"
            cls._delete_pattern(pattern)
            logger.info(f"캐시 태그 무효화: {tag}")
    
    @classmethod
    def invalidate_key(cls, key: str) -> None:
        """특정 캐시 키 무효화"""
        cache.delete(key)
        logger.debug(f"캐시 키 무효화: {key}")
    
    @classmethod
    def invalidate_pattern(cls, pattern: str) -> None:
        """패턴과 일치하는 모든 캐시 무효화"""
        cls._delete_pattern(pattern)
        logger.info(f"캐시 패턴 무효화: {pattern}")
    
    @classmethod
    def _get_default_timeout(cls, key: str) -> int:
        """키에 따른 기본 타임아웃 반환"""
        for tag_type, ttl in cls.DEFAULT_TTLS.items():
            if tag_type in key:
                return ttl
        return 300  # 기본값 5분
    
    @classmethod
    def _delete_pattern(cls, pattern: str) -> None:
        """
        패턴과 일치하는 캐시 키 삭제
        Redis 백엔드 필요
        """
        try:
            if hasattr(cache, '_cache'):
                # Django-redis 사용 시
                cache.delete_pattern(pattern)
            else:
                # 기본 캐시 백엔드는 패턴 삭제 미지원
                logger.warning(f"패턴 삭제 미지원: {pattern}")
        except Exception as e:
            logger.error(f"패턴 삭제 실패: {e}")


def cache_result(tag: str, timeout: int = None):
    """
    함수 결과를 캐시하는 데코레이터
    
    Args:
        tag: 캐시 태그
        timeout: 캐시 타임아웃
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = CacheStrategy.get_cache_key(
                tag,
                f"{func.__name__}:{str(args)}:{str(kwargs)}"
            )
            
            # 캐시에서 가져오거나 설정
            return CacheStrategy.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                timeout
            )
        return wrapper
    return decorator


class CompanyCacheStrategy(CacheStrategy):
    """회사 관련 캐시 전략"""
    
    @classmethod
    def get_company_hierarchy_key(cls, company_id: int) -> str:
        """회사 계층 구조 캐시 키"""
        return cls.get_cache_key('company_hierarchy', company_id)
    
    @classmethod
    def get_company_list_key(cls, company_type: str = None) -> str:
        """회사 목록 캐시 키"""
        if company_type:
            return cls.get_cache_key('company_list', company_type)
        return cls.get_cache_key('company_list', 'all')
    
    @classmethod
    def invalidate_company_cache(cls, company_id: int = None) -> None:
        """회사 캐시 무효화"""
        if company_id:
            # 특정 회사 캐시 무효화
            cls.invalidate_key(cls.get_cache_key('company_detail', company_id))
            cls.invalidate_key(cls.get_company_hierarchy_key(company_id))
        
        # 전체 회사 관련 캐시 무효화
        cls.invalidate_tag('company')


class PolicyCacheStrategy(CacheStrategy):
    """정책 관련 캐시 전략"""
    
    @classmethod
    def get_policy_assignment_key(cls, company_id: int) -> str:
        """정책 배정 캐시 키"""
        return cls.get_cache_key('policy_assignment', f"company_{company_id}")
    
    @classmethod
    def get_policy_list_key(cls, is_active: bool = None) -> str:
        """정책 목록 캐시 키"""
        if is_active is not None:
            return cls.get_cache_key('policy_list', f"active_{is_active}")
        return cls.get_cache_key('policy_list', 'all')
    
    @classmethod
    def invalidate_policy_cache(cls, policy_id: int = None, company_id: int = None) -> None:
        """정책 캐시 무효화"""
        if policy_id:
            cls.invalidate_key(cls.get_cache_key('policy_detail', policy_id))
        
        if company_id:
            cls.invalidate_key(cls.get_policy_assignment_key(company_id))
        
        # 전체 정책 관련 캐시 무효화
        cls.invalidate_tag('policy')


class OrderCacheStrategy(CacheStrategy):
    """주문 관련 캐시 전략"""
    
    @classmethod
    def get_order_stats_key(cls, company_id: int, period: str = 'daily') -> str:
        """주문 통계 캐시 키"""
        return cls.get_cache_key('order_stats', f"{company_id}_{period}")
    
    @classmethod
    def get_order_list_key(cls, company_id: int, status: str = None) -> str:
        """주문 목록 캐시 키"""
        if status:
            return cls.get_cache_key('order_list', f"{company_id}_{status}")
        return cls.get_cache_key('order_list', company_id)
    
    @classmethod
    def invalidate_order_cache(cls, order_id: int = None, company_id: int = None) -> None:
        """주문 캐시 무효화"""
        if order_id:
            cls.invalidate_key(cls.get_cache_key('order_detail', order_id))
        
        if company_id:
            # 회사별 주문 관련 캐시 무효화
            cls.invalidate_pattern(f"order_*:{company_id}_*")
        
        # 전체 주문 관련 캐시 무효화
        cls.invalidate_tag('order')


class UserCacheStrategy(CacheStrategy):
    """사용자 관련 캐시 전략"""
    
    @classmethod
    def get_user_permissions_key(cls, user_id: int) -> str:
        """사용자 권한 캐시 키"""
        return cls.get_cache_key('user_permissions', user_id)
    
    @classmethod
    def get_user_company_key(cls, user_id: int) -> str:
        """사용자 회사 정보 캐시 키"""
        return cls.get_cache_key('user_company', user_id)
    
    @classmethod
    def invalidate_user_cache(cls, user_id: int) -> None:
        """사용자 캐시 무효화"""
        cls.invalidate_key(cls.get_user_permissions_key(user_id))
        cls.invalidate_key(cls.get_user_company_key(user_id))
        cls.invalidate_key(cls.get_cache_key('user_profile', user_id))


class DashboardCacheStrategy(CacheStrategy):
    """대시보드 관련 캐시 전략"""
    
    @classmethod
    def get_dashboard_stats_key(cls, company_id: int) -> str:
        """대시보드 통계 캐시 키"""
        return cls.get_cache_key('dashboard_stats', company_id)
    
    @classmethod
    def get_dashboard_activities_key(cls, company_id: int) -> str:
        """대시보드 활동 캐시 키"""
        return cls.get_cache_key('dashboard_activities', company_id)
    
    @classmethod
    def invalidate_dashboard_cache(cls, company_id: int = None) -> None:
        """대시보드 캐시 무효화"""
        if company_id:
            cls.invalidate_key(cls.get_dashboard_stats_key(company_id))
            cls.invalidate_key(cls.get_dashboard_activities_key(company_id))
        else:
            cls.invalidate_tag('dashboard')


# 캐시 워밍업 함수
def warm_up_cache():
    """자주 사용되는 데이터를 미리 캐시에 로드"""
    logger.info("캐시 워밍업 시작")
    
    try:
        # 활성 회사 목록 캐싱
        from companies.models import Company
        active_companies = Company.objects.filter(is_active=True).values_list('id', 'name')
        cache.set(
            CompanyCacheStrategy.get_company_list_key('active'),
            list(active_companies),
            CompanyCacheStrategy.DEFAULT_TTLS['company']
        )
        
        # 활성 정책 목록 캐싱
        from policies.models import Policy
        active_policies = Policy.objects.filter(is_active=True).values_list('id', 'name')
        cache.set(
            PolicyCacheStrategy.get_policy_list_key(True),
            list(active_policies),
            PolicyCacheStrategy.DEFAULT_TTLS['policy']
        )
        
        logger.info("캐시 워밍업 완료")
        
    except Exception as e:
        logger.error(f"캐시 워밍업 실패: {e}")


# 캐시 모니터링
def get_cache_stats() -> dict:
    """캐시 통계 정보 반환"""
    stats = {
        'backend': settings.CACHES['default']['BACKEND'],
        'timestamp': timezone.now().isoformat(),
        'available': True
    }
    
    try:
        # Redis 사용 시 추가 정보
        if hasattr(cache, '_cache'):
            redis_info = cache._cache.get_client().info()
            stats.update({
                'used_memory': redis_info.get('used_memory_human'),
                'connected_clients': redis_info.get('connected_clients'),
                'total_commands_processed': redis_info.get('total_commands_processed'),
                'keyspace_hits': redis_info.get('keyspace_hits'),
                'keyspace_misses': redis_info.get('keyspace_misses'),
                'hit_rate': _calculate_hit_rate(
                    redis_info.get('keyspace_hits', 0),
                    redis_info.get('keyspace_misses', 0)
                )
            })
    except Exception as e:
        logger.error(f"캐시 통계 조회 실패: {e}")
        stats['error'] = str(e)
        
    return stats


def _calculate_hit_rate(hits: int, misses: int) -> float:
    """캐시 히트율 계산"""
    total = hits + misses
    if total == 0:
        return 0.0
    return round((hits / total) * 100, 2)
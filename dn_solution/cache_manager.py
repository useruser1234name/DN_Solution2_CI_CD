# -*- coding: utf-8 -*-
"""
Django Cache Manager - DN_SOLUTION2 리모델링
Multi-layer 캐싱 시스템 관리자
"""

import json
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union
from functools import wraps
from django.core.cache import cache, caches
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.http import JsonResponse
from django.contrib.auth.models import User
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Multi-layer 캐싱 시스템 관리자
    - L1 Cache: 로컬 캐시 (메모리)
    - L2 Cache: 분산 캐시 (Redis)
    - L3 Cache: 데이터베이스 캐시
    """
    
    # 캐시 레벨 정의
    L1_CACHE = 'l1'  # 로컬 메모리 캐시
    L2_CACHE = 'l2'  # Redis 분산 캐시
    L3_CACHE = 'l3'  # 데이터베이스 캐시
    
    # 캐시 키 접두사
    CACHE_PREFIXES = {
        'user': 'user:',
        'company': 'company:',
        'policy': 'policy:',
        'order': 'order:',
        'rebate': 'rebate:',
        'report': 'report:',
        'api': 'api:',
        'session': 'session:',
        'permission': 'perm:',
    }
    
    # 캐시 만료 시간 (초)
    CACHE_TIMEOUTS = {
        'short': 300,      # 5분
        'medium': 1800,    # 30분
        'long': 3600,      # 1시간
        'daily': 86400,    # 24시간
        'weekly': 604800,  # 7일
    }
    
    def __init__(self, cache_level: str = L2_CACHE):
        """캐시 매니저 초기화"""
        self.cache_level = cache_level
        self.cache = self._get_cache_backend()
        
    def _get_cache_backend(self):
        """캐시 백엔드 선택"""
        try:
            if self.cache_level == self.L1_CACHE:
                return caches['default']  # 기본 캐시 (메모리)
            elif self.cache_level == self.L2_CACHE:
                return caches['default']  # Redis 캐시
            else:
                return cache
        except Exception as e:
            logger.error(f"캐시 백엔드 초기화 실패: {e}")
            return cache
    
    def _generate_cache_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """캐시 키 생성"""
        base_key = f"{prefix}{identifier}"
        
        if kwargs:
            # 파라미터가 있는 경우 해시 생성
            params_str = json.dumps(kwargs, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            base_key = f"{base_key}:{params_hash}"
            
        return base_key
    
    def get(self, key: str, default=None) -> Any:
        """캐시에서 데이터 조회"""
        try:
            result = self.cache.get(key, default)
            if result is not None:
                logger.debug(f"캐시 HIT: {key}")
            else:
                logger.debug(f"캐시 MISS: {key}")
            return result
        except RedisError as e:
            logger.error(f"Redis 캐시 조회 실패: {e}")
            return default
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """캐시에 데이터 저장"""
        try:
            timeout = timeout or self.CACHE_TIMEOUTS['medium']
            result = self.cache.set(key, value, timeout)
            logger.debug(f"캐시 SET: {key} (timeout: {timeout}s)")
            return result
        except RedisError as e:
            logger.error(f"Redis 캐시 저장 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """캐시에서 데이터 삭제"""
        try:
            result = self.cache.delete(key)
            logger.debug(f"캐시 DELETE: {key}")
            return result
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """패턴에 매치되는 캐시 키들 삭제"""
        try:
            if hasattr(self.cache, 'delete_pattern'):
                count = self.cache.delete_pattern(pattern)
                logger.debug(f"캐시 패턴 삭제: {pattern} ({count}개)")
                return count
            return 0
        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패: {e}")
            return 0
    
    def clear(self) -> bool:
        """모든 캐시 삭제"""
        try:
            self.cache.clear()
            logger.info("모든 캐시 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"캐시 전체 삭제 실패: {e}")
            return False
    
    def get_or_set(self, key: str, callable_func, timeout: Optional[int] = None) -> Any:
        """캐시에서 조회하거나 없으면 함수 실행하여 저장"""
        try:
            result = self.cache.get_or_set(key, callable_func, timeout or self.CACHE_TIMEOUTS['medium'])
            return result
        except Exception as e:
            logger.error(f"캐시 get_or_set 실패: {e}")
            return callable_func()


# 전역 캐시 매니저 인스턴스
cache_manager = CacheManager()


def cache_key_for_user(user_id: int, key_type: str = 'profile') -> str:
    """사용자 캐시 키 생성"""
    return cache_manager._generate_cache_key(
        CacheManager.CACHE_PREFIXES['user'], 
        f"{user_id}:{key_type}"
    )


def cache_key_for_company(company_id: int, key_type: str = 'info') -> str:
    """회사 캐시 키 생성"""
    return cache_manager._generate_cache_key(
        CacheManager.CACHE_PREFIXES['company'], 
        f"{company_id}:{key_type}"
    )


def cache_key_for_api(endpoint: str, user_id: int = None, **params) -> str:
    """API 응답 캐시 키 생성"""
    identifier = f"{endpoint}"
    if user_id:
        identifier = f"{identifier}:user:{user_id}"
    
    return cache_manager._generate_cache_key(
        CacheManager.CACHE_PREFIXES['api'], 
        identifier, 
        **params
    )


def cached_api_response(timeout: int = None, key_prefix: str = 'api'):
    """
    API 응답 캐싱 데코레이터
    
    Usage:
        @cached_api_response(timeout=300)
        def my_api_view(request):
            return JsonResponse(data)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 캐시 키 생성
            cache_key_parts = [key_prefix, view_func.__name__]
            
            if hasattr(request, 'user') and request.user.is_authenticated:
                cache_key_parts.append(f"user_{request.user.id}")
            
            # URL 매개변수 추가
            if args:
                cache_key_parts.extend([str(arg) for arg in args])
            if kwargs:
                cache_key_parts.extend([f"{k}_{v}" for k, v in kwargs.items()])
            
            # GET 매개변수 추가
            if request.GET:
                get_params = sorted(request.GET.items())
                cache_key_parts.extend([f"{k}_{v}" for k, v in get_params])
            
            cache_key = ":".join(cache_key_parts)
            
            # 캐시에서 조회
            cached_response = cache_manager.get(cache_key)
            if cached_response is not None:
                logger.debug(f"API 캐시 HIT: {cache_key}")
                return JsonResponse(cached_response)
            
            # 캐시 미스 - 실제 뷰 함수 실행
            response = view_func(request, *args, **kwargs)
            
            # JSON 응답인 경우에만 캐싱
            if isinstance(response, JsonResponse) and response.status_code == 200:
                try:
                    response_data = json.loads(response.content.decode())
                    cache_manager.set(
                        cache_key, 
                        response_data, 
                        timeout or CacheManager.CACHE_TIMEOUTS['medium']
                    )
                    logger.debug(f"API 캐시 SET: {cache_key}")
                except Exception as e:
                    logger.error(f"API 응답 캐싱 실패: {e}")
            
            return response
        return wrapper
    return decorator


def cached_queryset(timeout: int = None, key_prefix: str = 'queryset'):
    """
    QuerySet 결과 캐싱 데코레이터
    
    Usage:
        @cached_queryset(timeout=600, key_prefix='users')
        def get_active_users():
            return User.objects.filter(is_active=True)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key_parts = [key_prefix, func.__name__]
            
            if args:
                cache_key_parts.extend([str(arg) for arg in args])
            if kwargs:
                cache_key_parts.extend([f"{k}_{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(cache_key_parts)
            
            # 캐시에서 조회
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"QuerySet 캐시 HIT: {cache_key}")
                return cached_result
            
            # 캐시 미스 - 실제 함수 실행
            result = func(*args, **kwargs)
            
            # QuerySet을 리스트로 변환하여 캐싱
            if hasattr(result, '__iter__') and hasattr(result, 'model'):
                # Django QuerySet
                cached_data = list(result.values())
            elif isinstance(result, models.Model):
                # 단일 모델 인스턴스
                cached_data = result.__dict__.copy()
                cached_data.pop('_state', None)
            else:
                cached_data = result
            
            cache_manager.set(
                cache_key, 
                cached_data, 
                timeout or CacheManager.CACHE_TIMEOUTS['medium']
            )
            logger.debug(f"QuerySet 캐시 SET: {cache_key}")
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """캐시 무효화 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 함수 실행 후 캐시 무효화
            cache_manager.delete_pattern(pattern)
            logger.debug(f"캐시 무효화: {pattern}")
            return result
        return wrapper
    return decorator


# 캐시 상태 모니터링
class CacheMonitor:
    """캐시 상태 모니터링 클래스"""
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """캐시 통계 정보 조회"""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            info = redis_conn.info()
            stats = {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'hit_rate': 0,
            }
            
            # 히트율 계산
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            if hits + misses > 0:
                stats['hit_rate'] = round((hits / (hits + misses)) * 100, 2)
            
            return stats
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}
    
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """캐시 시스템 헬스체크"""
        try:
            test_key = "health_check_test"
            test_value = f"test_{timezone.now().isoformat()}"
            
            # 쓰기 테스트
            write_success = cache_manager.set(test_key, test_value, 60)
            
            # 읽기 테스트
            read_value = cache_manager.get(test_key)
            read_success = read_value == test_value
            
            # 삭제 테스트
            delete_success = cache_manager.delete(test_key)
            
            return {
                'status': 'healthy' if all([write_success, read_success, delete_success]) else 'unhealthy',
                'write_test': write_success,
                'read_test': read_success,
                'delete_test': delete_success,
                'timestamp': timezone.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"캐시 헬스체크 실패: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
            }
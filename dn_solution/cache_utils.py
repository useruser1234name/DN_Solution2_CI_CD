# -*- coding: utf-8 -*-
"""
Cache Utils - DN_SOLUTION2 리모델링
캐시 관련 유틸리티 함수들
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import JsonResponse
from django.utils import timezone
from dn_solution.cache_manager import cache_manager, CacheManager

logger = logging.getLogger(__name__)


class CacheUtils:
    """캐시 관련 유틸리티 클래스"""
    
    @staticmethod
    def serialize_for_cache(obj: Any) -> Any:
        """객체를 캐시 저장 가능한 형태로 직렬화"""
        if isinstance(obj, models.Model):
            # Django 모델 인스턴스
            data = {}
            for field in obj._meta.fields:
                value = getattr(obj, field.name)
                if isinstance(value, (str, int, float, bool, type(None))):
                    data[field.name] = value
                elif hasattr(value, 'isoformat'):  # datetime
                    data[field.name] = value.isoformat()
                else:
                    data[field.name] = str(value)
            return data
        
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            # 리스트나 QuerySet
            return [CacheUtils.serialize_for_cache(item) for item in obj]
        
        elif isinstance(obj, dict):
            # 딕셔너리
            return {k: CacheUtils.serialize_for_cache(v) for k, v in obj.items()}
        
        else:
            # 기본 타입들
            try:
                json.dumps(obj, cls=DjangoJSONEncoder)
                return obj
            except TypeError:
                return str(obj)
    
    @staticmethod
    def cache_queryset_results(queryset, cache_key: str, timeout: int = None) -> List[Dict]:
        """QuerySet 결과를 캐시하고 반환"""
        try:
            # 캐시에서 조회
            cached_results = cache_manager.get(cache_key)
            if cached_results is not None:
                logger.debug(f"QuerySet 캐시 HIT: {cache_key}")
                return cached_results
            
            # 캐시 미스 - DB에서 조회
            results = list(queryset.values())
            
            # 캐시에 저장
            timeout = timeout or CacheManager.CACHE_TIMEOUTS['medium']
            cache_manager.set(cache_key, results, timeout)
            logger.debug(f"QuerySet 캐시 SET: {cache_key}")
            
            return results
            
        except Exception as e:
            logger.error(f"QuerySet 캐싱 실패: {e}")
            return list(queryset.values())
    
    @staticmethod
    def cache_model_instance(instance: models.Model, cache_key: str = None, timeout: int = None) -> Dict:
        """모델 인스턴스를 캐시하고 반환"""
        try:
            if not cache_key:
                cache_key = f"{instance._meta.label}:{instance.pk}"
            
            # 캐시에서 조회
            cached_instance = cache_manager.get(cache_key)
            if cached_instance is not None:
                logger.debug(f"모델 인스턴스 캐시 HIT: {cache_key}")
                return cached_instance
            
            # 캐시 미스 - 인스턴스 직렬화
            serialized_data = CacheUtils.serialize_for_cache(instance)
            
            # 캐시에 저장
            timeout = timeout or CacheManager.CACHE_TIMEOUTS['medium']
            cache_manager.set(cache_key, serialized_data, timeout)
            logger.debug(f"모델 인스턴스 캐시 SET: {cache_key}")
            
            return serialized_data
            
        except Exception as e:
            logger.error(f"모델 인스턴스 캐싱 실패: {e}")
            return CacheUtils.serialize_for_cache(instance)
    
    @staticmethod
    def invalidate_model_cache(model_class: models.Model, instance_id: int = None) -> int:
        """특정 모델의 캐시를 무효화"""
        try:
            model_label = model_class._meta.label
            
            if instance_id:
                # 특정 인스턴스 캐시만 삭제
                cache_key = f"{model_label}:{instance_id}"
                return 1 if cache_manager.delete(cache_key) else 0
            else:
                # 모델 전체 캐시 삭제
                pattern = f"{model_label}:*"
                return cache_manager.delete_pattern(pattern)
                
        except Exception as e:
            logger.error(f"모델 캐시 무효화 실패: {e}")
            return 0
    
    @staticmethod
    def cache_expensive_computation(func: Callable, cache_key: str, timeout: int = None, *args, **kwargs) -> Any:
        """비용이 많이 드는 연산 결과를 캐시"""
        try:
            # 캐시에서 조회
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"연산 결과 캐시 HIT: {cache_key}")
                return cached_result
            
            # 캐시 미스 - 연산 실행
            result = func(*args, **kwargs)
            
            # 결과 직렬화 및 캐시 저장
            serialized_result = CacheUtils.serialize_for_cache(result)
            timeout = timeout or CacheManager.CACHE_TIMEOUTS['long']
            cache_manager.set(cache_key, serialized_result, timeout)
            logger.debug(f"연산 결과 캐시 SET: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"연산 결과 캐싱 실패: {e}")
            return func(*args, **kwargs)


def cache_user_data(user_id: int, data_type: str = 'profile') -> Dict:
    """사용자 데이터 캐싱"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    cache_key = f"user:{user_id}:{data_type}"
    
    try:
        # 캐시에서 조회
        cached_data = cache_manager.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 사용자 조회
        user = User.objects.select_related('companyuser__company').get(id=user_id)
        
        # 사용자 데이터 구성
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        
        # CompanyUser 정보 추가
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            user_data.update({
                'company': {
                    'id': company_user.company.id,
                    'code': company_user.company.code,
                    'name': company_user.company.name,
                    'type': company_user.company.type,
                },
                'role': company_user.role,
                'status': company_user.status,
                'is_primary_admin': getattr(company_user, 'is_primary_admin', False),
            })
        
        # 캐시에 저장
        cache_manager.set(cache_key, user_data, CacheManager.CACHE_TIMEOUTS['long'])
        return user_data
        
    except User.DoesNotExist:
        logger.error(f"사용자를 찾을 수 없음: {user_id}")
        return {}
    except Exception as e:
        logger.error(f"사용자 데이터 캐싱 실패: {e}")
        return {}


def cache_company_hierarchy(company_id: int) -> Dict:
    """회사 계층 구조 캐싱"""
    from companies.models import Company
    
    cache_key = f"company_hierarchy:{company_id}"
    
    try:
        # 캐시에서 조회
        cached_hierarchy = cache_manager.get(cache_key)
        if cached_hierarchy is not None:
            return cached_hierarchy
        
        # 회사 계층 구조 조회
        def get_company_hierarchy(company):
            hierarchy = {
                'id': company.id,
                'code': company.code,
                'name': company.name,
                'type': company.type,
                'status': company.status,
                'children': []
            }
            
            # 하위 회사들 조회
            children = Company.objects.filter(parent_company=company, status=True)
            for child in children:
                hierarchy['children'].append(get_company_hierarchy(child))
            
            return hierarchy
        
        company = Company.objects.get(id=company_id)
        hierarchy_data = get_company_hierarchy(company)
        
        # 캐시에 저장
        cache_manager.set(cache_key, hierarchy_data, CacheManager.CACHE_TIMEOUTS['daily'])
        return hierarchy_data
        
    except Company.DoesNotExist:
        logger.error(f"회사를 찾을 수 없음: {company_id}")
        return {}
    except Exception as e:
        logger.error(f"회사 계층 구조 캐싱 실패: {e}")
        return {}


def cache_policy_rules(policy_id: int = None) -> Union[Dict, List[Dict]]:
    """정책 규칙 캐싱"""
    from policies.models import Policy
    
    cache_key = f"policy_rules:{policy_id}" if policy_id else "policy_rules:all"
    
    try:
        # 캐시에서 조회
        cached_rules = cache_manager.get(cache_key)
        if cached_rules is not None:
            return cached_rules
        
        if policy_id:
            # 특정 정책 규칙
            policy = Policy.objects.get(id=policy_id)
            rules_data = CacheUtils.serialize_for_cache(policy)
        else:
            # 모든 활성 정책 규칙
            policies = Policy.objects.filter(is_active=True)
            rules_data = [CacheUtils.serialize_for_cache(policy) for policy in policies]
        
        # 캐시에 저장
        cache_manager.set(cache_key, rules_data, CacheManager.CACHE_TIMEOUTS['long'])
        return rules_data
        
    except Policy.DoesNotExist:
        logger.error(f"정책을 찾을 수 없음: {policy_id}")
        return {} if policy_id else []
    except Exception as e:
        logger.error(f"정책 규칙 캐싱 실패: {e}")
        return {} if policy_id else []


def cache_dashboard_data(user_id: int, company_id: int) -> Dict:
    """대시보드 데이터 캐싱"""
    cache_key = f"dashboard:user_{user_id}:company_{company_id}"
    
    try:
        # 캐시에서 조회
        cached_data = cache_manager.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # 대시보드 데이터 조회 (실제 구현은 각 모델에 따라 다름)
        dashboard_data = {
            'summary': {
                'total_orders': 0,  # 실제 쿼리로 대체
                'monthly_rebates': 0,  # 실제 쿼리로 대체
                'active_policies': 0,  # 실제 쿼리로 대체
                'pending_approvals': 0,  # 실제 쿼리로 대체
            },
            'recent_activities': [],  # 실제 쿼리로 대체
            'notifications': [],  # 실제 쿼리로 대체
            'generated_at': timezone.now().isoformat(),
        }
        
        # 캐시에 저장 (짧은 시간)
        cache_manager.set(cache_key, dashboard_data, CacheManager.CACHE_TIMEOUTS['short'])
        return dashboard_data
        
    except Exception as e:
        logger.error(f"대시보드 데이터 캐싱 실패: {e}")
        return {}


# 캐시 데코레이터들
def cache_result(timeout: int = None, key_prefix: str = 'result'):
    """함수 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            import hashlib
            key_data = f"{func.__module__}.{func.__name__}:{args}:{sorted(kwargs.items())}"
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            cache_key = f"{key_prefix}:{key_hash}"
            
            return CacheUtils.cache_expensive_computation(
                func, cache_key, timeout, *args, **kwargs
            )
        return wrapper
    return decorator


def cache_model_method(timeout: int = None):
    """모델 메소드 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 인스턴스 기반 캐시 키 생성
            cache_key = f"{self._meta.label}:{self.pk}:{func.__name__}"
            if args or kwargs:
                import hashlib
                key_data = f"{args}:{sorted(kwargs.items())}"
                key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{key_hash}"
            
            return CacheUtils.cache_expensive_computation(
                func, cache_key, timeout, self, *args, **kwargs
            )
        return wrapper
    return decorator


def invalidate_on_save(cache_patterns: List[str]):
    """모델 저장 시 캐시 무효화 데코레이터"""
    def decorator(save_method):
        @wraps(save_method)
        def wrapper(self, *args, **kwargs):
            result = save_method(self, *args, **kwargs)
            
            # 캐시 무효화
            for pattern in cache_patterns:
                # 인스턴스 정보로 패턴 포맷팅
                formatted_pattern = pattern.format(
                    model=self._meta.label,
                    pk=self.pk,
                    **{field.name: getattr(self, field.name) for field in self._meta.fields}
                )
                cache_manager.delete_pattern(formatted_pattern)
                logger.debug(f"모델 저장 후 캐시 무효화: {formatted_pattern}")
            
            return result
        return wrapper
    return decorator
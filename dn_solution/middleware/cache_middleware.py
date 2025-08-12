# -*- coding: utf-8 -*-
"""
Cache Middleware - DN_SOLUTION2 리모델링
캐시 성능 최적화 미들웨어
"""

import time
import json
import logging
from typing import Any, Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.cache import get_cache_key
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PerformanceCacheMiddleware(MiddlewareMixin):
    """
    성능 최적화를 위한 캐시 미들웨어
    - API 응답 캐싱
    - 사용자별 권한 캐싱
    - DB 쿼리 결과 캐싱
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """요청 처리 전 캐시 확인"""
        
        # 캐시하지 않을 요청들 (POST, PUT, DELETE 등)
        if request.method not in ['GET', 'HEAD']:
            return None
            
        # 관리자 페이지는 캐시하지 않음
        if request.path.startswith('/admin/'):
            return None
            
        # API 요청 캐싱 확인
        if request.path.startswith('/api/'):
            return self._check_api_cache(request)
            
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """응답 처리 후 캐시 저장"""
        
        # 성공적인 GET 요청만 캐싱
        if (request.method == 'GET' and 
            response.status_code == 200 and 
            request.path.startswith('/api/')):
            
            self._store_api_cache(request, response)
        
        # 캐시 통계 헤더 추가 (개발환경)
        if settings.DEBUG:
            response['X-Cache-Status'] = getattr(request, '_cache_status', 'MISS')
            
        return response
    
    def _check_api_cache(self, request: HttpRequest) -> Optional[JsonResponse]:
        """API 캐시 확인"""
        try:
            cache_key = self._generate_api_cache_key(request)
            cached_response = self.cache_manager.get(cache_key)
            
            if cached_response is not None:
                logger.debug(f"API 캐시 HIT: {cache_key}")
                request._cache_status = 'HIT'
                
                # 캐시된 응답 반환
                response = JsonResponse(cached_response)
                response['X-Cache'] = 'HIT'
                response['X-Cache-Key'] = cache_key
                return response
                
            request._cache_status = 'MISS'
            return None
            
        except Exception as e:
            logger.error(f"API 캐시 확인 실패: {e}")
            return None
    
    def _store_api_cache(self, request: HttpRequest, response: HttpResponse):
        """API 응답 캐싱"""
        try:
            # JSON 응답만 캐싱
            if not isinstance(response, JsonResponse):
                return
                
            cache_key = self._generate_api_cache_key(request)
            
            # 응답 데이터 추출
            response_data = json.loads(response.content.decode())
            
            # 캐시 만료 시간 결정
            timeout = self._get_cache_timeout(request.path)
            
            # 캐시 저장
            success = self.cache_manager.set(cache_key, response_data, timeout)
            
            if success:
                logger.debug(f"API 캐시 SET: {cache_key} (timeout: {timeout}s)")
                response['X-Cache'] = 'MISS'
                response['X-Cache-Timeout'] = str(timeout)
            
        except Exception as e:
            logger.error(f"API 응답 캐싱 실패: {e}")
    
    def _generate_api_cache_key(self, request: HttpRequest) -> str:
        """API 캐시 키 생성"""
        key_parts = ['api', request.path.strip('/').replace('/', '_')]
        
        # 사용자별 캐시
        if hasattr(request, 'user') and request.user.is_authenticated:
            key_parts.append(f"user_{request.user.id}")
        
        # GET 매개변수 추가
        if request.GET:
            get_params = sorted(request.GET.items())
            params_str = "_".join([f"{k}_{v}" for k, v in get_params])
            key_parts.append(params_str)
        
        return ":".join(key_parts)
    
    def _get_cache_timeout(self, path: str) -> int:
        """경로별 캐시 만료 시간 결정"""
        
        # 경로별 캐시 설정
        cache_timeouts = {
            '/api/companies/': CacheManager.CACHE_TIMEOUTS['long'],      # 1시간
            '/api/policies/': CacheManager.CACHE_TIMEOUTS['medium'],     # 30분
            '/api/orders/': CacheManager.CACHE_TIMEOUTS['short'],        # 5분
            '/api/rebates/': CacheManager.CACHE_TIMEOUTS['medium'],      # 30분
            '/api/reports/': CacheManager.CACHE_TIMEOUTS['short'],       # 5분 (실시간성 중요)
            '/api/users/': CacheManager.CACHE_TIMEOUTS['medium'],        # 30분
        }
        
        # 경로 매칭
        for pattern, timeout in cache_timeouts.items():
            if path.startswith(pattern):
                return timeout
                
        # 기본값
        return CacheManager.CACHE_TIMEOUTS['medium']


class UserPermissionCacheMiddleware(MiddlewareMixin):
    """
    사용자 권한 캐싱 미들웨어
    - 사용자별 권한 정보 캐싱
    - 회사별 계층 권한 캐싱
    """
    
    def process_request(self, request: HttpRequest) -> None:
        """요청 처리 시 사용자 권한 캐싱"""
        
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return
        
        # 사용자 권한 정보 캐싱
        self._cache_user_permissions(request.user)
        
        # 회사 정보 캐싱
        if hasattr(request.user, 'companyuser'):
            self._cache_company_info(request.user.companyuser.company)
    
    def _cache_user_permissions(self, user) -> None:
        """사용자 권한 정보 캐싱"""
        try:
            cache_key = f"user_permissions:{user.id}"
            cached_permissions = cache_manager.get(cache_key)
            
            if cached_permissions is None:
                # 권한 정보 조회 및 캐싱
                permissions = self._get_user_permissions(user)
                cache_manager.set(
                    cache_key, 
                    permissions, 
                    CacheManager.CACHE_TIMEOUTS['long']
                )
                logger.debug(f"사용자 권한 캐싱: {cache_key}")
            
            # request에 권한 정보 첨부
            request.user._cached_permissions = cached_permissions or self._get_user_permissions(user)
            
        except Exception as e:
            logger.error(f"사용자 권한 캐싱 실패: {e}")
    
    def _cache_company_info(self, company) -> None:
        """회사 정보 캐싱"""
        try:
            cache_key = f"company_info:{company.id}"
            cached_info = cache_manager.get(cache_key)
            
            if cached_info is None:
                # 회사 정보 조회 및 캐싱
                company_info = {
                    'id': company.id,
                    'code': company.code,
                    'name': company.name,
                    'type': company.type,
                    'status': company.status,
                    'parent_company_id': company.parent_company_id,
                    'hierarchy_level': getattr(company, 'hierarchy_level', 0),
                }
                
                cache_manager.set(
                    cache_key, 
                    company_info, 
                    CacheManager.CACHE_TIMEOUTS['daily']
                )
                logger.debug(f"회사 정보 캐싱: {cache_key}")
            
        except Exception as e:
            logger.error(f"회사 정보 캐싱 실패: {e}")
    
    def _get_user_permissions(self, user) -> dict:
        """사용자 권한 정보 조회"""
        try:
            permissions = {
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
                'groups': list(user.groups.values_list('name', flat=True)),
                'user_permissions': list(user.user_permissions.values_list('codename', flat=True)),
            }
            
            # CompanyUser 권한 추가
            if hasattr(user, 'companyuser'):
                company_user = user.companyuser
                permissions.update({
                    'company_id': company_user.company_id,
                    'company_type': company_user.company.type,
                    'role': company_user.role,
                    'is_primary_admin': getattr(company_user, 'is_primary_admin', False),
                    'status': company_user.status,
                })
            
            return permissions
            
        except Exception as e:
            logger.error(f"사용자 권한 조회 실패: {e}")
            return {}


class CacheInvalidationMiddleware(MiddlewareMixin):
    """
    캐시 무효화 미들웨어
    - 데이터 변경 시 관련 캐시 자동 무효화
    """
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """응답 처리 후 캐시 무효화"""
        
        # 데이터 변경 요청 (POST, PUT, DELETE)인 경우
        if (request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and 
            response.status_code in [200, 201, 204]):
            
            self._invalidate_related_cache(request)
        
        return response
    
    def _invalidate_related_cache(self, request: HttpRequest) -> None:
        """관련 캐시 무효화"""
        try:
            path = request.path
            
            # API 경로별 캐시 무효화 패턴
            invalidation_patterns = {
                '/api/companies/': ['api:*companies*', 'company_info:*'],
                '/api/policies/': ['api:*policies*', 'policy:*'],
                '/api/orders/': ['api:*orders*', 'order:*', 'api:*reports*'],
                '/api/rebates/': ['api:*rebates*', 'rebate:*', 'api:*reports*'],
                '/api/users/': ['api:*users*', 'user:*', 'user_permissions:*'],
                '/api/auth/': ['user_permissions:*', 'session:*'],
            }
            
            # 매칭되는 패턴으로 캐시 무효화
            for pattern_path, cache_patterns in invalidation_patterns.items():
                if path.startswith(pattern_path):
                    for cache_pattern in cache_patterns:
                        deleted_count = cache_manager.delete_pattern(cache_pattern)
                        if deleted_count > 0:
                            logger.info(f"캐시 무효화: {cache_pattern} ({deleted_count}개)")
                    break
        
        except Exception as e:
            logger.error(f"캐시 무효화 실패: {e}")


class CacheMetricsMiddleware(MiddlewareMixin):
    """
    캐시 성능 메트릭 수집 미들웨어
    """
    
    def process_request(self, request: HttpRequest) -> None:
        """요청 시작 시간 기록"""
        request._cache_start_time = time.time()
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """응답 완료 시 메트릭 기록"""
        
        if hasattr(request, '_cache_start_time'):
            duration = time.time() - request._cache_start_time
            
            # 캐시 상태에 따른 메트릭
            cache_status = getattr(request, '_cache_status', 'UNKNOWN')
            
            if settings.DEBUG:
                response['X-Cache-Duration'] = f"{duration:.3f}s"
                
            # 로깅 (운영환경에서는 메트릭 시스템으로 전송)
            logger.info(
                f"Cache Metrics - Path: {request.path}, "
                f"Method: {request.method}, "
                f"Status: {cache_status}, "
                f"Duration: {duration:.3f}s, "
                f"Response: {response.status_code}"
            )
        
        return response
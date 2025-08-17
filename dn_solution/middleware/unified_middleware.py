# -*- coding: utf-8 -*-
"""
통합 미들웨어 - DN_SOLUTION2 최적화
성능 모니터링, API 로깅, 캐시 관리를 하나의 미들웨어로 통합
"""

import time
import json
import logging
from typing import Any, Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('api')
performance_logger = logging.getLogger('performance')


class UnifiedAPIMiddleware(MiddlewareMixin):
    """
    통합 API 미들웨어
    - API 로깅
    - 성능 모니터링
    - 간소화된 캐시 관리
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.start_time = None
        
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """요청 처리 시작"""
        self.start_time = time.time()
        request._request_id = f"req_{int(self.start_time * 1000)}"
        
        # API 요청인 경우에만 로깅
        if request.path.startswith('/api/'):
            self._log_api_request(request)
            
            # 간단한 캐시 확인 (GET 요청만)
            if request.method == 'GET':
                cached_response = self._check_simple_cache(request)
                if cached_response:
                    return cached_response
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """응답 처리 완료"""
        
        if not hasattr(request, '_request_id'):
            return response
            
        end_time = time.time()
        duration = end_time - (self.start_time or end_time)
        
        # API 요청인 경우 로깅 및 성능 모니터링
        if request.path.startswith('/api/'):
            self._log_api_response(request, response, duration)
            self._monitor_performance(request, response, duration)
            
            # 성공적인 GET 요청 캐싱
            if (request.method == 'GET' and 
                response.status_code == 200 and
                isinstance(response, JsonResponse)):
                self._store_simple_cache(request, response)
        
        # 성능 헤더 추가
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        if settings.DEBUG:
            response['X-Cache-Status'] = getattr(request, '_cache_status', 'MISS')
        
        return response
    
    def process_exception(self, request, exception):
        """예외 처리"""
        if request.path.startswith('/api/'):
            logger.error(
                f"[{getattr(request, '_request_id', 'unknown')}] API 예외 발생 - "
                f"{request.method} {request.path} - 오류: {str(exception)}", 
                exc_info=True
            )
        return None
    
    def _log_api_request(self, request: HttpRequest):
        """API 요청 로깅 (간소화)"""
        request_id = request._request_id
        
        logger.info(
            f"[{request_id}] {request.method} {request.path} - "
            f"IP: {request.META.get('REMOTE_ADDR')} - "
            f"User: {getattr(request.user, 'username', 'Anonymous')}"
        )
        
        # POST/PUT/PATCH 요청의 민감정보 마스킹
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = request.body.decode('utf-8')
                sanitized_body = self._sanitize_request_body(body)
                logger.info(f"[{request_id}] 요청 본문: {sanitized_body}")
            except Exception:
                logger.info(f"[{request_id}] 요청 본문: [바이너리 데이터]")
    
    def _log_api_response(self, request: HttpRequest, response: HttpResponse, duration: float):
        """API 응답 로깅 (간소화)"""
        request_id = request._request_id
        
        log_level = logger.error if response.status_code >= 400 else logger.info
        log_level(
            f"[{request_id}] 응답 완료 - 상태: {response.status_code} - "
            f"소요시간: {duration:.3f}초"
        )
        
        # 오류 응답의 경우 상세 로깅
        if response.status_code >= 400 and hasattr(response, 'content'):
            try:
                error_content = response.content.decode('utf-8')
                if len(error_content) < 500:  # 너무 긴 오류는 생략
                    logger.error(f"[{request_id}] 오류 내용: {error_content}")
            except Exception:
                pass
    
    def _monitor_performance(self, request: HttpRequest, response: HttpResponse, duration: float):
        """성능 모니터링 (간소화)"""
        
        # 느린 요청 경고 (2초 이상)
        if duration > 2.0:
            performance_logger.warning(
                f"느린 API 요청 - {request.method} {request.path} - "
                f"처리시간: {duration:.3f}초"
            )
        
        # 기본 성능 로깅 (디버그 모드에서만)
        if settings.DEBUG:
            performance_logger.debug(
                f"{request.method} {request.path} - "
                f"처리시간: {duration:.3f}초 - "
                f"상태: {response.status_code}"
            )
    
    def _check_simple_cache(self, request: HttpRequest) -> Optional[JsonResponse]:
        """간단한 캐시 확인"""
        try:
            # 캐시하지 않을 경로들
            no_cache_paths = ['/api/auth/', '/api/admin/', '/api/dashboard/']
            if any(request.path.startswith(path) for path in no_cache_paths):
                return None
            
            cache_key = f"api_cache:{request.path}:{request.GET.urlencode()}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                request._cache_status = 'HIT'
                response = JsonResponse(cached_data)
                response['X-Cache'] = 'HIT'
                return response
            
            request._cache_status = 'MISS'
            return None
            
        except Exception as e:
            logger.debug(f"캐시 확인 실패: {e}")
            return None
    
    def _store_simple_cache(self, request: HttpRequest, response: JsonResponse):
        """간단한 캐시 저장"""
        try:
            # 캐시하지 않을 경로들
            no_cache_paths = ['/api/auth/', '/api/admin/', '/api/dashboard/']
            if any(request.path.startswith(path) for path in no_cache_paths):
                return
            
            cache_key = f"api_cache:{request.path}:{request.GET.urlencode()}"
            response_data = json.loads(response.content.decode())
            
            # 캐시 만료 시간 (기본 5분)
            timeout = 300
            if '/policies/' in request.path:
                timeout = 600  # 정책은 10분
            elif '/companies/' in request.path:
                timeout = 180  # 업체는 3분
            
            cache.set(cache_key, response_data, timeout)
            logger.debug(f"캐시 저장: {cache_key} (TTL: {timeout}초)")
            
        except Exception as e:
            logger.debug(f"캐시 저장 실패: {e}")
    
    def _sanitize_request_body(self, body: str) -> str:
        """요청 본문 민감정보 마스킹 (간소화)"""
        import re
        
        # 민감한 필드들
        sensitive_fields = ['password', 'token', 'secret', 'key', 'csrf']
        
        sanitized_body = body
        for field in sensitive_fields:
            # JSON 형태 마스킹
            pattern = rf'"{field}"[^:]*:[^",}}\]]*[",}}\]]'
            sanitized_body = re.sub(
                pattern, 
                f'"{field}": "***MASKED***"', 
                sanitized_body, 
                flags=re.IGNORECASE
            )
        
        # 너무 긴 본문은 요약
        if len(sanitized_body) > 500:
            sanitized_body = sanitized_body[:500] + "... [생략]"
        
        return sanitized_body

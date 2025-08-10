"""
보안 미들웨어 - DN_SOLUTION2
Rate Limiting, IP 화이트리스트, SQL Injection 방지
"""

import logging
import time
import hashlib
from typing import Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    API Rate Limiting 미들웨어
    - IP 기반 요청 제한
    - 사용자별 요청 제한
    - DDoS 공격 방지
    """
    
    # 기본 제한 설정
    DEFAULT_LIMITS = {
        'anon': {'requests': 100, 'window': 3600},  # 시간당 100 요청
        'user': {'requests': 1000, 'window': 3600},  # 시간당 1000 요청
        'burst': {'requests': 60, 'window': 60},     # 분당 60 요청
    }
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """요청 처리 전 Rate Limit 체크"""
        
        # 관리자나 내부 요청은 제외
        if request.path.startswith('/admin/') or self._is_internal_ip(request):
            return None
        
        # Rate Limit 체크
        if not self._check_rate_limit(request):
            return JsonResponse(
                {'error': 'Rate limit exceeded. Please try again later.'},
                status=429,
                headers={'Retry-After': '60'}
            )
        
        return None
    
    def _check_rate_limit(self, request: HttpRequest) -> bool:
        """Rate Limit 체크"""
        # 사용자 식별
        if hasattr(request, 'user') and request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
            limits = self.DEFAULT_LIMITS['user']
        else:
            identifier = f"ip:{self._get_client_ip(request)}"
            limits = self.DEFAULT_LIMITS['anon']
        
        # Burst 체크 (분당 제한)
        burst_key = f"rate_limit:burst:{identifier}"
        burst_count = cache.get(burst_key, 0)
        
        if burst_count >= self.DEFAULT_LIMITS['burst']['requests']:
            logger.warning(f"Burst limit exceeded for {identifier}")
            return False
        
        # 시간당 제한 체크
        hourly_key = f"rate_limit:hourly:{identifier}"
        hourly_count = cache.get(hourly_key, 0)
        
        if hourly_count >= limits['requests']:
            logger.warning(f"Hourly limit exceeded for {identifier}")
            return False
        
        # 카운터 증가
        cache.set(burst_key, burst_count + 1, self.DEFAULT_LIMITS['burst']['window'])
        cache.set(hourly_key, hourly_count + 1, limits['window'])
        
        return True
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _is_internal_ip(self, request: HttpRequest) -> bool:
        """내부 IP 체크"""
        ip = self._get_client_ip(request)
        internal_ips = ['127.0.0.1', 'localhost', '::1']
        return ip in internal_ips


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    IP 화이트리스트 미들웨어
    - 특정 IP만 접근 허용 (선택적)
    - 관리자 페이지 보호
    """
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """IP 화이트리스트 체크"""
        
        # 화이트리스트가 설정되지 않았으면 통과
        whitelist = getattr(settings, 'IP_WHITELIST', [])
        if not whitelist:
            return None
        
        # 관리자 페이지 접근 시 IP 체크
        if request.path.startswith('/admin/'):
            client_ip = self._get_client_ip(request)
            
            if client_ip not in whitelist:
                logger.warning(f"Unauthorized admin access attempt from {client_ip}")
                return JsonResponse(
                    {'error': 'Access denied'},
                    status=403
                )
        
        return None
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    SQL Injection 방지 미들웨어
    - 의심스러운 패턴 감지
    - 파라미터 검증
    """
    
    # SQL Injection 패턴
    SUSPICIOUS_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bOR\b\s*\d+\s*=\s*\d+)",
        r"(\bAND\b\s*\d+\s*=\s*\d+)",
        r"(';|';--|';\s*DROP)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(xp_cmdshell|sp_executesql)",
        r"(<script|javascript:|onerror=|onload=)",
    ]
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """요청 파라미터 검증"""
        
        # GET, POST 파라미터 검증
        suspicious_params = []
        
        # GET 파라미터 체크
        for key, value in request.GET.items():
            if self._is_suspicious(str(value)):
                suspicious_params.append(f"GET[{key}]={value}")
        
        # POST 파라미터 체크
        if request.method == 'POST':
            for key, value in request.POST.items():
                if self._is_suspicious(str(value)):
                    suspicious_params.append(f"POST[{key}]={value}")
        
        # 의심스러운 파라미터 발견 시
        if suspicious_params:
            logger.warning(
                f"Potential SQL injection attempt from {self._get_client_ip(request)}: "
                f"{', '.join(suspicious_params)}"
            )
            
            # 보안 이벤트 기록
            self._log_security_event(request, 'sql_injection_attempt', suspicious_params)
            
            return JsonResponse(
                {'error': 'Invalid request parameters'},
                status=400
            )
        
        return None
    
    def _is_suspicious(self, value: str) -> bool:
        """의심스러운 패턴 체크"""
        import re
        
        value_upper = value.upper()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _log_security_event(self, request: HttpRequest, event_type: str, details: list):
        """보안 이벤트 로깅"""
        try:
            from companies.models import SecurityLog  # 보안 로그 모델 (생성 필요)
            
            SecurityLog.objects.create(
                event_type=event_type,
                ip_address=self._get_client_ip(request),
                user=request.user if request.user.is_authenticated else None,
                path=request.path,
                method=request.method,
                details=str(details),
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    보안 헤더 추가 미들웨어
    """
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """보안 헤더 추가"""
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.dn-solution.com;"
        )
        
        # 기타 보안 헤더
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class AuditLogMiddleware(MiddlewareMixin):
    """
    감사 로그 미들웨어
    - 중요 작업 로깅
    - 데이터 변경 추적
    """
    
    # 감사 대상 경로
    AUDIT_PATHS = [
        '/api/companies/',
        '/api/policies/',
        '/api/orders/',
        '/api/users/',
        '/admin/',
    ]
    
    def process_request(self, request: HttpRequest) -> None:
        """요청 시작 시간 기록"""
        request._audit_start_time = time.time()
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """감사 로그 기록"""
        
        # 감사 대상 체크
        if not any(request.path.startswith(path) for path in self.AUDIT_PATHS):
            return response
        
        # 데이터 변경 작업만 로깅
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return response
        
        # 성공한 요청만 로깅
        if response.status_code not in range(200, 300):
            return response
        
        # 감사 로그 기록
        try:
            duration = time.time() - getattr(request, '_audit_start_time', 0)
            
            audit_data = {
                'user': request.user.username if request.user.is_authenticated else 'anonymous',
                'ip': self._get_client_ip(request),
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration': f"{duration:.3f}s",
                'timestamp': timezone.now().isoformat(),
            }
            
            logger.info(f"AUDIT: {audit_data}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip

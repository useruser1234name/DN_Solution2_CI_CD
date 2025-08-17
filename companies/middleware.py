import logging
import json
import time
from django.utils import timezone
from django.http import JsonResponse

logger = logging.getLogger('api')

class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("[APILoggingMiddleware] 미들웨어 초기화 완료")

    def __call__(self, request):
        # 요청 시작 시간
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000)}"
        
        # API 요청 로깅
        if request.path.startswith('/api/'):
            logger.info(f"[{request_id}] API 요청 시작 - {request.method} {request.path}")
            logger.info(f"[{request_id}] 클라이언트 정보 - IP: {request.META.get('REMOTE_ADDR')} - User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
            logger.info(f"[{request_id}] 요청 시간: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 요청 헤더 로깅 (민감한 정보 제외)
            headers = dict(request.headers)
            safe_headers = self._sanitize_headers(headers)
            logger.info(f"[{request_id}] 요청 헤더: {json.dumps(safe_headers, default=str, ensure_ascii=False)}")
            
            # POST/PUT/PATCH 요청의 경우 본문 로깅 (민감한 정보 제외)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = request.body.decode('utf-8')
                    sanitized_body = self._sanitize_request_body(body)
                    logger.info(f"[{request_id}] 요청 본문: {sanitized_body}")
                except Exception as e:
                    logger.warning(f"[{request_id}] 요청 본문 로깅 실패: {str(e)}")

        response = self.get_response(request)

        # 응답 로깅
        if request.path.startswith('/api/'):
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"[{request_id}] API 응답 완료 - {request.method} {request.path}")
            logger.info(f"[{request_id}] 응답 상태: {response.status_code}")
            logger.info(f"[{request_id}] 소요시간: {duration:.3f}초")
            logger.info(f"[{request_id}] 응답 시간: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 응답 헤더 로깅 (민감한 정보 제외)
            response_headers = dict(response.headers)
            safe_response_headers = {k: v for k, v in response_headers.items() if k.lower() not in ['set-cookie']}
            logger.info(f"[{request_id}] 응답 헤더: {json.dumps(safe_response_headers, default=str, ensure_ascii=False)}")
            
            # 응답 본문 로깅 (JSON 응답인 경우)
            if hasattr(response, 'content') and response.get('Content-Type', '').startswith('application/json'):
                try:
                    content = response.content.decode('utf-8')
                    if len(content) < 1000:  # 너무 긴 응답은 로깅하지 않음
                        logger.info(f"[{request_id}] 응답 본문: {content}")
                    else:
                        logger.info(f"[{request_id}] 응답 본문 길이: {len(content)}자 (너무 길어서 로깅 생략)")
                except Exception as e:
                    logger.warning(f"[{request_id}] 응답 본문 로깅 실패: {str(e)}")
            
            # 오류 응답 로깅
            if response.status_code >= 400:
                logger.error(f"[{request_id}] API 오류 응답 - 상태: {response.status_code} - 경로: {request.path}")
                if hasattr(response, 'content'):
                    try:
                        error_content = response.content.decode('utf-8')
                        logger.error(f"[{request_id}] 오류 내용: {error_content}")
                    except Exception as e:
                        logger.warning(f"[{request_id}] 응답 본문 로깅 실패: {str(e)}")

        return response

    def _sanitize_headers(self, headers):
        """민감한 헤더 정보를 마스킹 처리"""
        sensitive_headers = [
            'authorization', 'cookie', 'x-csrf-token', 'x-api-key',
            'x-auth-token', 'authentication', 'proxy-authorization'
        ]
        
        safe_headers = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                safe_headers[key] = '***MASKED***'
            else:
                safe_headers[key] = value
        
        return safe_headers
    
    def _sanitize_request_body(self, body):
        """요청 본문에서 민감한 정보를 마스킹 처리"""
        import re
        
        # 민감한 필드들
        sensitive_fields = [
            'password', 'passwd', 'pwd', 'token', 'secret', 'key',
            'api_key', 'access_token', 'refresh_token', 'csrf_token',
            'credit_card', 'ssn', 'social_security'
        ]
        
        sanitized_body = body
        
        # JSON 형태의 민감한 필드 마스킹
        for field in sensitive_fields:
            # "field": "value" 형태 매칭
            pattern = rf'"{field}"\s*:\s*"[^"]*"'
            sanitized_body = re.sub(pattern, f'"{field}": "***MASKED***"', sanitized_body, flags=re.IGNORECASE)
            
            # 'field': 'value' 형태 매칭
            pattern = rf"'{field}'\s*:\s*'[^']*'"
            sanitized_body = re.sub(pattern, f"'{field}': '***MASKED***'", sanitized_body, flags=re.IGNORECASE)
            
            # form data 형태 매칭
            pattern = rf'{field}=[^&\s]*'
            sanitized_body = re.sub(pattern, f'{field}=***MASKED***', sanitized_body, flags=re.IGNORECASE)
        
        return sanitized_body

    def process_exception(self, request, exception):
        """예외 처리 로깅"""
        if request.path.startswith('/api/'):
            logger.error(f"[API] 예외 발생 - {request.method} {request.path} - 오류: {str(exception)}", exc_info=True)
        return None 

class PerformanceMiddleware:
    """
    성능 모니터링을 위한 미들웨어
    - 요청 처리 시간 측정
    - 메모리 사용량 모니터링
    - 성능 지표 수집
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("[PerformanceMiddleware] 성능 모니터링 미들웨어 초기화 완료")

    def __call__(self, request):
        # 요청 시작 시간
        start_time = time.time()
        
        # 메모리 사용량 측정 (시작) - psutil 필요시 주석 해제
        # import psutil
        # process = psutil.Process()
        # start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        response = self.get_response(request)
        
        # 요청 처리 시간
        end_time = time.time()
        duration = end_time - start_time
        
        # 메모리 사용량 측정 (종료) - psutil 필요시 주석 해제
        # end_memory = process.memory_info().rss / 1024 / 1024  # MB
        # memory_diff = end_memory - start_memory
        memory_diff = 0  # psutil 없을 때 기본값
        
        # 성능 지표 로깅
        if request.path.startswith('/api/'):
            logger.info(f"[Performance] {request.method} {request.path} - 처리시간: {duration:.3f}초, 메모리변화: {memory_diff:+.2f}MB")
        
        # 성능 헤더 추가
        response['X-Response-Time'] = f"{duration:.3f}s"
        # response['X-Memory-Usage'] = f"{end_memory:.2f}MB"  # psutil 없을 때 주석
        
        return response

    def process_exception(self, request, exception):
        """예외 발생 시 성능 정보 로깅"""
        if request.path.startswith('/api/'):
            logger.error(f"[Performance] 예외 발생 - {request.method} {request.path} - 오류: {str(exception)}")
        return None 
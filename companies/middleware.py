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
            safe_headers = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie']}
            logger.info(f"[{request_id}] 요청 헤더: {json.dumps(safe_headers, default=str, ensure_ascii=False)}")
            
            # POST/PUT/PATCH 요청의 경우 본문 로깅 (민감한 정보 제외)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = request.body.decode('utf-8')
                    # 비밀번호 필드 제거
                    if 'password' in body.lower():
                        body = body.replace('"password":"', '"password":"***"')
                    logger.info(f"[{request_id}] 요청 본문: {body}")
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

    def process_exception(self, request, exception):
        """예외 처리 로깅"""
        if request.path.startswith('/api/'):
            logger.error(f"[API] 예외 발생 - {request.method} {request.path} - 오류: {str(exception)}", exc_info=True)
        return None 
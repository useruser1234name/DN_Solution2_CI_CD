# -*- coding: utf-8 -*-
"""
사용자 정의 예외 처리 핸들러
"""
import logging
import traceback
from typing import Optional, Dict, Any

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, DatabaseError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException, AuthenticationFailed, NotAuthenticated,
    PermissionDenied as DRFPermissionDenied
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    """
    DRF의 기본 예외 처리를 확장하여 더 상세한 에러 정보를 제공합니다.
    
    Args:
        exc: 발생한 예외
        context: 예외 발생 컨텍스트 (view, request 등)
        
    Returns:
        Response 객체 또는 None
    """
    # DRF 기본 예외 처리 먼저 실행
    response = exception_handler(exc, context)
    
    # 요청 정보 추출
    request = context.get('request')
    view = context.get('view')
    
    # 에러 로깅을 위한 정보 구성
    error_info = {
        'exception_type': type(exc).__name__,
        'exception_message': str(exc),
        'view': view.__class__.__name__ if view else None,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user': str(request.user) if request and hasattr(request, 'user') else None,
    }
    
    # Django 예외 처리
    if isinstance(exc, Http404):
        error_code = 'NOT_FOUND'
        error_message = '요청한 리소스를 찾을 수 없습니다.'
        status_code = status.HTTP_404_NOT_FOUND
        
    elif isinstance(exc, ValidationError):
        error_code = 'VALIDATION_ERROR'
        error_message = '입력 데이터가 유효하지 않습니다.'
        status_code = status.HTTP_400_BAD_REQUEST
        error_info['validation_errors'] = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        
    elif isinstance(exc, IntegrityError):
        error_code = 'DATA_INTEGRITY_ERROR'
        error_message = '데이터 무결성 제약 조건을 위반했습니다.'
        status_code = status.HTTP_409_CONFLICT
        logger.error(f"IntegrityError: {exc}", extra=error_info, exc_info=True)
        
    elif isinstance(exc, DatabaseError):
        error_code = 'DATABASE_ERROR'
        error_message = '데이터베이스 처리 중 오류가 발생했습니다.'
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logger.critical(f"DatabaseError: {exc}", extra=error_info, exc_info=True)
        
    elif isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
        error_code = 'PERMISSION_DENIED'
        error_message = '이 작업을 수행할 권한이 없습니다.'
        status_code = status.HTTP_403_FORBIDDEN
        
    elif isinstance(exc, NotAuthenticated):
        error_code = 'NOT_AUTHENTICATED'
        error_message = '인증이 필요합니다.'
        status_code = status.HTTP_401_UNAUTHORIZED
        
    elif isinstance(exc, AuthenticationFailed):
        error_code = 'AUTHENTICATION_FAILED'
        error_message = '인증에 실패했습니다.'
        status_code = status.HTTP_401_UNAUTHORIZED
        
    elif isinstance(exc, APIException):
        # DRF APIException 처리
        error_code = exc.default_code if hasattr(exc, 'default_code') else 'API_ERROR'
        error_message = exc.detail if hasattr(exc, 'detail') else str(exc)
        status_code = exc.status_code if hasattr(exc, 'status_code') else status.HTTP_400_BAD_REQUEST
        
    elif response is not None:
        # DRF가 처리한 예외
        return response
        
    else:
        # 처리되지 않은 예외
        error_code = 'INTERNAL_SERVER_ERROR'
        error_message = '서버 내부 오류가 발생했습니다.'
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # 심각한 오류는 상세 로깅
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                **error_info,
                'traceback': traceback.format_exc()
            },
            exc_info=True
        )
    
    # 개발 환경에서는 더 상세한 정보 제공
    from django.conf import settings
    if settings.DEBUG:
        error_data = {
            'error': {
                'code': error_code,
                'message': error_message,
                'detail': str(exc),
                'type': type(exc).__name__,
                'path': request.path if request else None,
                'method': request.method if request else None,
            }
        }
        
        # ValidationError의 경우 상세 정보 추가
        if hasattr(exc, 'message_dict'):
            error_data['error']['validation_errors'] = exc.message_dict
    else:
        # 프로덕션 환경에서는 민감한 정보 제거
        error_data = {
            'error': {
                'code': error_code,
                'message': error_message,
            }
        }
    
    return Response(error_data, status=status_code)


class BusinessLogicException(APIException):
    """비즈니스 로직 예외"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '비즈니스 규칙 위반입니다.'
    default_code = 'business_logic_error'


class ResourceNotFoundException(APIException):
    """리소스를 찾을 수 없음"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '요청한 리소스를 찾을 수 없습니다.'
    default_code = 'resource_not_found'


class ConflictException(APIException):
    """리소스 충돌"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = '리소스 충돌이 발생했습니다.'
    default_code = 'conflict'


class ExternalServiceException(APIException):
    """외부 서비스 오류"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = '외부 서비스가 일시적으로 이용 불가능합니다.'
    default_code = 'external_service_error'
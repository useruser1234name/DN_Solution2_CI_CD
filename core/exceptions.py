"""
커스텀 예외 클래스
프로젝트 전반에서 사용할 예외 정의
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class BusinessLogicException(APIException):
    """비즈니스 로직 예외 기본 클래스"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '비즈니스 로직 오류가 발생했습니다.'
    default_code = 'business_logic_error'


class HierarchyException(BusinessLogicException):
    """계층 구조 관련 예외"""
    default_detail = '계층 구조 규칙을 위반했습니다.'
    default_code = 'hierarchy_violation'


class CompanyNotFoundException(BusinessLogicException):
    """회사를 찾을 수 없는 경우"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '회사를 찾을 수 없습니다.'
    default_code = 'company_not_found'


class InvalidCompanyTypeException(BusinessLogicException):
    """잘못된 회사 타입"""
    default_detail = '잘못된 회사 타입입니다.'
    default_code = 'invalid_company_type'


class PermissionDeniedException(APIException):
    """권한 거부"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = '이 작업을 수행할 권한이 없습니다.'
    default_code = 'permission_denied'


class PolicyException(BusinessLogicException):
    """정책 관련 예외"""
    default_detail = '정책 처리 중 오류가 발생했습니다.'
    default_code = 'policy_error'


class PolicyNotFoundException(PolicyException):
    """정책을 찾을 수 없는 경우"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '정책을 찾을 수 없습니다.'
    default_code = 'policy_not_found'


class PolicyAssignmentException(PolicyException):
    """정책 배정 관련 예외"""
    default_detail = '정책 배정 중 오류가 발생했습니다.'
    default_code = 'policy_assignment_error'


class OrderException(BusinessLogicException):
    """주문 관련 예외"""
    default_detail = '주문 처리 중 오류가 발생했습니다.'
    default_code = 'order_error'


class OrderNotFoundException(OrderException):
    """주문을 찾을 수 없는 경우"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '주문을 찾을 수 없습니다.'
    default_code = 'order_not_found'


class OrderStatusException(OrderException):
    """주문 상태 관련 예외"""
    default_detail = '주문 상태 변경이 불가능합니다.'
    default_code = 'order_status_error'


class InvalidOrderStatusTransition(OrderStatusException):
    """잘못된 주문 상태 전환"""
    default_detail = '현재 상태에서는 요청한 상태로 변경할 수 없습니다.'
    default_code = 'invalid_status_transition'


class OrderAlreadyApprovedException(OrderStatusException):
    """이미 승인된 주문"""
    default_detail = '이미 승인된 주문은 수정할 수 없습니다.'
    default_code = 'order_already_approved'


class SensitiveDataException(BusinessLogicException):
    """민감정보 처리 관련 예외"""
    default_detail = '민감정보 처리 중 오류가 발생했습니다.'
    default_code = 'sensitive_data_error'


class SensitiveDataNotFoundException(SensitiveDataException):
    """민감정보를 찾을 수 없는 경우"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '민감정보를 찾을 수 없습니다. TTL이 만료되었을 수 있습니다.'
    default_code = 'sensitive_data_not_found'


class RedisConnectionException(APIException):
    """Redis 연결 오류"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Redis 서버에 연결할 수 없습니다.'
    default_code = 'redis_connection_error'


class ValidationException(BusinessLogicException):
    """유효성 검증 실패"""
    default_detail = '입력값 검증에 실패했습니다.'
    default_code = 'validation_error'


class DuplicateException(BusinessLogicException):
    """중복 데이터 예외"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = '이미 존재하는 데이터입니다.'
    default_code = 'duplicate_error'


class RebateCalculationException(BusinessLogicException):
    """리베이트 계산 오류"""
    default_detail = '리베이트 계산 중 오류가 발생했습니다.'
    default_code = 'rebate_calculation_error'


class FormTemplateException(BusinessLogicException):
    """폼 템플릿 관련 예외"""
    default_detail = '주문서 양식 처리 중 오류가 발생했습니다.'
    default_code = 'form_template_error'


class InvalidFormDataException(FormTemplateException):
    """잘못된 폼 데이터"""
    default_detail = '주문서 데이터가 양식과 일치하지 않습니다.'
    default_code = 'invalid_form_data'


class SettlementException(BusinessLogicException):
    """정산 관련 예외"""
    default_detail = '정산 처리 중 오류가 발생했습니다.'
    default_code = 'settlement_error'


class InsufficientBalanceException(SettlementException):
    """잔액 부족"""
    default_detail = '정산을 위한 잔액이 부족합니다.'
    default_code = 'insufficient_balance'


class AuthenticationException(APIException):
    """인증 관련 예외"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = '인증에 실패했습니다.'
    default_code = 'authentication_failed'


class TokenExpiredException(AuthenticationException):
    """토큰 만료"""
    default_detail = '토큰이 만료되었습니다. 다시 로그인해주세요.'
    default_code = 'token_expired'


class InvalidTokenException(AuthenticationException):
    """잘못된 토큰"""
    default_detail = '유효하지 않은 토큰입니다.'
    default_code = 'invalid_token'


# 예외 처리 유틸리티 함수
def handle_business_exception(exc: Exception, context: dict = None) -> dict:
    """
    비즈니스 예외를 일관된 형식으로 처리
    
    Args:
        exc: 발생한 예외
        context: 추가 컨텍스트 정보
        
    Returns:
        에러 응답 딕셔너리
    """
    error_response = {
        'success': False,
        'error': {
            'code': getattr(exc, 'default_code', 'unknown_error'),
            'message': str(exc),
            'type': exc.__class__.__name__
        }
    }
    
    if context:
        error_response['error']['context'] = context
        
    return error_response
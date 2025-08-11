# -*- coding: utf-8 -*-
"""
재사용 가능한 베이스 뷰 클래스와 믹스인
"""
import logging
from typing import Any, Dict, Optional

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from companies.models import CompanyUser

logger = logging.getLogger(__name__)


class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""
    
    def log_action(self, action: str, message: str, level: str = 'INFO', **kwargs):
        """
        액션 로깅
        
        Args:
            action: 수행된 액션
            message: 로그 메시지
            level: 로그 레벨
            **kwargs: 추가 컨텍스트 정보
        """
        log_data = {
            'action': action,
            'user': str(self.request.user) if hasattr(self, 'request') else 'system',
            'ip_address': self.get_client_ip() if hasattr(self, 'get_client_ip') else None,
            **kwargs
        }
        
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, extra=log_data)
    
    def get_client_ip(self) -> Optional[str]:
        """클라이언트 IP 주소 추출"""
        if not hasattr(self, 'request'):
            return None
            
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')


class CompanyContextMixin:
    """회사 컨텍스트를 제공하는 믹스인"""
    
    def get_company_user(self) -> Optional[CompanyUser]:
        """현재 사용자의 CompanyUser 객체 반환"""
        if not hasattr(self, 'request') or not self.request.user.is_authenticated:
            return None
        
        try:
            return CompanyUser.objects.select_related('company').get(
                django_user=self.request.user
            )
        except CompanyUser.DoesNotExist:
            logger.warning(f"CompanyUser not found for user: {self.request.user}")
            return None
    
    def get_company(self):
        """현재 사용자의 회사 반환"""
        company_user = self.get_company_user()
        return company_user.company if company_user else None
    
    def check_company_permission(self, target_company, action: str = 'view') -> bool:
        """
        회사 권한 체크
        
        Args:
            target_company: 대상 회사
            action: 수행할 액션 ('view', 'edit', 'delete')
            
        Returns:
            권한 여부
        """
        company_user = self.get_company_user()
        if not company_user:
            return False
        
        user_company = company_user.company
        
        # 본사는 모든 권한
        if user_company.type == 'headquarters':
            return True
        
        # 자기 회사는 항상 조회 가능
        if action == 'view' and target_company.id == user_company.id:
            return True
        
        # 대리점은 하위 소매점만 관리
        if user_company.type == 'agency':
            if action in ['view', 'edit']:
                return target_company.parent_company_id == user_company.id
        
        # 소매점은 자기 회사만 조회
        if user_company.type == 'retail':
            return action == 'view' and target_company.id == user_company.id
        
        return False


class ErrorHandlingMixin:
    """에러 처리를 위한 믹스인"""
    
    def handle_error(self, exc: Exception, message: str = None, 
                    log_level: str = 'ERROR') -> Response:
        """
        예외를 처리하고 적절한 응답 반환
        
        Args:
            exc: 발생한 예외
            message: 사용자에게 보여줄 메시지
            log_level: 로그 레벨
            
        Returns:
            에러 응답
        """
        if isinstance(exc, ValidationError):
            error_detail = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
            logger.warning(f"Validation error: {error_detail}")
            return Response(
                {'error': message or '입력 데이터가 유효하지 않습니다.', 'detail': error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        elif isinstance(exc, IntegrityError):
            logger.error(f"Integrity error: {exc}", exc_info=True)
            return Response(
                {'error': message or '데이터 무결성 오류가 발생했습니다.'},
                status=status.HTTP_409_CONFLICT
            )
        
        else:
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            return Response(
                {'error': message or '서버 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def safe_transaction(self, func, *args, **kwargs):
        """
        트랜잭션 내에서 안전하게 함수 실행
        
        Args:
            func: 실행할 함수
            *args, **kwargs: 함수 인자
            
        Returns:
            함수 실행 결과 또는 에러 응답
        """
        try:
            with transaction.atomic():
                return func(*args, **kwargs)
        except Exception as e:
            return self.handle_error(e)


class BaseModelViewSet(ModelViewSet, LoggingMixin, CompanyContextMixin, ErrorHandlingMixin):
    """기본 ModelViewSet with 공통 기능"""
    
    def perform_create(self, serializer):
        """생성 시 로깅"""
        instance = serializer.save()
        self.log_action(
            'create',
            f"Created {self.get_queryset().model.__name__}: {instance}",
            object_id=str(instance.pk)
        )
        return instance
    
    def perform_update(self, serializer):
        """수정 시 로깅"""
        instance = serializer.save()
        self.log_action(
            'update',
            f"Updated {self.get_queryset().model.__name__}: {instance}",
            object_id=str(instance.pk)
        )
        return instance
    
    def perform_destroy(self, instance):
        """삭제 시 로깅"""
        model_name = self.get_queryset().model.__name__
        instance_id = str(instance.pk)
        instance.delete()
        self.log_action(
            'delete',
            f"Deleted {model_name}: {instance_id}",
            object_id=instance_id
        )


class PaginationMixin:
    """페이지네이션 헬퍼 믹스인"""
    
    def get_paginated_data(self, queryset, serializer_class=None):
        """
        페이지네이션된 데이터 반환
        
        Args:
            queryset: 쿼리셋
            serializer_class: 시리얼라이저 클래스
            
        Returns:
            페이지네이션된 응답 데이터
        """
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = (serializer_class or self.get_serializer_class())(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = (serializer_class or self.get_serializer_class())(
            queryset, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)


class CachedViewMixin:
    """캐시 관련 믹스인"""
    
    cache_timeout = 300  # 기본 5분
    cache_key_prefix = None
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """캐시 키 생성"""
        prefix = self.cache_key_prefix or self.__class__.__name__
        key_parts = [prefix]
        
        # 사용자별 캐시
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            key_parts.append(f"user_{self.request.user.id}")
        
        # 추가 인자로 키 구성
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}_{v}" for k, v in kwargs.items())
        
        return ":".join(key_parts)
    
    def get_cached_or_compute(self, cache_key: str, compute_func, timeout=None):
        """
        캐시에서 가져오거나 계산 후 캐시
        
        Args:
            cache_key: 캐시 키
            compute_func: 데이터 계산 함수
            timeout: 캐시 타임아웃
            
        Returns:
            캐시된 또는 계산된 데이터
        """
        from django.core.cache import cache
        
        data = cache.get(cache_key)
        if data is None:
            data = compute_func()
            cache.set(cache_key, data, timeout or self.cache_timeout)
            logger.debug(f"Cache miss and set: {cache_key}")
        else:
            logger.debug(f"Cache hit: {cache_key}")
        
        return data
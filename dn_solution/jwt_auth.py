# -*- coding: utf-8 -*-
"""
JWT Authentication System - DN_SOLUTION2 리모델링
개선된 JWT 인증 시스템
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
# from dn_solution.cache_manager import cache_manager, CacheManager - removed
from dn_solution.cache_manager import cache_manager, CacheManager

User = get_user_model()
logger = logging.getLogger(__name__)


class EnhancedJWTAuthentication(JWTAuthentication):
    """개선된 JWT 인증 클래스"""
    
    def authenticate(self, request):
        """JWT 토큰 인증 (캐시 및 보안 강화)"""
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        # 토큰 블랙리스트 확인 (캐시 사용)
        if self.is_token_blacklisted(raw_token):
            raise InvalidToken('토큰이 블랙리스트에 등록되어 있습니다.')

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        # 사용자 상태 및 권한 확인
        if not self.is_user_valid(user, validated_token):
            raise InvalidToken('사용자 인증에 실패했습니다.')
        
        # 토큰 사용 기록 (보안 로깅)
        self.log_token_usage(user, validated_token, request)
        
        return user, validated_token
    
    def is_token_blacklisted(self, raw_token: bytes) -> bool:
        """토큰 블랙리스트 확인 (캐시 활용)"""
        try:
            token_str = raw_token.decode()
            cache_key = f"blacklisted_token:{hash(token_str)}"
            
            # 캐시에서 블랙리스트 확인
            is_blacklisted = cache_manager.get(cache_key)
            if is_blacklisted is not None:
                return is_blacklisted
            
            # DB에서 블랙리스트 확인 (실제 구현에서는 DB 모델 사용)
            # 예: BlacklistedToken.objects.filter(token=token_str).exists()
            is_blacklisted = False  # 실제 DB 조회로 대체
            
            # 결과를 캐시에 저장
            cache_manager.set(cache_key, is_blacklisted, CacheManager.CACHE_TIMEOUTS['medium'])
            
            return is_blacklisted
            
        except Exception as e:
            logger.error(f"블랙리스트 확인 실패: {e}")
            return False
    
    def is_user_valid(self, user, token) -> bool:
        """사용자 유효성 검사"""
        if not user or not user.is_active:
            return False
        
        # 추가 보안 검사
        # 1. 사용자 계정 상태 확인
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            if company_user.status not in ['approved', 'active']:
                return False
        
        # 2. 토큰 발급 시점과 사용자 정보 변경 시점 비교
        token_iat = token.get('iat')
        if token_iat:
            token_issued_at = datetime.fromtimestamp(token_iat, tz=timezone.utc)
            # 사용자 정보가 토큰 발급 이후에 변경되었는지 확인
            if hasattr(user, 'profile_updated_at') and user.profile_updated_at > token_issued_at:
                return False
        
        return True
    
    def log_token_usage(self, user, token, request):
        """토큰 사용 기록 (보안 모니터링)"""
        try:
            usage_info = {
                'user_id': user.id,
                'username': user.username,
                'token_jti': token.get('jti'),
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat(),
                'endpoint': request.path,
                'method': request.method,
            }
            
            # 보안 로깅
            logger.info(f"JWT 토큰 사용: {usage_info}")
            
            # 비정상적인 접근 패턴 탐지 (선택적)
            self.detect_suspicious_activity(user, usage_info)
            
        except Exception as e:
            logger.error(f"토큰 사용 기록 실패: {e}")
    
    def get_client_ip(self, request) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    def detect_suspicious_activity(self, user, usage_info):
        """비정상적인 활동 탐지"""
        try:
            cache_key = f"token_usage:{user.id}:recent"
            recent_usages = cache_manager.get(cache_key, [])
            
            # 최근 사용 기록에 추가
            recent_usages.append(usage_info)
            
            # 최근 10분간의 기록만 유지
            cutoff_time = timezone.now() - timedelta(minutes=10)
            recent_usages = [
                usage for usage in recent_usages
                if datetime.fromisoformat(usage['timestamp'].replace('Z', '+00:00')) > cutoff_time
            ]
            
            # 비정상 패턴 확인
            if len(recent_usages) > 100:  # 10분간 100회 이상 요청
                logger.warning(f"높은 빈도의 토큰 사용 탐지: 사용자 {user.username}")
            
            # 다중 IP 사용 확인
            unique_ips = set(usage['ip_address'] for usage in recent_usages[-10:])
            if len(unique_ips) > 3:  # 최근 10개 요청에서 3개 이상의 IP
                logger.warning(f"다중 IP 사용 탐지: 사용자 {user.username}, IPs: {unique_ips}")
            
            # 캐시에 저장
            cache_manager.set(cache_key, recent_usages, 600)  # 10분
            
        except Exception as e:
            logger.error(f"비정상 활동 탐지 실패: {e}")


class CustomTokenGenerator:
    """커스텀 JWT 토큰 생성기"""
    
    @staticmethod
    def generate_tokens(user) -> Tuple[str, str]:
        """사용자용 JWT 토큰 생성 (액세스 + 리프레시)"""
        try:
            refresh = RefreshToken.for_user(user)
            
            # 추가 클레임 설정
            refresh['user_type'] = 'company_user'
            if hasattr(user, 'companyuser'):
                company_user = user.companyuser
                refresh['company_id'] = str(company_user.company.id)  # UUID를 문자열로 변환
                refresh['company_code'] = company_user.company.code
                refresh['company_type'] = company_user.company.type
                refresh['role'] = company_user.role
                refresh['is_primary_admin'] = getattr(company_user, 'is_primary_admin', False)
            
            access_token = refresh.access_token
            
            # 액세스 토큰에도 동일한 클레임 추가
            for key, value in refresh.payload.items():
                if key not in ['token_type', 'exp', 'iat', 'jti']:
                    access_token[key] = value
            
            return str(access_token), str(refresh)
            
        except Exception as e:
            logger.error(f"토큰 생성 실패: {e}")
            raise TokenError("토큰 생성에 실패했습니다.")
    
    @staticmethod
    def generate_api_token(user, scopes: list = None, expires_in: int = 3600) -> str:
        """API 전용 토큰 생성"""
        try:
            now = timezone.now()
            payload = {
                'user_id': user.id,
                'username': user.username,
                'token_type': 'api',
                'scopes': scopes or ['read'],
                'iat': now.timestamp(),
                'exp': (now + timedelta(seconds=expires_in)).timestamp(),
                'jti': f"api_{user.id}_{now.timestamp()}",
            }
            
            if hasattr(user, 'companyuser'):
                payload['company_id'] = str(user.companyuser.company.id)  # UUID를 문자열로 변환
                payload['company_type'] = user.companyuser.company.type
            
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            
            # API 토큰을 캐시에 저장 (추적용)
            cache_key = f"api_token:{payload['jti']}"
            cache_manager.set(cache_key, {
                'user_id': user.id,
                'created_at': now.isoformat(),
                'scopes': scopes,
            }, expires_in)
            
            return token
            
        except Exception as e:
            logger.error(f"API 토큰 생성 실패: {e}")
            raise TokenError("API 토큰 생성에 실패했습니다.")


class TokenManager:
    """JWT 토큰 관리 클래스"""
    
    @staticmethod
    def blacklist_token(token: str) -> bool:
        """토큰을 블랙리스트에 추가"""
        try:
            # 토큰 디코딩 및 검증
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            jti = decoded_token.get('jti')
            exp = decoded_token.get('exp')
            
            if not jti or not exp:
                return False
            
            # 만료 시간까지 블랙리스트에 유지
            expiry_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            remaining_time = (expiry_datetime - timezone.now()).total_seconds()
            
            if remaining_time > 0:
                cache_key = f"blacklisted_token:{hash(token)}"
                cache_manager.set(cache_key, True, int(remaining_time))
                
                # JTI 기반 블랙리스트도 설정
                jti_cache_key = f"blacklisted_jti:{jti}"
                cache_manager.set(jti_cache_key, True, int(remaining_time))
                
                logger.info(f"토큰 블랙리스트 추가: JTI={jti}")
                return True
            
            return False
            
        except jwt.ExpiredSignatureError:
            # 이미 만료된 토큰
            return True
        except Exception as e:
            logger.error(f"토큰 블랙리스트 추가 실패: {e}")
            return False
    
    @staticmethod
    def revoke_user_tokens(user) -> int:
        """사용자의 모든 토큰 무효화"""
        try:
            # 사용자의 모든 refresh 토큰 무효화 (DB에서)
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            
            blacklisted_count = 0
            for token in outstanding_tokens:
                if TokenManager.blacklist_token(str(token.token)):
                    blacklisted_count += 1
            
            # 캐시에서 사용자 관련 토큰 정보 삭제
            cache_manager.delete_pattern(f'token_usage:{user.id}:*')
            cache_manager.delete_pattern(f'api_token:*user_{user.id}*')
            
            logger.info(f"사용자 {user.username}의 토큰 {blacklisted_count}개 무효화")
            return blacklisted_count
            
        except Exception as e:
            logger.error(f"사용자 토큰 무효화 실패: {e}")
            return 0
    
    @staticmethod
    def get_token_info(token: str) -> Dict[str, Any]:
        """토큰 정보 조회"""
        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            return {
                'user_id': decoded_token.get('user_id'),
                'username': decoded_token.get('username'),
                'company_id': decoded_token.get('company_id'),
                'company_type': decoded_token.get('company_type'),
                'role': decoded_token.get('role'),
                'token_type': decoded_token.get('token_type'),
                'issued_at': datetime.fromtimestamp(decoded_token.get('iat', 0)),
                'expires_at': datetime.fromtimestamp(decoded_token.get('exp', 0)),
                'jti': decoded_token.get('jti'),
            }
            
        except jwt.ExpiredSignatureError:
            raise TokenError("토큰이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise TokenError("유효하지 않은 토큰입니다.")
        except Exception as e:
            logger.error(f"토큰 정보 조회 실패: {e}")
            raise TokenError("토큰 정보를 조회할 수 없습니다.")


class TokenPermissionValidator:
    """토큰 권한 검증 클래스"""
    
    @staticmethod
    def validate_company_access(token_info: Dict[str, Any], target_company_id: int) -> bool:
        """회사 접근 권한 검증"""
        try:
            user_company_id = token_info.get('company_id')
            company_type = token_info.get('company_type')
            
            if not user_company_id:
                return False
            
            # 동일한 회사인 경우 허용
            if user_company_id == target_company_id:
                return True
            
            # 본부는 모든 회사에 접근 가능
            if company_type == 'headquarters':
                return True
            
            # 대리점은 하위 소매점에만 접근 가능
            if company_type == 'agency':
                # 실제 구현에서는 DB에서 계층 구조 확인
                return TokenPermissionValidator._is_subordinate_company(user_company_id, target_company_id)
            
            return False
            
        except Exception as e:
            logger.error(f"회사 접근 권한 검증 실패: {e}")
            return False
    
    @staticmethod
    def _is_subordinate_company(parent_company_id: int, child_company_id: int) -> bool:
        """하위 회사 관계 확인"""
        # 실제 구현에서는 Company 모델에서 parent_company 관계 확인
        # 캐시를 활용하여 성능 최적화
        cache_key = f"company_hierarchy:{parent_company_id}:children"
        subordinate_ids = cache_manager.get(cache_key)
        
        if subordinate_ids is None:
            # DB에서 조회 후 캐시에 저장
            # subordinate_ids = Company.objects.filter(parent_company_id=parent_company_id).values_list('id', flat=True)
            subordinate_ids = []  # 실제 구현으로 대체
            cache_manager.set(cache_key, list(subordinate_ids), CacheManager.CACHE_TIMEOUTS['long'])
        
        return child_company_id in subordinate_ids
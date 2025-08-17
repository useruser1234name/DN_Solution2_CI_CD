"""
Company 앱 보안 설정 및 유틸리티

JWT 토큰 보안, 민감정보 처리 등 보안 관련 기능을 제공합니다.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User


class SecurityConfig:
    """보안 설정 클래스"""
    
    # JWT 토큰 설정
    JWT_ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
    JWT_REFRESH_TOKEN_LIFETIME = timedelta(days=7)
    JWT_ROTATE_REFRESH_TOKENS = True
    JWT_BLACKLIST_AFTER_ROTATION = True
    
    # 비밀번호 정책
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL_CHARS = True
    
    # 로그인 시도 제한
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATION = timedelta(minutes=30)
    
    # 세션 보안
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'


class TokenSecurityManager:
    """JWT 토큰 보안 관리 클래스"""
    
    @staticmethod
    def generate_secure_key() -> str:
        """안전한 키 생성"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_token_fingerprint(token: str, user_agent: str, ip_address: str) -> str:
        """토큰 지문 생성 (토큰 탈취 방지)"""
        data = f"{token}:{user_agent}:{ip_address}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def is_token_valid_for_request(token: str, request) -> bool:
        """요청에 대한 토큰 유효성 검증"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        expected_fingerprint = TokenSecurityManager.create_token_fingerprint(
            token, user_agent, ip_address
        )
        
        # 캐시에서 저장된 지문과 비교
        cache_key = f"token_fingerprint:{hashlib.md5(token.encode()).hexdigest()}"
        stored_fingerprint = cache.get(cache_key)
        
        return stored_fingerprint == expected_fingerprint
    
    @staticmethod
    def store_token_fingerprint(token: str, request, lifetime: timedelta):
        """토큰 지문 저장"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        fingerprint = TokenSecurityManager.create_token_fingerprint(
            token, user_agent, ip_address
        )
        
        cache_key = f"token_fingerprint:{hashlib.md5(token.encode()).hexdigest()}"
        cache.set(cache_key, fingerprint, timeout=int(lifetime.total_seconds()))


class LoginAttemptManager:
    """로그인 시도 관리 클래스"""
    
    @staticmethod
    def get_cache_key(identifier: str) -> str:
        """캐시 키 생성"""
        return f"login_attempts:{identifier}"
    
    @staticmethod
    def record_failed_attempt(identifier: str) -> None:
        """실패한 로그인 시도 기록"""
        cache_key = LoginAttemptManager.get_cache_key(identifier)
        current_attempts = cache.get(cache_key, 0)
        cache.set(
            cache_key, 
            current_attempts + 1, 
            timeout=int(SecurityConfig.LOGIN_LOCKOUT_DURATION.total_seconds())
        )
    
    @staticmethod
    def clear_failed_attempts(identifier: str) -> None:
        """실패한 로그인 시도 기록 삭제"""
        cache_key = LoginAttemptManager.get_cache_key(identifier)
        cache.delete(cache_key)
    
    @staticmethod
    def is_locked_out(identifier: str) -> bool:
        """계정 잠금 상태 확인"""
        cache_key = LoginAttemptManager.get_cache_key(identifier)
        attempts = cache.get(cache_key, 0)
        return attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS
    
    @staticmethod
    def get_remaining_attempts(identifier: str) -> int:
        """남은 시도 횟수 반환"""
        cache_key = LoginAttemptManager.get_cache_key(identifier)
        attempts = cache.get(cache_key, 0)
        return max(0, SecurityConfig.MAX_LOGIN_ATTEMPTS - attempts)


class PasswordValidator:
    """비밀번호 유효성 검증 클래스"""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """
        비밀번호 유효성 검증
        
        Returns:
            Dict: 검증 결과와 메시지
        """
        errors = []
        
        # 길이 검증
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            errors.append(f"비밀번호는 최소 {SecurityConfig.PASSWORD_MIN_LENGTH}자 이상이어야 합니다.")
        
        # 대문자 검증
        if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("비밀번호에 대문자가 포함되어야 합니다.")
        
        # 소문자 검증
        if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("비밀번호에 소문자가 포함되어야 합니다.")
        
        # 숫자 검증
        if SecurityConfig.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("비밀번호에 숫자가 포함되어야 합니다.")
        
        # 특수문자 검증
        if SecurityConfig.PASSWORD_REQUIRE_SPECIAL_CHARS:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("비밀번호에 특수문자가 포함되어야 합니다.")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """안전한 비밀번호 생성"""
        import string
        
        # 각 카테고리에서 최소 1개씩 포함
        lowercase = secrets.choice(string.ascii_lowercase)
        uppercase = secrets.choice(string.ascii_uppercase)
        digit = secrets.choice(string.digits)
        special = secrets.choice("!@#$%^&*")
        
        # 나머지 길이만큼 랜덤 선택
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        remaining = ''.join(secrets.choice(all_chars) for _ in range(length - 4))
        
        # 섞기
        password_list = list(lowercase + uppercase + digit + special + remaining)
        secrets.SystemRandom().shuffle(password_list)
        
        return ''.join(password_list)


class DataMasker:
    """민감 정보 마스킹 유틸리티"""
    
    SENSITIVE_FIELDS = [
        'password', 'passwd', 'pwd', 'token', 'secret', 'key',
        'api_key', 'access_token', 'refresh_token', 'csrf_token',
        'credit_card', 'ssn', 'social_security', 'phone', 'email'
    ]
    
    @staticmethod
    def mask_string(value: str, show_chars: int = 3) -> str:
        """문자열 마스킹"""
        if len(value) <= show_chars * 2:
            return '*' * len(value)
        
        return value[:show_chars] + '*' * (len(value) - show_chars * 2) + value[-show_chars:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """이메일 마스킹"""
        if '@' not in email:
            return DataMasker.mask_string(email)
        
        local, domain = email.split('@', 1)
        # 로컬 부분의 첫 글자는 유지, 나머지는 마스킹
        if len(local) > 1:
            masked_local = local[0] + '*' * (len(local) - 1)
        else:
            masked_local = 'u*'  # 로컬 부분이 한 글자인 경우
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """전화번호 마스킹"""
        # 숫자만 추출
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) >= 8:
            return phone.replace(digits[3:-4], '*' * (len(digits) - 7))
        return DataMasker.mask_string(phone)
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """딕셔너리에서 민감한 데이터 마스킹"""
        masked_data = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                masked_data[key] = DataMasker.mask_sensitive_data(value)
            elif isinstance(value, str):
                if key.lower() in DataMasker.SENSITIVE_FIELDS:
                    if 'email' in key.lower():
                        masked_data[key] = DataMasker.mask_email(value)
                    elif 'phone' in key.lower():
                        masked_data[key] = DataMasker.mask_phone(value)
                    else:
                        masked_data[key] = '***MASKED***'
                else:
                    masked_data[key] = value
            else:
                masked_data[key] = value
        
        return masked_data


class SecurityAuditLogger:
    """보안 감사 로그 클래스"""
    
    @staticmethod
    def log_login_attempt(username: str, ip_address: str, success: bool, reason: str = None):
        """로그인 시도 로깅"""
        import logging
        
        logger = logging.getLogger('security')
        
        status = "성공" if success else "실패"
        log_data = {
            'event': 'login_attempt',
            'username': username,
            'ip_address': ip_address,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if not success and reason:
            log_data['reason'] = reason
        
        if success:
            logger.info(f"로그인 성공 - 사용자: {username}, IP: {ip_address}")
        else:
            logger.warning(f"로그인 실패 - 사용자: {username}, IP: {ip_address}, 이유: {reason}")
    
    @staticmethod
    def log_permission_violation(user: User, action: str, resource: str, ip_address: str):
        """권한 위반 로깅"""
        import logging
        
        logger = logging.getLogger('security')
        logger.warning(
            f"권한 위반 - 사용자: {user.username}, 액션: {action}, "
            f"리소스: {resource}, IP: {ip_address}"
        )
    
    @staticmethod
    def log_suspicious_activity(description: str, user: Optional[User] = None, ip_address: str = None):
        """의심스러운 활동 로깅"""
        import logging
        
        logger = logging.getLogger('security')
        log_message = f"의심스러운 활동 - {description}"
        
        if user:
            log_message += f", 사용자: {user.username}"
        if ip_address:
            log_message += f", IP: {ip_address}"
        
        logger.error(log_message)

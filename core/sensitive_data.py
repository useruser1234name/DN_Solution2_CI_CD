"""
민감정보 처리 매니저
Redis를 사용한 임시 저장 및 해시화 처리
"""

import hashlib
import json
import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
import redis

logger = logging.getLogger(__name__)


class SensitiveDataManager:
    """
    민감정보 처리를 위한 매니저 클래스
    - Redis 임시 저장 (TTL 24시간)
    - 승인 시 해시화하여 DB 저장
    - 로그 마스킹
    """
    
    CACHE_PREFIX = "sensitive_data"
    DEFAULT_TTL = 86400  # 24시간
    HASH_ALGORITHM = 'sha256'
    
    def __init__(self):
        """Redis 연결 초기화"""
        try:
            # Redis URL에서 연결 정보 파싱
            from django_redis import get_redis_connection
            self.redis_client = get_redis_connection("default")
            self.redis_client.ping()
            logger.info("Redis 연결 성공")
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            self.redis_client = None
    
    def store_temporary(self, data: Dict[str, Any], key: str, ttl: int = None) -> bool:
        """
        민감정보를 Redis에 임시 저장
        
        Args:
            data: 저장할 민감정보 딕셔너리
            key: 저장 키
            ttl: Time To Live (초 단위, 기본값: 24시간)
            
        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            logger.error("Redis 클라이언트가 초기화되지 않았습니다.")
            return False
            
        ttl = ttl or self.DEFAULT_TTL
        cache_key = f"{self.CACHE_PREFIX}:{key}"
        
        try:
            # 민감정보 로깅 시 마스킹
            masked_data = self._mask_sensitive_fields(data.copy())
            logger.info(f"민감정보 임시 저장: {cache_key}, 데이터: {masked_data}")
            
            # JSON 직렬화 후 저장
            json_data = json.dumps(data)
            self.redis_client.setex(cache_key, ttl, json_data)
            
            # 메타데이터 저장
            meta_key = f"{cache_key}:meta"
            meta_data = {
                'created_at': timezone.now().isoformat(),
                'ttl': ttl,
                'fields': list(data.keys())
            }
            self.redis_client.setex(meta_key, ttl, json.dumps(meta_data))
            
            return True
            
        except Exception as e:
            logger.error(f"민감정보 저장 실패: {e}")
            return False
    
    def retrieve_temporary(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Redis에서 민감정보 조회
        
        Args:
            key: 조회할 키
            
        Returns:
            민감정보 딕셔너리 또는 None
        """
        if not self.redis_client:
            logger.error("Redis 클라이언트가 초기화되지 않았습니다.")
            return None
            
        cache_key = f"{self.CACHE_PREFIX}:{key}"
        
        try:
            json_data = self.redis_client.get(cache_key)
            if json_data:
                data = json.loads(json_data)
                logger.info(f"민감정보 조회 성공: {cache_key}")
                return data
            else:
                logger.warning(f"민감정보를 찾을 수 없음: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"민감정보 조회 실패: {e}")
            return None
    
    def delete_temporary(self, key: str) -> bool:
        """
        Redis에서 민감정보 삭제
        
        Args:
            key: 삭제할 키
            
        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            return False
            
        cache_key = f"{self.CACHE_PREFIX}:{key}"
        meta_key = f"{cache_key}:meta"
        
        try:
            self.redis_client.delete(cache_key, meta_key)
            logger.info(f"민감정보 삭제: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"민감정보 삭제 실패: {e}")
            return False
    
    def hash_and_store(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        민감정보를 해시화하여 저장 가능한 형태로 변환
        
        Args:
            data: 해시화할 민감정보
            
        Returns:
            해시화된 데이터
        """
        hashed_data = {}
        
        for field, value in data.items():
            if value and isinstance(value, str):
                # 솔트 추가하여 해시화
                salt = settings.SECRET_KEY[:16]
                hash_value = hashlib.sha256(
                    f"{salt}{value}".encode('utf-8')
                ).hexdigest()
                hashed_data[f"{field}_hash"] = hash_value
                
                # 마스킹된 원본도 저장 (표시용)
                hashed_data[f"{field}_masked"] = self._mask_value(value, field)
            else:
                hashed_data[field] = value
        
        logger.info(f"민감정보 해시화 완료: {list(hashed_data.keys())}")
        return hashed_data
    
    def mask_for_logging(self, data: Any) -> Any:
        """
        로그용 데이터 마스킹
        
        Args:
            data: 마스킹할 데이터
            
        Returns:
            마스킹된 데이터
        """
        if isinstance(data, dict):
            return self._mask_sensitive_fields(data.copy())
        elif isinstance(data, str):
            return self._mask_value(data)
        else:
            return data
    
    def _mask_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """민감한 필드들을 마스킹"""
        sensitive_fields = [
            'customer_name', 'name', '고객명',
            'phone', 'phone_number', '전화번호',
            'ssn', 'resident_number', '주민등록번호',
            'address', '주소',
            'card_number', '카드번호',
            'email', '이메일'
        ]
        
        for field in data.keys():
            if any(sensitive in field.lower() for sensitive in sensitive_fields):
                data[field] = self._mask_value(data[field], field)
        
        return data
    
    def _mask_value(self, value: str, field_type: str = None) -> str:
        """값 마스킹"""
        if not value or not isinstance(value, str):
            return value
            
        length = len(value)
        
        # 필드 타입별 마스킹 규칙
        if field_type and 'phone' in field_type.lower():
            # 전화번호: 010-****-1234
            if length >= 11:
                return f"{value[:3]}-****-{value[-4:]}"
        elif field_type and any(x in field_type.lower() for x in ['ssn', 'resident']):
            # 주민등록번호: ******-*******
            return '*' * length
        elif field_type and 'card' in field_type.lower():
            # 카드번호: ****-****-****-1234
            if length >= 16:
                return f"****-****-****-{value[-4:]}"
        elif field_type and 'email' in field_type.lower():
            # 이메일: a***@domain.com
            if '@' in value:
                local, domain = value.split('@', 1)
                if len(local) > 1:
                    return f"{local[0]}***@{domain}"
        
        # 기본 마스킹: 앞 1자, 뒤 1자만 표시
        if length <= 2:
            return '*' * length
        elif length == 3:
            return f"{value[0]}*{value[-1]}"
        else:
            return f"{value[0]}{'*' * (length - 2)}{value[-1]}"
    
    def get_ttl(self, key: str) -> Optional[int]:
        """키의 남은 TTL 조회"""
        if not self.redis_client:
            return None
            
        cache_key = f"{self.CACHE_PREFIX}:{key}"
        try:
            ttl = self.redis_client.ttl(cache_key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"TTL 조회 실패: {e}")
            return None
    
    def extend_ttl(self, key: str, additional_seconds: int = 3600) -> bool:
        """TTL 연장 (기본 1시간)"""
        if not self.redis_client:
            return False
            
        cache_key = f"{self.CACHE_PREFIX}:{key}"
        try:
            current_ttl = self.redis_client.ttl(cache_key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                self.redis_client.expire(cache_key, new_ttl)
                self.redis_client.expire(f"{cache_key}:meta", new_ttl)
                logger.info(f"TTL 연장: {cache_key}, 새 TTL: {new_ttl}초")
                return True
            return False
        except Exception as e:
            logger.error(f"TTL 연장 실패: {e}")
            return False


# 싱글톤 인스턴스
sensitive_data_manager = SensitiveDataManager()
# -*- coding: utf-8 -*-
"""
로깅 설정 및 유틸리티
"""
import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os


def setup_logging(settings_module):
    """
    로깅 시스템 설정
    
    Args:
        settings_module: Django 설정 모듈
    """
    # 로그 디렉토리 생성
    log_dir = Path(settings_module.BASE_DIR) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 로깅 설정
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{'
            },
            'json': {
                '()': 'dn_solution.utils.logging_config.JSONFormatter',
            }
        },
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'sensitive_data_filter': {
                '()': 'dn_solution.utils.logging_config.SensitiveDataFilter',
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG' if settings_module.DEBUG else 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                'filters': ['sensitive_data_filter']
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'api.log'),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'formatter': 'json',
                'filters': ['sensitive_data_filter']
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'error.log'),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'formatter': 'json',
                'filters': ['sensitive_data_filter']
            },
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'security.log'),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 10,
                'formatter': 'json',
                'filters': ['sensitive_data_filter']
            },
            'performance_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': str(log_dir / 'performance.log'),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'formatter': 'json'
            }
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['error_file', 'console'],
                'level': 'ERROR',
                'propagate': False,
            },
            'django.security': {
                'handlers': ['security_file', 'console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'companies': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG' if settings_module.DEBUG else 'INFO',
                'propagate': False,
            },
            'policies': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG' if settings_module.DEBUG else 'INFO',
                'propagate': False,
            },
            'orders': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG' if settings_module.DEBUG else 'INFO',
                'propagate': False,
            },
            'auth': {
                'handlers': ['console', 'file', 'security_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'performance': {
                'handlers': ['performance_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'cache': {
                'handlers': ['console', 'performance_file'],
                'level': 'DEBUG' if settings_module.DEBUG else 'INFO',
                'propagate': False,
            }
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        }
    }
    
    logging.config.dictConfig(LOGGING_CONFIG)


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process': record.process,
            'thread': record.thread,
        }
        
        # 추가 컨텍스트 정보
        if hasattr(record, 'user'):
            log_data['user'] = str(record.user)
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'object_id'):
            log_data['object_id'] = record.object_id
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        
        # 예외 정보
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class SensitiveDataFilter(logging.Filter):
    """민감한 데이터를 마스킹하는 로그 필터"""
    
    SENSITIVE_PATTERNS = {
        'password': '***',
        'token': '***',
        'secret': '***',
        'api_key': '***',
        'registration_number': '***-**-*****',  # 주민등록번호
        'card_number': '****-****-****-****',  # 카드번호
        'account_number': '***-***-******',  # 계좌번호
    }
    
    def filter(self, record):
        """로그 레코드 필터링"""
        message = record.getMessage()
        
        # 민감한 데이터 마스킹
        for key, mask in self.SENSITIVE_PATTERNS.items():
            if key in message.lower():
                # 간단한 마스킹 (실제로는 더 정교한 정규식 필요)
                import re
                pattern = rf'({key}["\']?\s*[=:]\s*["\']?)([^"\'\s,}}]+)'
                message = re.sub(pattern, rf'\1{mask}', message, flags=re.IGNORECASE)
        
        record.msg = message
        record.args = ()
        
        return True


class PerformanceLogger:
    """성능 로깅 유틸리티"""
    
    def __init__(self, logger_name='performance'):
        self.logger = logging.getLogger(logger_name)
    
    def log_api_call(self, method: str, path: str, duration: float, 
                     status_code: int, user=None):
        """
        API 호출 성능 로깅
        
        Args:
            method: HTTP 메서드
            path: 요청 경로
            duration: 처리 시간 (초)
            status_code: 응답 상태 코드
            user: 사용자 객체
        """
        extra = {
            'action': 'api_call',
            'method': method,
            'path': path,
            'duration': duration * 1000,  # ms로 변환
            'status_code': status_code,
        }
        
        if user:
            extra['user'] = str(user)
        
        if duration > 1.0:  # 1초 이상
            self.logger.warning(f"Slow API call: {method} {path} took {duration:.2f}s", extra=extra)
        else:
            self.logger.info(f"API call: {method} {path} took {duration:.3f}s", extra=extra)
    
    def log_db_query(self, query: str, duration: float):
        """
        데이터베이스 쿼리 성능 로깅
        
        Args:
            query: SQL 쿼리
            duration: 실행 시간 (초)
        """
        extra = {
            'action': 'db_query',
            'query': query[:500],  # 쿼리 길이 제한
            'duration': duration * 1000,  # ms로 변환
        }
        
        if duration > 0.5:  # 500ms 이상
            self.logger.warning(f"Slow query took {duration:.3f}s", extra=extra)
        else:
            self.logger.debug(f"Query took {duration:.3f}s", extra=extra)
    
    def log_cache_hit(self, cache_key: str, hit: bool):
        """
        캐시 히트/미스 로깅
        
        Args:
            cache_key: 캐시 키
            hit: 히트 여부
        """
        extra = {
            'action': 'cache_access',
            'cache_key': cache_key,
            'hit': hit
        }
        
        self.logger.debug(f"Cache {'hit' if hit else 'miss'}: {cache_key}", extra=extra)
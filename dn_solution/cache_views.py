# -*- coding: utf-8 -*-
"""
Cache Management Views - DN_SOLUTION2 리모델링
캐시 관리 API 뷰
"""

import json
import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from dn_solution.cache_manager import cache_manager, CacheMonitor, CacheManager
from dn_solution.cache_utils import CacheUtils

logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name='dispatch')
class CacheStatusView(View):
    """캐시 상태 조회 뷰"""
    
    def get(self, request):
        """캐시 시스템 상태 반환"""
        try:
            # 기본 상태 정보
            health_status = CacheMonitor.health_check()
            cache_stats = CacheMonitor.get_cache_stats()
            
            response_data = {
                'timestamp': timezone.now().isoformat(),
                'cache_backend': cache_manager.cache.__class__.__name__,
                'cache_level': cache_manager.cache_level,
                'health': health_status,
                'stats': cache_stats,
                'prefixes': CacheManager.CACHE_PREFIXES,
                'timeouts': CacheManager.CACHE_TIMEOUTS,
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"캐시 상태 조회 실패: {e}")
            return JsonResponse({
                'error': '캐시 상태 조회에 실패했습니다',
                'detail': str(e)
            }, status=500)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_cache(request):
    """캐시 삭제 API"""
    try:
        data = request.data
        pattern = data.get('pattern')
        
        if pattern:
            # 패턴 매칭 삭제
            count = cache_manager.delete_pattern(pattern)
            message = f"패턴 '{pattern}'에 매치되는 {count}개 캐시 키 삭제 완료"
        else:
            # 전체 캐시 삭제
            success = cache_manager.clear()
            if success:
                message = "전체 캐시 삭제 완료"
                count = "all"
            else:
                return Response({
                    'success': False,
                    'message': '캐시 삭제에 실패했습니다'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(f"캐시 삭제: {message} (사용자: {request.user.username})")
        
        return Response({
            'success': True,
            'message': message,
            'deleted_count': count,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"캐시 삭제 실패: {e}")
        return Response({
            'success': False,
            'message': '캐시 삭제 중 오류가 발생했습니다',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def warm_up_cache(request):
    """캐시 워밍업 API"""
    try:
        start_time = timezone.now()
        warmed_items = {}
        
        # 1. 시스템 설정 캐싱
        system_settings = {
            'app_version': '2.0.0',
            'maintenance_mode': False,
            'max_upload_size': 10 * 1024 * 1024,
            'session_timeout': 3600,
        }
        
        for key, value in system_settings.items():
            cache_key = f"system_setting:{key}"
            cache_manager.set(cache_key, value, CacheManager.CACHE_TIMEOUTS['daily'])
        
        warmed_items['system_settings'] = len(system_settings)
        
        # 2. 자주 사용되는 쿼리 결과 캐싱 (예시)
        # 실제 구현에서는 각 앱의 중요한 데이터를 캐싱
        
        end_time = timezone.now()
        elapsed_seconds = (end_time - start_time).total_seconds()
        
        logger.info(f"캐시 워밍업 완료: {warmed_items} (사용자: {request.user.username})")
        
        return Response({
            'success': True,
            'message': '캐시 워밍업이 완료되었습니다',
            'warmed_items': warmed_items,
            'elapsed_seconds': elapsed_seconds,
            'timestamp': end_time.isoformat()
        })
        
    except Exception as e:
        logger.error(f"캐시 워밍업 실패: {e}")
        return Response({
            'success': False,
            'message': '캐시 워밍업 중 오류가 발생했습니다',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def cache_performance_test(request):
    """캐시 성능 테스트 API"""
    try:
        iterations = int(request.GET.get('iterations', 100))
        
        import time
        
        # 쓰기 성능 테스트
        write_times = []
        for i in range(iterations):
            start_time = time.time()
            key = f"perf_test_write_{i}"
            value = {'test_data': i, 'timestamp': timezone.now().isoformat()}
            cache_manager.set(key, value, 60)
            write_times.append(time.time() - start_time)
        
        # 읽기 성능 테스트
        read_times = []
        for i in range(iterations):
            start_time = time.time()
            key = f"perf_test_write_{i}"
            cache_manager.get(key)
            read_times.append(time.time() - start_time)
        
        # 정리
        for i in range(iterations):
            cache_manager.delete(f"perf_test_write_{i}")
        
        # 결과 계산
        avg_write_time = sum(write_times) / len(write_times) * 1000  # ms
        avg_read_time = sum(read_times) / len(read_times) * 1000  # ms
        
        results = {
            'iterations': iterations,
            'average_write_time_ms': round(avg_write_time, 3),
            'average_read_time_ms': round(avg_read_time, 3),
            'total_time_ms': round(sum(write_times + read_times) * 1000, 3),
            'writes_per_second': round(iterations / sum(write_times), 2),
            'reads_per_second': round(iterations / sum(read_times), 2),
            'timestamp': timezone.now().isoformat()
        }
        
        return Response({
            'success': True,
            'performance_results': results
        })
        
    except Exception as e:
        logger.error(f"캐시 성능 테스트 실패: {e}")
        return Response({
            'success': False,
            'message': '성능 테스트 중 오류가 발생했습니다',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def cache_keys_list(request):
    """캐시 키 목록 조회 API (개발용)"""
    try:
        # Redis 연결을 통해 키 목록 조회
        from django_redis import get_redis_connection
        
        redis_conn = get_redis_connection("default")
        pattern = request.GET.get('pattern', '*')
        limit = int(request.GET.get('limit', 100))
        
        keys = redis_conn.keys(pattern)[:limit]
        
        key_info = []
        for key in keys:
            try:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                ttl = redis_conn.ttl(key)
                key_type = redis_conn.type(key).decode()
                
                key_info.append({
                    'key': key_str,
                    'ttl': ttl,
                    'type': key_type,
                })
            except Exception as e:
                logger.warning(f"키 정보 조회 실패 ({key}): {e}")
        
        return Response({
            'success': True,
            'pattern': pattern,
            'total_found': len(keys),
            'returned_count': len(key_info),
            'keys': key_info
        })
        
    except Exception as e:
        logger.error(f"캐시 키 목록 조회 실패: {e}")
        return Response({
            'success': False,
            'message': '키 목록 조회 중 오류가 발생했습니다',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """헬스체크 API (인증 불필요)"""
    try:
        health_status = CacheMonitor.health_check()
        
        if health_status['status'] == 'healthy':
            return Response(health_status)
        else:
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# Django 뷰 (DRF 없이 사용 가능)
@require_http_methods(["GET"])
@staff_member_required
def cache_dashboard(request):
    """캐시 대시보드 데이터"""
    try:
        # 기본 통계
        stats = CacheMonitor.get_cache_stats()
        health = CacheMonitor.health_check()
        
        # 최근 성능 메트릭 (실제로는 메트릭 저장소에서 조회)
        performance_metrics = {
            'last_hour_hit_rate': 85.2,
            'average_response_time_ms': 12.5,
            'cache_size_mb': 128.5,
            'daily_operations': 45230,
        }
        
        response_data = {
            'timestamp': timezone.now().isoformat(),
            'health': health,
            'stats': stats,
            'performance': performance_metrics,
            'cache_config': {
                'levels': ['L1 (Local)', 'L2 (Redis)', 'L3 (Database)'],
                'current_level': cache_manager.cache_level,
                'timeouts': CacheManager.CACHE_TIMEOUTS,
                'prefixes': list(CacheManager.CACHE_PREFIXES.keys()),
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"캐시 대시보드 데이터 조회 실패: {e}")
        return JsonResponse({
            'error': '대시보드 데이터 조회에 실패했습니다',
            'detail': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@staff_member_required  
def invalidate_cache_pattern(request):
    """캐시 패턴 무효화"""
    try:
        data = json.loads(request.body)
        patterns = data.get('patterns', [])
        
        if not patterns:
            return JsonResponse({
                'success': False,
                'message': '무효화할 패턴을 제공해주세요'
            }, status=400)
        
        results = {}
        total_deleted = 0
        
        for pattern in patterns:
            count = cache_manager.delete_pattern(pattern)
            results[pattern] = count
            total_deleted += count
        
        logger.info(f"캐시 패턴 무효화: {results} (사용자: {request.user.username})")
        
        return JsonResponse({
            'success': True,
            'message': f'{total_deleted}개 캐시 키가 무효화되었습니다',
            'results': results,
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'JSON 형식이 올바르지 않습니다'
        }, status=400)
    except Exception as e:
        logger.error(f"캐시 패턴 무효화 실패: {e}")
        return JsonResponse({
            'success': False,
            'message': '캐시 무효화 중 오류가 발생했습니다',
            'detail': str(e)
        }, status=500)
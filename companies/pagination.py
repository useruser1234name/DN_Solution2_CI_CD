"""
Company 앱 페이지네이션 클래스

성능 최적화된 페이지네이션을 제공합니다.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class OptimizedPageNumberPagination(PageNumberPagination):
    """
    성능 최적화된 페이지네이션
    
    - 캐싱 지원
    - 메타데이터 최적화
    - 커서 기반 페이지네이션 옵션
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """페이지네이션 응답 생성"""
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.page_size),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))
    
    def get_paginated_response_schema(self, schema):
        """페이지네이션 스키마"""
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                    'description': '전체 항목 수'
                },
                'total_pages': {
                    'type': 'integer',
                    'example': 7,
                    'description': '전체 페이지 수'
                },
                'current_page': {
                    'type': 'integer',
                    'example': 1,
                    'description': '현재 페이지 번호'
                },
                'page_size': {
                    'type': 'integer',
                    'example': 20,
                    'description': '페이지 크기'
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/accounts/?page=4',
                    'description': '다음 페이지 URL'
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/accounts/?page=2',
                    'description': '이전 페이지 URL'
                },
                'results': schema,
            },
        }


class CachedPageNumberPagination(OptimizedPageNumberPagination):
    """
    캐시를 활용한 페이지네이션
    
    자주 요청되는 페이지의 결과를 캐시하여 성능을 향상시킵니다.
    """
    
    def __init__(self):
        super().__init__()
        self.cache_timeout = 300  # 5분
    
    def paginate_queryset(self, queryset, request, view=None):
        """캐시를 고려한 쿼리셋 페이지네이션"""
        from django.core.cache import cache
        import hashlib
        import json
        
        # 캐시 키 생성
        cache_key_data = {
            'model': queryset.model.__name__,
            'page': self.get_page_number(request, self.paginator),
            'page_size': self.get_page_size(request),
            'query_params': dict(request.query_params),
            'user_id': str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None
        }
        
        cache_key = f"pagination:{hashlib.md5(json.dumps(cache_key_data, sort_keys=True).encode()).hexdigest()}"
        
        # 캐시에서 조회
        cached_result = cache.get(cache_key)
        if cached_result:
            self.page = cached_result['page']
            return cached_result['page_data']
        
        # 캐시 미스 시 일반 페이지네이션 수행
        result = super().paginate_queryset(queryset, request, view)
        
        # 결과를 캐시에 저장
        if result and self.page:
            cache_data = {
                'page': self.page,
                'page_data': list(result)  # QuerySet을 리스트로 변환
            }
            cache.set(cache_key, cache_data, self.cache_timeout)
        
        return result


class CompanyPagination(OptimizedPageNumberPagination):
    """업체 목록용 페이지네이션"""
    page_size = 25
    max_page_size = 50


class CompanyUserPagination(OptimizedPageNumberPagination):
    """업체 사용자 목록용 페이지네이션"""
    page_size = 30
    max_page_size = 100


class CursorPagination:
    """
    커서 기반 페이지네이션 (대용량 데이터용)
    
    OFFSET 기반 페이지네이션의 성능 문제를 해결합니다.
    """
    
    def __init__(self, ordering_field='created_at', page_size=20):
        self.ordering_field = ordering_field
        self.page_size = page_size
    
    def paginate_queryset(self, queryset, cursor=None, direction='next'):
        """커서 기반 쿼리셋 페이지네이션"""
        ordered_qs = queryset.order_by(f'-{self.ordering_field}')
        
        if cursor:
            if direction == 'next':
                # 다음 페이지: 커서보다 작은 값들
                ordered_qs = ordered_qs.filter(**{f'{self.ordering_field}__lt': cursor})
            else:
                # 이전 페이지: 커서보다 큰 값들
                ordered_qs = ordered_qs.filter(**{f'{self.ordering_field}__gt': cursor})
                ordered_qs = ordered_qs.order_by(self.ordering_field)
        
        # 페이지 크기보다 1개 더 조회하여 다음 페이지 존재 여부 확인
        items = list(ordered_qs[:self.page_size + 1])
        
        has_next = len(items) > self.page_size
        if has_next:
            items = items[:-1]  # 마지막 항목 제거
        
        # 이전 페이지에서는 순서를 다시 뒤집기
        if cursor and direction == 'previous':
            items.reverse()
        
        return {
            'items': items,
            'has_next': has_next,
            'has_previous': cursor is not None,
            'next_cursor': getattr(items[-1], self.ordering_field) if items and has_next else None,
            'previous_cursor': getattr(items[0], self.ordering_field) if items and cursor else None
        }


class SmartPagination:
    """
    스마트 페이지네이션
    
    데이터 크기에 따라 적절한 페이지네이션 방식을 자동 선택합니다.
    """
    
    SMALL_DATASET_THRESHOLD = 1000
    LARGE_DATASET_THRESHOLD = 10000
    
    @classmethod
    def get_paginator(cls, queryset, request):
        """데이터셋 크기에 따른 최적 페이지네이터 선택"""
        # 대략적인 카운트 추정 (정확한 카운트는 비용이 많이 듦)
        estimated_count = cls._estimate_count(queryset)
        
        if estimated_count <= cls.SMALL_DATASET_THRESHOLD:
            # 작은 데이터셋: 일반 페이지네이션
            return OptimizedPageNumberPagination()
        elif estimated_count <= cls.LARGE_DATASET_THRESHOLD:
            # 중간 데이터셋: 캐시된 페이지네이션
            return CachedPageNumberPagination()
        else:
            # 대용량 데이터셋: 커서 기반 페이지네이션 권장
            # (하지만 API 호환성을 위해 캐시된 페이지네이션 사용)
            paginator = CachedPageNumberPagination()
            paginator.page_size = 50  # 페이지 크기 증가
            return paginator
    
    @classmethod
    def _estimate_count(cls, queryset):
        """쿼리셋 카운트 추정"""
        try:
            # EXPLAIN을 사용한 추정 (PostgreSQL 등)
            # 여기서는 단순히 실제 카운트 사용
            return queryset.count()
        except Exception:
            # 오류 시 중간 크기로 가정
            return cls.SMALL_DATASET_THRESHOLD + 1


class PerformanceOptimizedMixin:
    """
    성능 최적화 믹스인
    
    ViewSet에 적용하여 자동으로 최적화된 페이지네이션을 사용합니다.
    """
    
    def get_queryset(self):
        """최적화된 쿼리셋 반환"""
        queryset = super().get_queryset()
        
        # 필수 관련 객체 미리 로드
        if hasattr(self, 'select_related_fields'):
            queryset = queryset.select_related(*self.select_related_fields)
        
        if hasattr(self, 'prefetch_related_fields'):
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)
        
        return queryset
    
    @property
    def paginator(self):
        """스마트 페이지네이터 사용"""
        if not hasattr(self, '_paginator'):
            self._paginator = SmartPagination.get_paginator(
                self.get_queryset(), 
                self.request
            )
        return self._paginator
    
    def paginate_queryset(self, queryset):
        """최적화된 페이지네이션 수행"""
        # 페이지네이션 전에 쿼리 최적화
        if hasattr(self, 'optimize_queryset'):
            queryset = self.optimize_queryset(queryset)
        
        return super().paginate_queryset(queryset)

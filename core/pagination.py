"""
커스텀 페이지네이션 클래스

이 모듈은 API 응답의 페이지네이션을 위한 커스텀 클래스를 제공합니다.
성능 최적화와 사용자 경험 개선을 위해 설계되었습니다.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultSetPagination(PageNumberPagination):
    """
    표준 페이지네이션 클래스
    
    - 페이지 크기 조절 가능
    - 메타데이터 포함
    - 성능 최적화
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """페이지네이션된 응답 반환"""
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })


class LargeResultSetPagination(PageNumberPagination):
    """
    대용량 데이터를 위한 페이지네이션 클래스
    
    - 더 큰 페이지 크기 지원
    - 성능 최적화
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    
    def get_paginated_response(self, data):
        """페이지네이션된 응답 반환"""
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })


class CursorSetPagination(PageNumberPagination):
    """
    실시간 데이터를 위한 커서 기반 페이지네이션
    
    - 정렬 필드 기반
    - 실시간 데이터 처리에 적합
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-created_at'  # 기본 정렬 필드
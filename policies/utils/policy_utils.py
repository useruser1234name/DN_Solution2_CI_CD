"""
정책 관련 유틸리티 함수
"""

import logging
from ..models import Policy, PolicyAssignment, PolicyExposure

logger = logging.getLogger('policies')


def get_visible_policies(company=None, user=None):
    """
    노출 가능한 정책 목록을 반환합니다.
    
    Args:
        company: 회사 객체 (선택사항)
        user: 사용자 객체 (선택사항)
        
    Returns:
        QuerySet: 노출 가능한 정책 목록
    """
    # 기본적으로 노출 설정된 정책만 반환
    queryset = Policy.objects.filter(expose=True, is_active=True)
    
    # 회사 정보가 있으면 추가 필터링
    if company:
        # 회사 타입에 따라 다른 필터링 적용
        if company.type == 'headquarters' or company.code.startswith('A-'):
            # 본사는 모든 정책 볼 수 있음 (단, 노출 설정된 것만)
            pass
        elif company.type == 'agency' or company.code.startswith('B-'):
            # 협력사는 자신에게 배정된 정책만 볼 수 있음
            queryset = queryset.filter(
                assignments__company=company
            ).distinct()
        elif company.type == 'retail' or company.code.startswith('C-'):
            # 판매점은 상위 협력사에 배정되고 하위 노출 설정된 정책만 볼 수 있음
            if company.parent_company:
                queryset = queryset.filter(
                    assignments__company=company.parent_company,
                    assignments__expose_to_child=True
                ).distinct()
            else:
                # 상위 협력사가 없는 판매점은 직접 배정된 정책만 볼 수 있음
                queryset = queryset.filter(
                    assignments__company=company
                ).distinct()
    
    # 사용자 정보가 있으면 추가 필터링 가능
    if user and user.is_authenticated and not user.is_superuser:
        # 필요한 경우 사용자별 추가 필터링 로직 구현
        pass
    
    return queryset

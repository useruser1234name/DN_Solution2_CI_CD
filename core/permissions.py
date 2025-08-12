"""
계층적 권한 시스템
본사 > 협력사 > 판매점 계층 구조에 따른 권한 관리
"""

import logging
from typing import Optional, List, Tuple

from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View

logger = logging.getLogger(__name__)


class HierarchyPermission(permissions.BasePermission):
    """
    계층 구조 기반 권한 클래스
    상위 계층은 하위 계층의 데이터에 접근 가능
    """
    
    def has_permission(self, request: Request, view: View) -> bool:
        """
        뷰 레벨 권한 체크
        인증된 사용자만 접근 가능
        """
        if not request.user.is_authenticated:
            logger.warning(f"인증되지 않은 사용자 접근 시도: {request.path}")
            return False
            
        # 슈퍼유저는 모든 권한 허용
        if request.user.is_superuser:
            return True
            
        # CompanyUser가 있는지 확인
        if not hasattr(request.user, 'companyuser'):
            logger.warning(f"CompanyUser가 없는 사용자: {request.user.username}")
            return False
            
        return True
    
    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """
        객체 레벨 권한 체크
        계층 구조에 따른 접근 권한 검증
        """
        if not request.user.is_authenticated:
            return False
            
        # 슈퍼유저는 모든 권한 허용
        if request.user.is_superuser:
            return True
            
        company_user = getattr(request.user, 'companyuser', None)
        if not company_user:
            return False
            
        user_company = company_user.company
        
        # 객체가 company 속성을 가진 경우
        if hasattr(obj, 'company'):
            return self._check_company_hierarchy(user_company, obj.company)
        
        # 객체가 Company 모델인 경우
        if hasattr(obj, 'company_type'):
            return self._check_company_hierarchy(user_company, obj)
            
        # 기타 경우는 동일 회사만 허용
        return True
    
    def _check_company_hierarchy(self, user_company, target_company) -> bool:
        """
        회사 계층 구조 확인
        상위 회사는 하위 회사 데이터 접근 가능
        """
        if not user_company or not target_company:
            return False
            
        # 동일 회사
        if user_company.id == target_company.id:
            return True
            
        # 본사는 모든 데이터 접근 가능
        if user_company.company_type == 'headquarters':
            return True
            
        # 협력사는 자신의 하위 판매점 데이터만 접근 가능
        if user_company.company_type == 'agency':
            if target_company.company_type == 'retail' and \
               target_company.parent_company_id == user_company.id:
                return True
                
        return False


class CompanyTypePermission(permissions.BasePermission):
    """
    회사 타입별 권한 클래스
    특정 기능을 특정 회사 타입만 사용 가능하도록 제한
    """
    
    # 회사 타입별 허용된 액션
    ALLOWED_ACTIONS = {
        'headquarters': ['create_policy', 'manage_agencies', 'approve_orders', 'view_all'],
        'agency': ['manage_retails', 'view_orders', 'distribute_rebates'],
        'retail': ['create_order', 'edit_own_order', 'view_own_orders']
    }
    
    def __init__(self, required_types: List[str] = None, required_action: str = None):
        """
        Args:
            required_types: 허용된 회사 타입 리스트
            required_action: 필요한 액션
        """
        self.required_types = required_types or []
        self.required_action = required_action
    
    def has_permission(self, request: Request, view: View) -> bool:
        """회사 타입 기반 권한 체크"""
        if not request.user.is_authenticated:
            return False
            
        if request.user.is_superuser:
            return True
            
        company_user = getattr(request.user, 'companyuser', None)
        if not company_user:
            return False
            
        company_type = company_user.company.company_type
        
        # 특정 타입만 허용하는 경우
        if self.required_types and company_type not in self.required_types:
            logger.warning(
                f"권한 거부: {company_type} 타입은 {self.required_types}에 포함되지 않음"
            )
            return False
            
        # 특정 액션이 필요한 경우
        if self.required_action:
            allowed_actions = self.ALLOWED_ACTIONS.get(company_type, [])
            if self.required_action not in allowed_actions:
                logger.warning(
                    f"권한 거부: {company_type} 타입은 {self.required_action} 액션 불가"
                )
                return False
                
        return True


class IsOwnerPermission(permissions.BasePermission):
    """
    소유자 권한 클래스
    자신이 생성한 데이터만 수정/삭제 가능
    """
    
    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """객체 소유자 확인"""
        # 읽기는 모두 허용
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # 슈퍼유저는 모든 권한 허용
        if request.user.is_superuser:
            return True
            
        # created_by 필드 확인
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
            
        # user 필드 확인
        if hasattr(obj, 'user'):
            return obj.user == request.user
            
        # company 필드를 통한 확인
        if hasattr(obj, 'company'):
            company_user = getattr(request.user, 'companyuser', None)
            if company_user:
                return obj.company == company_user.company
                
        return False


class OrderPermission(HierarchyPermission):
    """
    주문 관련 특별 권한
    """
    
    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        """주문 객체에 대한 권한 체크"""
        if not super().has_object_permission(request, view, obj):
            return False
            
        company_user = request.user.companyuser
        company_type = company_user.company.company_type
        
        # 주문 상태에 따른 권한 제어
        if hasattr(obj, 'status'):
            # 판매점은 pending 상태의 주문만 수정 가능
            if company_type == 'retail' and request.method in ['PUT', 'PATCH', 'DELETE']:
                if obj.status != 'pending':
                    logger.warning(
                        f"권한 거부: 판매점은 {obj.status} 상태의 주문을 수정할 수 없음"
                    )
                    return False
                    
            # 본사만 주문 승인 가능
            if 'approve' in request.path and company_type != 'headquarters':
                logger.warning(f"권한 거부: {company_type}는 주문을 승인할 수 없음")
                return False
                
        return True


class PolicyPermission(CompanyTypePermission):
    """
    정책 관련 권한
    본사만 정책 생성/수정 가능
    """
    
    def __init__(self):
        super().__init__(required_types=['headquarters'])
    
    def has_permission(self, request: Request, view: View) -> bool:
        """정책 권한 체크"""
        # 조회는 모든 인증된 사용자 허용
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
            
        # 생성/수정/삭제는 본사만
        return super().has_permission(request, view)


def check_company_permission(user: User, target_company, action: str = 'view') -> bool:
    """
    회사 권한 체크 유틸리티 함수
    
    Args:
        user: 요청 사용자
        target_company: 대상 회사
        action: 수행할 액션 (view, edit, delete)
        
    Returns:
        권한 여부
    """
    if not user.is_authenticated:
        return False
        
    if user.is_superuser:
        return True
        
    company_user = getattr(user, 'companyuser', None)
    if not company_user:
        return False
        
    user_company = company_user.company
    
    # 읽기 권한
    if action == 'view':
        # 본사는 모든 회사 조회 가능
        if user_company.company_type == 'headquarters':
            return True
        # 협력사는 자신과 하위 판매점 조회 가능
        elif user_company.company_type == 'agency':
            return (user_company.id == target_company.id or
                   (target_company.company_type == 'retail' and 
                    target_company.parent_company_id == user_company.id))
        # 판매점은 자신만 조회 가능
        else:
            return user_company.id == target_company.id
    
    # 수정/삭제 권한
    elif action in ['edit', 'delete']:
        # 본사는 모든 회사 수정 가능
        if user_company.company_type == 'headquarters':
            return True
        # 그 외에는 자신만 수정 가능
        else:
            return user_company.id == target_company.id
            
    return False


def get_accessible_companies(user: User) -> List[int]:
    """
    사용자가 접근 가능한 회사 ID 목록 반환
    
    Args:
        user: 요청 사용자
        
    Returns:
        접근 가능한 회사 ID 리스트
    """
    if not user.is_authenticated:
        return []
        
    if user.is_superuser:
        from companies.models import Company
        return list(Company.objects.values_list('id', flat=True))
        
    company_user = getattr(user, 'companyuser', None)
    if not company_user:
        return []
        
    user_company = company_user.company
    accessible_ids = [user_company.id]
    
    # 본사는 모든 회사 접근 가능
    if user_company.company_type == 'headquarters':
        from companies.models import Company
        return list(Company.objects.values_list('id', flat=True))
    
    # 협력사는 하위 판매점도 접근 가능
    elif user_company.company_type == 'agency':
        from companies.models import Company
        retail_ids = Company.objects.filter(
            parent_company=user_company,
            company_type='retail'
        ).values_list('id', flat=True)
        accessible_ids.extend(retail_ids)
        
    return accessible_ids
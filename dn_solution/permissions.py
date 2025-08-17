# -*- coding: utf-8 -*-
"""
Hierarchical Permission System - DN_SOLUTION2 리모델링
계층별 권한 시스템
"""

import logging
from typing import Dict, List, Set, Optional, Any
from enum import Enum
from django.contrib.auth.models import User
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from companies.models import Company, CompanyUser
from django.core.cache import cache
from dn_solution.cache_manager import cache_manager, CacheManager
from dn_solution.cache_utils import CacheUtils

logger = logging.getLogger('permissions')


class CompanyType(Enum):
    """회사 타입 열거형"""
    HEADQUARTERS = 'headquarters'
    AGENCY = 'agency'
    RETAIL = 'retail'


class UserRole(Enum):
    """사용자 역할 열거형"""
    ADMIN = 'admin'
    MANAGER = 'manager' 
    STAFF = 'staff'
    VIEWER = 'viewer'


class PermissionLevel(Enum):
    """권한 레벨 열거형"""
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3
    SUPER_ADMIN = 4


class HierarchicalPermissionManager:
    """계층별 권한 관리자"""
    
    # 회사 타입별 권한 매트릭스
    COMPANY_PERMISSIONS = {
        CompanyType.HEADQUARTERS: {
            'can_view_all_companies': True,
            'can_manage_agencies': True,
            'can_manage_retailers': True,
            'can_view_all_reports': True,
            'can_manage_policies': True,
            'can_approve_settlements': True,
            'hierarchy_level': 1,
        },
        CompanyType.AGENCY: {
            'can_view_subordinate_companies': True,
            'can_manage_retailers': True,
            'can_view_subordinate_reports': True,
            'can_manage_orders': True,
            'can_request_settlements': True,
            'hierarchy_level': 2,
        },
        CompanyType.RETAIL: {
            'can_view_own_company': True,
            'can_manage_own_orders': True,
            'can_view_own_reports': True,
            'can_request_rebates': True,
            'hierarchy_level': 3,
        }
    }
    
    # 역할별 권한 매트릭스
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            'can_manage_users': True,
            'can_approve_users': True,
            'can_manage_company_settings': True,
            'can_view_all_data': True,
            'can_export_data': True,
        },
        UserRole.MANAGER: {
            'can_view_reports': True,
            'can_manage_orders': True,
            'can_approve_orders': True,
            'can_manage_inventory': True,
        },
        UserRole.STAFF: {
            'can_create_orders': True,
            'can_view_own_orders': True,
            'can_update_inventory': True,
        },
        UserRole.VIEWER: {
            'can_view_reports': True,
            'can_view_orders': True,
        }
    }
    
    @classmethod
    def get_user_permissions(cls, user: User) -> Dict[str, Any]:
        """사용자의 전체 권한 조회 (캐시 활용)"""
        cache_key = f"user_full_permissions:{user.id}"
        cached_permissions = cache_manager.get(cache_key)
        
        if cached_permissions is not None:
            return cached_permissions
        
        permissions = {
            'user_id': user.id,
            'username': user.username,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'company_permissions': {},
            'role_permissions': {},
            'combined_permissions': {},
            'hierarchy_level': 999,  # 기본값 (권한 없음)
        }
        
        try:
            if hasattr(user, 'companyuser'):
                company_user = user.companyuser
                company = company_user.company
                
                # 회사 정보
                permissions.update({
                    'company_id': company.id,
                    'company_code': company.code,
                    'company_name': company.name,
                    'company_type': company.type,
                    'user_role': company_user.role,
                    'is_primary_admin': getattr(company_user, 'is_primary_admin', False),
                })
                
                # 회사 타입별 권한
                company_type = CompanyType(company.type)
                permissions['company_permissions'] = cls.COMPANY_PERMISSIONS.get(company_type, {})
                permissions['hierarchy_level'] = permissions['company_permissions'].get('hierarchy_level', 999)
                
                # 역할별 권한
                user_role = UserRole(company_user.role)
                permissions['role_permissions'] = cls.ROLE_PERMISSIONS.get(user_role, {})
                
                # 권한 조합
                permissions['combined_permissions'] = {
                    **permissions['company_permissions'],
                    **permissions['role_permissions']
                }
                
                # 특수 권한 (주 관리자)
                if permissions['is_primary_admin']:
                    permissions['combined_permissions']['can_delete_company'] = True
                    permissions['combined_permissions']['can_transfer_ownership'] = True
        
        except Exception as e:
            logger.error(f"사용자 권한 조회 실패: {e}")
        
        # 캐시에 저장
            cache_manager.set(cache_key, permissions, CacheManager.CACHE_TIMEOUTS['long'])
        
        return permissions
    
    @classmethod
    def can_access_company(cls, user: User, target_company_id: int) -> bool:
        """사용자가 특정 회사에 접근할 수 있는지 확인"""
        user_permissions = cls.get_user_permissions(user)
        
        # 슈퍼유저는 모든 회사 접근 가능
        if user_permissions.get('is_superuser'):
            return True
        
        user_company_id = user_permissions.get('company_id')
        if not user_company_id:
            return False
        
        # 자신의 회사는 항상 접근 가능
        if user_company_id == target_company_id:
            return True
        
        # 계층별 접근 권한 확인
        company_type = user_permissions.get('company_type')
        
        if company_type == CompanyType.HEADQUARTERS.value:
            # 본부는 모든 회사 접근 가능
            return True
        elif company_type == CompanyType.AGENCY.value:
            # 대리점은 하위 소매점만 접근 가능
            return cls._is_subordinate_company(user_company_id, target_company_id)
        
        return False
    
    @classmethod
    def can_manage_user(cls, manager_user: User, target_user: User) -> bool:
        """사용자가 다른 사용자를 관리할 수 있는지 확인"""
        manager_permissions = cls.get_user_permissions(manager_user)
        target_permissions = cls.get_user_permissions(target_user)
        
        # 슈퍼유저는 모든 사용자 관리 가능
        if manager_permissions.get('is_superuser'):
            return True
        
        # 사용자 관리 권한이 있는지 확인
        if not manager_permissions.get('combined_permissions', {}).get('can_manage_users'):
            return False
        
        # 계층 레벨 비교 (낮은 번호가 상위)
        manager_level = manager_permissions.get('hierarchy_level', 999)
        target_level = target_permissions.get('hierarchy_level', 999)
        
        if manager_level >= target_level:
            return False
        
        # 회사 관계 확인
        manager_company_id = manager_permissions.get('company_id')
        target_company_id = target_permissions.get('company_id')
        
        if manager_company_id == target_company_id:
            # 같은 회사 내에서는 역할에 따라 관리 가능
            return True
        
        # 상위 회사에서 하위 회사 사용자 관리
        return cls.can_access_company(manager_user, target_company_id)
    
    @classmethod
    def get_accessible_companies(cls, user: User) -> List[int]:
        """사용자가 접근 가능한 회사 ID 목록 조회 (캐시 활용)"""
        cache_key = f"accessible_companies:{user.id}"
        cached_companies = cache_manager.get(cache_key)
        
        if cached_companies is not None:
            return cached_companies
        
        user_permissions = cls.get_user_permissions(user)
        accessible_companies = []
        
        try:
            # 슈퍼유저는 모든 회사 접근 가능
            if user_permissions.get('is_superuser'):
                all_companies = Company.objects.filter(status=True).values_list('id', flat=True)
                accessible_companies = list(all_companies)
            else:
                user_company_id = user_permissions.get('company_id')
                company_type = user_permissions.get('company_type')
                
                if user_company_id:
                    accessible_companies.append(user_company_id)
                    
                    if company_type == CompanyType.HEADQUARTERS.value:
                        # 본부: 모든 하위 회사
                        subordinates = Company.objects.filter(
                            parent_company_id=user_company_id, status=True
                        ).values_list('id', flat=True)
                        accessible_companies.extend(subordinates)
                        
                        # 손자 회사들도 포함 (대리점의 하위 소매점들)
                        for subordinate_id in subordinates:
                            grand_children = Company.objects.filter(
                                parent_company_id=subordinate_id, status=True
                            ).values_list('id', flat=True)
                            accessible_companies.extend(grand_children)
                    
                    elif company_type == CompanyType.AGENCY.value:
                        # 대리점: 직접 하위 소매점들만
                        subordinates = Company.objects.filter(
                            parent_company_id=user_company_id, status=True
                        ).values_list('id', flat=True)
                        accessible_companies.extend(subordinates)
        
        except Exception as e:
            logger.error(f"접근 가능 회사 목록 조회 실패: {e}")
        
        # 중복 제거
        accessible_companies = list(set(accessible_companies))
        
        # 캐시에 저장
            cache_manager.set(cache_key, accessible_companies, CacheManager.CACHE_TIMEOUTS['long'])
        
        return accessible_companies
    
    @classmethod
    def _is_subordinate_company(cls, parent_company_id: int, child_company_id: int) -> bool:
        """하위 회사 관계 확인 (캐시 활용)"""
        cache_key = f"subordinate_check:{parent_company_id}:{child_company_id}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        try:
            # 직접 하위 회사인지 확인
            is_direct_child = Company.objects.filter(
                id=child_company_id, 
                parent_company_id=parent_company_id
            ).exists()
            
            if is_direct_child:
                result = True
            else:
                # 간접 하위 회사인지 확인 (손자 회사 등)
                # 재귀적으로 확인하되, 무한 루프 방지를 위해 깊이 제한
                result = cls._check_hierarchical_relationship(parent_company_id, child_company_id, depth=0, max_depth=5)
            
            # 캐시에 저장
            cache_manager.set(cache_key, result, CacheManager.CACHE_TIMEOUTS['daily'])
            
            return result
            
        except Exception as e:
            logger.error(f"하위 회사 관계 확인 실패: {e}")
            return False
    
    @classmethod
    def _check_hierarchical_relationship(cls, ancestor_id: int, descendant_id: int, depth: int = 0, max_depth: int = 5) -> bool:
        """계층적 관계 확인 (재귀)"""
        if depth > max_depth:
            return False
        
        try:
            # 현재 레벨의 자식 회사들 조회
            children = Company.objects.filter(parent_company_id=ancestor_id).values_list('id', flat=True)
            
            if descendant_id in children:
                return True
            
            # 자식 회사들에서 재귀적으로 검색
            for child_id in children:
                if cls._check_hierarchical_relationship(child_id, descendant_id, depth + 1, max_depth):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"계층 관계 확인 실패: {e}")
            return False


# DRF Permission Classes

class IsAuthenticated(BasePermission):
    """인증된 사용자 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsCompanyUser(BasePermission):
    """회사 사용자 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        return hasattr(request.user, 'companyuser')


class IsApprovedUser(BasePermission):
    """승인된 사용자 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'companyuser'):
            return False
        
        company_user = request.user.companyuser
        return company_user.status == 'approved' and company_user.is_approved


class IsAdminUser(BasePermission):
    """관리자 사용자 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 슈퍼유저는 항상 허용
        if request.user.is_superuser:
            return True
        
        # 회사 관리자 확인
        if hasattr(request.user, 'companyuser'):
            company_user = request.user.companyuser
            return company_user.role == 'admin' and company_user.status == 'approved'
        
        return False


class CanManageCompany(BasePermission):
    """회사 관리 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        return IsApprovedUser().has_permission(request, view)
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.user.is_superuser:
            return True
        
        # 객체가 Company인 경우
        if isinstance(obj, Company):
            return HierarchicalPermissionManager.can_access_company(request.user, obj.id)
        
        # 객체가 CompanyUser인 경우
        if isinstance(obj, CompanyUser):
            return HierarchicalPermissionManager.can_access_company(request.user, obj.company.id)
        
        return False


class CanManageUsers(BasePermission):
    """사용자 관리 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not IsApprovedUser().has_permission(request, view):
            return False
        
        user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
        return user_permissions.get('combined_permissions', {}).get('can_manage_users', False)
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.user.is_superuser:
            return True
        
        # 사용자 객체인 경우
        if isinstance(obj, (User, CompanyUser)):
            target_user = obj if isinstance(obj, User) else obj.django_user
            return HierarchicalPermissionManager.can_manage_user(request.user, target_user)
        
        return False


class CanViewReports(BasePermission):
    """리포트 조회 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not IsApprovedUser().has_permission(request, view):
            return False
        
        user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
        combined_permissions = user_permissions.get('combined_permissions', {})
        
        return (combined_permissions.get('can_view_all_reports', False) or 
                combined_permissions.get('can_view_subordinate_reports', False) or
                combined_permissions.get('can_view_own_reports', False))


class CanManageOrders(BasePermission):
    """주문 관리 권한"""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not IsApprovedUser().has_permission(request, view):
            return False
        
        user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
        combined_permissions = user_permissions.get('combined_permissions', {})
        
        return (combined_permissions.get('can_manage_orders', False) or 
                combined_permissions.get('can_manage_own_orders', False) or
                combined_permissions.get('can_create_orders', False))


# 권한 데코레이터
def require_permission(permission_name: str):
    """권한 필요 데코레이터"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                from django.http import JsonResponse
                return JsonResponse({'error': '인증이 필요합니다.'}, status=401)
            
            user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
            if not user_permissions.get('combined_permissions', {}).get(permission_name, False):
                from django.http import JsonResponse
                return JsonResponse({'error': '권한이 없습니다.'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_company_access(company_id_param: str = 'company_id'):
    """회사 접근 권한 필요 데코레이터"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                from django.http import JsonResponse
                return JsonResponse({'error': '인증이 필요합니다.'}, status=401)
            
            # URL 파라미터 또는 요청 데이터에서 회사 ID 추출
            company_id = kwargs.get(company_id_param) or request.data.get(company_id_param)
            if not company_id:
                from django.http import JsonResponse
                return JsonResponse({'error': '회사 ID가 필요합니다.'}, status=400)
            
            if not HierarchicalPermissionManager.can_access_company(request.user, int(company_id)):
                from django.http import JsonResponse
                return JsonResponse({'error': '해당 회사에 접근할 권한이 없습니다.'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
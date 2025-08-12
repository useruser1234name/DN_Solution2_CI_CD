# -*- coding: utf-8 -*-
"""
Permission Management Views - DN_SOLUTION2 리모델링
권한 관리 뷰들
"""

import logging
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from companies.models import Company, CompanyUser
from dn_solution.permissions import (
    HierarchicalPermissionManager, IsAuthenticated, IsApprovedUser,
    IsAdminUser, CanManageUsers, require_permission, require_company_access
)
from django.core.cache import cache
from dn_solution.cache_utils import cache_user_data

logger = logging.getLogger('permission_views')


class UserPermissionsView(APIView):
    """사용자 권한 조회 뷰"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        """사용자 권한 정보 조회"""
        try:
            # 대상 사용자 결정
            if user_id:
                # 다른 사용자의 권한 조회 시 권한 확인
                if user_id != str(request.user.id) and not request.user.is_superuser:
                    # 관리자인지 확인
                    user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
                    if not user_permissions.get('combined_permissions', {}).get('can_manage_users'):
                        return Response({
                            'error': '다른 사용자의 권한을 조회할 권한이 없습니다.'
                        }, status=status.HTTP_403_FORBIDDEN)
                
                try:
                    target_user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return Response({
                        'error': '사용자를 찾을 수 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                target_user = request.user
            
            # 권한 정보 조회
            permissions = HierarchicalPermissionManager.get_user_permissions(target_user)
            
            # 접근 가능한 회사 목록 추가
            accessible_companies = HierarchicalPermissionManager.get_accessible_companies(target_user)
            permissions['accessible_companies'] = accessible_companies
            
            return Response(permissions)
            
        except Exception as e:
            logger.error(f"사용자 권한 조회 실패: {e}")
            return Response({
                'error': '권한 정보 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompanyAccessCheckView(APIView):
    """회사 접근 권한 확인 뷰"""
    permission_classes = [IsApprovedUser]
    
    def get(self, request, company_id):
        """특정 회사에 대한 접근 권한 확인"""
        try:
            # 회사 존재 확인
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return Response({
                    'error': '회사를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 접근 권한 확인
            can_access = HierarchicalPermissionManager.can_access_company(request.user, company_id)
            
            response_data = {
                'company_id': company_id,
                'company_name': company.name,
                'company_type': company.type,
                'can_access': can_access,
                'access_level': self._get_access_level(request.user, company),
            }
            
            if can_access:
                # 접근 가능한 경우 상세 권한 정보 제공
                user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
                response_data['permissions'] = user_permissions.get('combined_permissions', {})
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"회사 접근 권한 확인 실패: {e}")
            return Response({
                'error': '권한 확인 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_access_level(self, user, company) -> str:
        """접근 레벨 결정"""
        if user.is_superuser:
            return 'super_admin'
        
        user_permissions = HierarchicalPermissionManager.get_user_permissions(user)
        user_company_id = user_permissions.get('company_id')
        
        if user_company_id == company.id:
            return 'owner'
        elif user_permissions.get('company_type') == 'headquarters':
            return 'headquarters'
        elif user_permissions.get('company_type') == 'agency':
            return 'agency'
        else:
            return 'none'


class UserManagementPermissionView(APIView):
    """사용자 관리 권한 확인 뷰"""
    permission_classes = [CanManageUsers]
    
    def get(self, request):
        """관리 가능한 사용자 목록 조회"""
        try:
            user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
            accessible_companies = user_permissions.get('accessible_companies', [])
            
            # 접근 가능한 회사의 사용자들 조회
            manageable_users = CompanyUser.objects.filter(
                company_id__in=accessible_companies
            ).select_related('django_user', 'company')
            
            # 실제 관리 권한 확인
            manageable_user_data = []
            for company_user in manageable_users:
                if HierarchicalPermissionManager.can_manage_user(request.user, company_user.django_user):
                    manageable_user_data.append({
                        'id': company_user.id,
                        'user_id': company_user.django_user.id,
                        'username': company_user.username,
                        'company_id': company_user.company.id,
                        'company_name': company_user.company.name,
                        'company_type': company_user.company.type,
                        'role': company_user.role,
                        'status': company_user.status,
                        'is_approved': company_user.is_approved,
                    })
            
            return Response({
                'manageable_users': manageable_user_data,
                'total_count': len(manageable_user_data),
                'user_permissions': user_permissions.get('combined_permissions', {}),
            })
            
        except Exception as e:
            logger.error(f"관리 가능한 사용자 목록 조회 실패: {e}")
            return Response({
                'error': '사용자 목록 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, target_user_id):
        """사용자 관리 작업 수행 (승인/거부/역할변경 등)"""
        try:
            # 대상 사용자 조회
            try:
                target_company_user = CompanyUser.objects.get(id=target_user_id)
                target_user = target_company_user.django_user
            except CompanyUser.DoesNotExist:
                return Response({
                    'error': '사용자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 관리 권한 확인
            if not HierarchicalPermissionManager.can_manage_user(request.user, target_user):
                return Response({
                    'error': '해당 사용자를 관리할 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            action = request.data.get('action')
            
            if action == 'approve':
                target_company_user.status = 'approved'
                target_company_user.is_approved = True
                target_company_user.approved_by = request.user.companyuser
                target_company_user.approved_at = timezone.now()
                message = f'{target_company_user.username}님이 승인되었습니다.'
                
            elif action == 'reject':
                target_company_user.status = 'rejected'
                target_company_user.is_approved = False
                message = f'{target_company_user.username}님이 거부되었습니다.'
                
            elif action == 'change_role':
                new_role = request.data.get('new_role')
                if new_role not in ['admin', 'manager', 'staff', 'viewer']:
                    return Response({
                        'error': '유효하지 않은 역할입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 역할 변경 권한 확인 (관리자만 가능)
                manager_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
                if manager_permissions.get('user_role') != 'admin':
                    return Response({
                        'error': '역할을 변경할 권한이 없습니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                old_role = target_company_user.role
                target_company_user.role = new_role
                message = f'{target_company_user.username}님의 역할이 {old_role}에서 {new_role}로 변경되었습니다.'
                
            else:
                return Response({
                    'error': '유효하지 않은 작업입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            target_company_user.save()
            
            # 관련 캐시 무효화
            self._invalidate_user_caches(target_user)
            
            logger.info(f"사용자 관리 작업: {message} (관리자: {request.user.username})")
            
            return Response({
                'message': message,
                'user_status': target_company_user.status,
                'user_role': target_company_user.role,
            })
            
        except Exception as e:
            logger.error(f"사용자 관리 작업 실패: {e}")
            return Response({
                'error': '사용자 관리 작업 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _invalidate_user_caches(self, user):
        """사용자 관련 캐시 무효화"""
        patterns = [
            f'user_full_permissions:{user.id}',
            f'accessible_companies:{user.id}',
            f'user:{user.id}:*',
        ]
        
        for pattern in patterns:
            cache_manager.delete_pattern(pattern)


@api_view(['GET'])
@permission_classes([IsApprovedUser])
def get_company_hierarchy(request, company_id=None):
    """회사 계층 구조 조회"""
    try:
        # 회사 ID가 지정되지 않은 경우 사용자의 회사 사용
        if not company_id:
            if not hasattr(request.user, 'companyuser'):
                return Response({
                    'error': '회사 정보가 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            company_id = request.user.companyuser.company.id
        
        # 접근 권한 확인
        if not HierarchicalPermissionManager.can_access_company(request.user, company_id):
            return Response({
                'error': '해당 회사 정보에 접근할 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 계층 구조 조회
        hierarchy = get_company_hierarchy_tree(company_id)
        
        return Response({
            'company_id': company_id,
            'hierarchy': hierarchy,
        })
        
    except Company.DoesNotExist:
        return Response({
            'error': '회사를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"회사 계층 구조 조회 실패: {e}")
        return Response({
            'error': '계층 구조 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_company_hierarchy_tree(company_id: int) -> dict:
    """회사 계층 구조 트리 생성"""
    try:
        company = Company.objects.get(id=company_id)
        
        hierarchy = {
            'id': company.id,
            'code': company.code,
            'name': company.name,
            'type': company.type,
            'status': company.status,
            'parent_id': company.parent_company_id,
            'children': []
        }
        
        # 하위 회사들 조회
        children = Company.objects.filter(parent_company=company, status=True)
        for child in children:
            hierarchy['children'].append(get_company_hierarchy_tree(child.id))
        
        return hierarchy
        
    except Company.DoesNotExist:
        return {}


@api_view(['POST'])
@permission_classes([IsAdminUser])
def refresh_user_permissions(request):
    """사용자 권한 캐시 갱신"""
    try:
        user_id = request.data.get('user_id')
        
        if user_id:
            # 특정 사용자 권한 갱신
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': '사용자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 캐시 삭제 후 재생성
            cache_patterns = [
                f'user_full_permissions:{user_id}',
                f'accessible_companies:{user_id}',
                f'user:{user_id}:*',
            ]
            
            for pattern in cache_patterns:
                cache_manager.delete_pattern(pattern)
            
            # 권한 정보 재생성
            new_permissions = HierarchicalPermissionManager.get_user_permissions(target_user)
            
            logger.info(f"사용자 권한 캐시 갱신: {target_user.username}")
            
            return Response({
                'message': f'사용자 {target_user.username}의 권한이 갱신되었습니다.',
                'permissions': new_permissions,
            })
        else:
            # 모든 사용자 권한 캐시 갱신
            cache_manager.delete_pattern('user_full_permissions:*')
            cache_manager.delete_pattern('accessible_companies:*')
            
            logger.info("모든 사용자 권한 캐시 갱신")
            
            return Response({
                'message': '모든 사용자의 권한 캐시가 갱신되었습니다.'
            })
            
    except Exception as e:
        logger.error(f"권한 캐시 갱신 실패: {e}")
        return Response({
            'error': '권한 갱신 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('can_view_reports')
def check_report_access(request, report_type):
    """리포트 접근 권한 확인"""
    try:
        user_permissions = HierarchicalPermissionManager.get_user_permissions(request.user)
        combined_permissions = user_permissions.get('combined_permissions', {})
        
        # 리포트 타입별 권한 확인
        access_info = {
            'report_type': report_type,
            'can_view': False,
            'access_level': 'none',
            'accessible_companies': [],
        }
        
        if combined_permissions.get('can_view_all_reports'):
            access_info.update({
                'can_view': True,
                'access_level': 'all',
                'accessible_companies': HierarchicalPermissionManager.get_accessible_companies(request.user),
            })
        elif combined_permissions.get('can_view_subordinate_reports'):
            accessible_companies = HierarchicalPermissionManager.get_accessible_companies(request.user)
            access_info.update({
                'can_view': True,
                'access_level': 'subordinate',
                'accessible_companies': accessible_companies,
            })
        elif combined_permissions.get('can_view_own_reports'):
            user_company_id = user_permissions.get('company_id')
            access_info.update({
                'can_view': True,
                'access_level': 'own',
                'accessible_companies': [user_company_id] if user_company_id else [],
            })
        
        return Response(access_info)
        
    except Exception as e:
        logger.error(f"리포트 접근 권한 확인 실패: {e}")
        return Response({
            'error': '권한 확인 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
"""
Policies 앱 서비스 레이어

비즈니스 로직을 모델과 뷰에서 분리하여 재사용성과 테스트 용이성을 향상시킵니다.
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models import Q, Count, Prefetch
from django.core.cache import cache

from .models import Policy, PolicyAssignment, PolicyNotice, RebateMatrix
from companies.models import Company, CompanyUser

logger = logging.getLogger('policies')


class PolicyService:
    """정책 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def create_policy_with_defaults(policy_data: Dict[str, Any], creator: User) -> Policy:
        """
        정책 생성 시 기본 설정과 함께 생성
        
        Args:
            policy_data: 정책 데이터
            creator: 생성자
        
        Returns:
            생성된 Policy 객체
        """
        try:
            with transaction.atomic():
                # 정책 생성
                policy = Policy.objects.create(
                    created_by=creator,
                    **policy_data
                )
                
                # 기본 리베이트 매트릭스 생성
                if policy_data.get('create_default_matrix', True):
                    RebateMatrix.create_default_matrix(policy)
                
                logger.info(f"정책이 생성되었습니다: {policy.title} (생성자: {creator.username})")
                return policy
                
        except Exception as e:
            logger.error(f"정책 생성 실패: {str(e)}")
            raise ValidationError(f"정책 생성에 실패했습니다: {str(e)}")
    
    @staticmethod
    def bulk_assign_policy(policy_id: str, company_ids: List[str], 
                          custom_rebate: Optional[Decimal] = None,
                          expose_to_child: bool = True) -> Dict[str, Any]:
        """
        정책을 여러 업체에 일괄 배정
        
        Args:
            policy_id: 정책 ID
            company_ids: 업체 ID 목록
            custom_rebate: 커스텀 리베이트
            expose_to_child: 하위 노출 여부
        
        Returns:
            배정 결과
        """
        try:
            with transaction.atomic():
                policy = Policy.objects.get(id=policy_id)
                companies = Company.objects.filter(id__in=company_ids, status=True)
                
                if not companies.exists():
                    raise ValidationError("유효한 업체가 없습니다.")
                
                assignments = policy.assign_to_companies(
                    companies, custom_rebate, expose_to_child
                )
                
                # 캐시 무효화
                PolicyService._invalidate_policy_cache(policy_id)
                
                return {
                    'success': True,
                    'assigned_count': len(assignments),
                    'company_names': [c.name for c in companies]
                }
                
        except Policy.DoesNotExist:
            raise ValidationError("정책을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"정책 일괄 배정 실패: {str(e)}")
            raise ValidationError(f"정책 배정에 실패했습니다: {str(e)}")
    
    @staticmethod
    def get_policy_statistics(user: User) -> Dict[str, Any]:
        """
        사용자별 정책 통계 조회
        
        Args:
            user: 사용자
        
        Returns:
            정책 통계
        """
        cache_key = f"policy_stats_{user.id}"
        stats = cache.get(cache_key)
        
        if stats is None:
            try:
                company_user = CompanyUser.objects.select_related('company').get(django_user=user)
                
                # 접근 가능한 정책들
                if company_user.company.type == 'headquarters':
                    policies = Policy.objects.all()
                else:
                    policies = Policy.objects.filter(
                        Q(assignments__company=company_user.company) |
                        Q(created_by=user)
                    ).distinct()
                
                stats = {
                    'total_policies': policies.count(),
                    'active_policies': policies.filter(status='active').count(),
                    'draft_policies': policies.filter(status='draft').count(),
                    'expired_policies': policies.filter(status='expired').count(),
                    'assigned_policies': PolicyAssignment.objects.filter(
                        company=company_user.company
                    ).count(),
                    'my_policies': policies.filter(created_by=user).count(),
                }
                
                # 30분 캐시
                cache.set(cache_key, stats, 1800)
                
            except CompanyUser.DoesNotExist:
                stats = {
                    'total_policies': 0,
                    'active_policies': 0,
                    'draft_policies': 0,
                    'expired_policies': 0,
                    'assigned_policies': 0,
                    'my_policies': 0,
                }
        
        return stats
    
    @staticmethod
    def get_accessible_policies(user: User, filters: Optional[Dict] = None) -> List[Policy]:
        """
        사용자가 접근 가능한 정책 목록 조회 (최적화된 쿼리)
        
        Args:
            user: 사용자
            filters: 필터 조건
        
        Returns:
            정책 목록
        """
        try:
            company_user = CompanyUser.objects.select_related('company').get(django_user=user)
            
            # 기본 쿼리셋 구성
            if company_user.company.type == 'headquarters':
                queryset = Policy.objects.all()
            else:
                queryset = Policy.objects.filter(
                    Q(assignments__company=company_user.company) |
                    Q(created_by=user)
                ).distinct()
            
            # 필터 적용
            if filters:
                if filters.get('status'):
                    queryset = queryset.filter(status=filters['status'])
                if filters.get('carrier'):
                    queryset = queryset.filter(carrier=filters['carrier'])
                if filters.get('form_type'):
                    queryset = queryset.filter(form_type=filters['form_type'])
                if filters.get('expose') is not None:
                    queryset = queryset.filter(expose=filters['expose'])
            
            # 성능 최적화: 관련 객체 미리 로드
            queryset = queryset.select_related('created_by').prefetch_related(
                Prefetch(
                    'assignments',
                    queryset=PolicyAssignment.objects.select_related('company')
                ),
                'notices'
            )
            
            return list(queryset)
            
        except CompanyUser.DoesNotExist:
            return []
    
    @staticmethod
    def _invalidate_policy_cache(policy_id: str):
        """정책 관련 캐시 무효화"""
        cache_patterns = [
            f"policy_{policy_id}",
            f"policy_stats_*",
            f"policy_list_*",
            f"policy_assignments_{policy_id}",
        ]
        
        for pattern in cache_patterns:
            if '*' in pattern:
                # 패턴 매칭 캐시 삭제는 복잡하므로 전체 캐시 플러시
                cache.clear()
                break
            else:
                cache.delete(pattern)


class PolicyAssignmentService:
    """정책 배정 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def get_assignment_history(company_id: str, page_size: int = 20) -> Dict[str, Any]:
        """
        업체의 정책 배정 이력 조회
        
        Args:
            company_id: 업체 ID
            page_size: 페이지 크기
        
        Returns:
            배정 이력
        """
        try:
            assignments = PolicyAssignment.objects.filter(
                company_id=company_id
            ).select_related(
                'policy', 'policy__created_by'
            ).order_by('-assigned_at')[:page_size]
            
            history = []
            for assignment in assignments:
                history.append({
                    'policy_id': str(assignment.policy.id),
                    'policy_title': assignment.policy.title,
                    'assigned_at': assignment.assigned_at,
                    'custom_rebate': assignment.custom_rebate,
                    'expose_to_child': assignment.expose_to_child,
                    'effective_rebate': assignment.get_effective_rebate(),
                    'rebate_source': assignment.get_rebate_source(),
                })
            
            return {
                'success': True,
                'assignments': history,
                'total_count': PolicyAssignment.objects.filter(company_id=company_id).count()
            }
            
        except Exception as e:
            logger.error(f"정책 배정 이력 조회 실패: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'assignments': [],
                'total_count': 0
            }
    
    @staticmethod
    def bulk_remove_assignments(policy_id: str, company_ids: List[str]) -> Dict[str, Any]:
        """
        정책을 여러 업체에서 일괄 제거
        
        Args:
            policy_id: 정책 ID
            company_ids: 업체 ID 목록
        
        Returns:
            제거 결과
        """
        try:
            with transaction.atomic():
                policy = Policy.objects.get(id=policy_id)
                companies = Company.objects.filter(id__in=company_ids)
                
                removed_count = policy.remove_from_companies(companies)
                
                # 캐시 무효화
                PolicyService._invalidate_policy_cache(policy_id)
                
                return {
                    'success': True,
                    'removed_count': removed_count,
                    'company_names': [c.name for c in companies]
                }
                
        except Policy.DoesNotExist:
            raise ValidationError("정책을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"정책 일괄 제거 실패: {str(e)}")
            raise ValidationError(f"정책 제거에 실패했습니다: {str(e)}")


class RebateCalculationService:
    """리베이트 계산 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def calculate_rebate(policy_id: str, carrier: str, plan_amount: int, 
                        contract_period: int, company_id: Optional[str] = None) -> Dict[str, Any]:
        """
        리베이트 금액 계산
        
        Args:
            policy_id: 정책 ID
            carrier: 통신사
            plan_amount: 요금제 금액
            contract_period: 가입기간
            company_id: 업체 ID (커스텀 리베이트 확인용)
        
        Returns:
            계산된 리베이트 정보
        """
        try:
            policy = Policy.objects.get(id=policy_id)
            
            # 커스텀 리베이트 확인
            if company_id:
                try:
                    assignment = PolicyAssignment.objects.get(
                        policy=policy, company_id=company_id
                    )
                    if assignment.custom_rebate is not None:
                        return {
                            'rebate_amount': assignment.custom_rebate,
                            'rebate_source': 'custom',
                            'policy_title': policy.title,
                            'company_name': assignment.company.name
                        }
                except PolicyAssignment.DoesNotExist:
                    pass
            
            # 리베이트 매트릭스에서 계산
            matrix_rebate = RebateMatrix.get_rebate_amount(
                policy, carrier, plan_amount, contract_period
            )
            
            if matrix_rebate is not None:
                return {
                    'rebate_amount': matrix_rebate,
                    'rebate_source': 'matrix',
                    'policy_title': policy.title,
                    'carrier': carrier,
                    'plan_amount': plan_amount,
                    'contract_period': contract_period
                }
            
            # 기본 리베이트 사용
            return {
                'rebate_amount': policy.rebate_agency,  # 기본값
                'rebate_source': 'default',
                'policy_title': policy.title
            }
            
        except Policy.DoesNotExist:
            raise ValidationError("정책을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"리베이트 계산 실패: {str(e)}")
            raise ValidationError(f"리베이트 계산에 실패했습니다: {str(e)}")

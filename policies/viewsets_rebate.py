"""
리베이트 관련 ViewSet
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from companies.models import Company
from .models import Policy, PolicyExposure, AgencyRebate, RebateMatrix
from .serializers import PolicySerializer
from core.exceptions import ValidationError
from users.models import CompanyUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

logger = logging.getLogger('policies')


class RebateViewSet(viewsets.ViewSet):
    """
    리베이트 조회 및 관리 ViewSet
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='summary')
    def rebate_summary(self, request):
        """
        사용자별 리베이트 현황 조회
        - 본사: 각 협력사에게 지불할 리베이트
        - 협력사: 본사에서 받을 리베이트 + 판매점에게 줄 리베이트
        - 판매점: 협력사에서 받을 리베이트
        """
        try:
            # 현재 사용자의 회사 정보 가져오기
            company_user = CompanyUser.objects.get(django_user=request.user)
            user_company = company_user.company
            
            # 회사 타입 결정
            company_type = user_company.type
            if not company_type and user_company.code:
                if user_company.code.startswith('A-'):
                    company_type = 'headquarters'
                elif user_company.code.startswith('B-'):
                    company_type = 'agency'
                elif user_company.code.startswith('C-'):
                    company_type = 'retail'
            
            rebate_data = []
            
            if company_type == 'headquarters':
                # 본사: 각 협력사에게 지불할 리베이트 조회
                policies = Policy.objects.filter(
                    created_by__companyuser__company=user_company
                ).values('id', 'title', 'rebate_agency')
                
                # 각 정책별로 노출된 협력사들 조회
                for policy in policies:
                    exposures = PolicyExposure.objects.filter(
                        policy_id=policy['id'],
                        is_active=True
                    ).select_related('agency')
                    
                    for exposure in exposures:
                        rebate_data.append({
                            'policy_id': policy['id'],
                            'policy_title': policy['title'],
                            'company_name': exposure.agency.name,
                            'company_type': 'agency',
                            'rebate_amount': policy['rebate_agency'],
                            'rebate_type': '지급할 리베이트',
                            'status': 'active'
                        })
            
            elif company_type == 'agency':
                # 협력사: 본사에서 받을 리베이트 + 판매점에게 줄 리베이트
                
                # 1. 본사에서 받을 리베이트
                exposures = PolicyExposure.objects.filter(
                    agency=user_company,
                    is_active=True
                ).select_related('policy')
                
                for exposure in exposures:
                    rebate_data.append({
                        'policy_id': str(exposure.policy.id),
                        'policy_title': exposure.policy.title,
                        'company_name': '본사',
                        'company_type': 'headquarters',
                        'rebate_amount': exposure.policy.rebate_agency,
                        'rebate_type': '받을 리베이트',
                        'status': 'active'
                    })
                
                # 2. 판매점에게 줄 리베이트
                agency_rebates = AgencyRebate.objects.filter(
                    policy_exposure__agency=user_company,
                    is_active=True
                ).select_related('policy_exposure__policy', 'retail_company')
                
                for rebate in agency_rebates:
                    rebate_data.append({
                        'policy_id': str(rebate.policy_exposure.policy.id),
                        'policy_title': rebate.policy_exposure.policy.title,
                        'company_name': rebate.retail_company.name,
                        'company_type': 'retail',
                        'rebate_amount': rebate.rebate_amount,
                        'rebate_type': '지급할 리베이트',
                        'status': 'active'
                    })
            
            elif company_type == 'retail':
                # 판매점: 협력사에서 받을 리베이트
                agency_rebates = AgencyRebate.objects.filter(
                    retail_company=user_company,
                    is_active=True
                ).select_related('policy_exposure__policy', 'policy_exposure__agency')
                
                for rebate in agency_rebates:
                    rebate_data.append({
                        'policy_id': str(rebate.policy_exposure.policy.id),
                        'policy_title': rebate.policy_exposure.policy.title,
                        'company_name': rebate.policy_exposure.agency.name,
                        'company_type': 'agency',
                        'rebate_amount': rebate.rebate_amount,
                        'rebate_type': '받을 리베이트',
                        'status': 'active'
                    })
            
            return Response({
                'success': True,
                'data': {
                    'user_company': user_company.name,
                    'company_type': company_type,
                    'rebates': rebate_data,
                    'summary': {
                        'total_count': len(rebate_data),
                        'total_amount': sum([r['rebate_amount'] for r in rebate_data]),
                        'receive_amount': sum([r['rebate_amount'] for r in rebate_data if r['rebate_type'] == '받을 리베이트']),
                        'pay_amount': sum([r['rebate_amount'] for r in rebate_data if r['rebate_type'] == '지급할 리베이트'])
                    }
                }
            })
            
        except CompanyUser.DoesNotExist:
            return Response({
                'success': False,
                'error': '유효한 회사 사용자가 아닙니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f'리베이트 현황 조회 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '리베이트 현황 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get', 'post'], url_path='agency')
    def agency_rebate(self, request):
        """
        협력사용 리베이트 설정 및 조회
        """
        try:
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            # 협력사만 접근 가능
            company_type = company_user.company.type
            if not company_type and company_user.company.code:
                if company_user.company.code.startswith('B-'):
                    company_type = 'agency'
            
            if company_type != 'agency':
                return Response({
                    'success': False,
                    'error': '협력사만 접근 가능합니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            if request.method == 'GET':
                # 노출된 정책들 조회
                exposed_policies = PolicyExposure.objects.filter(
                    agency=company_user.company,
                    is_active=True
                ).select_related('policy')
                
                # 하위 판매점들 조회  
                retail_companies = Company.objects.filter(
                    parent_company=company_user.company,
                    code__startswith='C-'
                )
                
                # 기존 설정된 리베이트들 조회
                existing_rebates = AgencyRebate.objects.filter(
                    policy_exposure__agency=company_user.company,
                    is_active=True
                ).select_related('policy_exposure__policy', 'retail_company')
                
                return Response({
                    'success': True,
                    'data': {
                        'exposed_policies': [
                            {
                                'id': str(exp.id),
                                'policy': {
                                    'id': str(exp.policy.id),
                                    'title': exp.policy.title,
                                    'rebate_agency': exp.policy.rebate_agency
                                }
                            }
                            for exp in exposed_policies
                        ],
                        'retail_companies': [
                            {
                                'id': str(company.id),
                                'name': company.name,
                                'code': company.code
                            }
                            for company in retail_companies
                        ],
                        'existing_rebates': [
                            {
                                'id': str(rebate.id),
                                'policy_title': rebate.policy_exposure.policy.title,
                                'retail_company_name': rebate.retail_company.name,
                                'rebate_amount': rebate.rebate_amount,
                                'created_at': rebate.created_at.isoformat()
                            }
                            for rebate in existing_rebates
                        ]
                    }
                })
            
            elif request.method == 'POST':
                # 리베이트 설정
                policy_exposure_id = request.data.get('policy_exposure')
                retail_company_id = request.data.get('retail_company')
                rebate_amount = request.data.get('rebate_amount')
                
                if not all([policy_exposure_id, retail_company_id, rebate_amount]):
                    return Response({
                        'success': False,
                        'error': '필수 항목이 누락되었습니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 정책 노출 확인
                policy_exposure = PolicyExposure.objects.get(
                    id=policy_exposure_id,
                    agency=company_user.company
                )
                
                # 판매점 확인
                retail_company = Company.objects.get(
                    id=retail_company_id,
                    parent_company=company_user.company
                )
                
                # 리베이트 생성 또는 업데이트
                agency_rebate, created = AgencyRebate.objects.update_or_create(
                    policy_exposure=policy_exposure,
                    retail_company=retail_company,
                    defaults={
                        'rebate_amount': rebate_amount,
                        'is_active': True
                    }
                )
                
                return Response({
                    'success': True,
                    'message': '리베이트가 설정되었습니다.',
                    'data': {
                        'id': str(agency_rebate.id),
                        'created': created
                    }
                })
                
        except CompanyUser.DoesNotExist:
            return Response({
                'success': False,
                'error': '유효한 회사 사용자가 아닙니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f'협력사 리베이트 처리 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
정책 노출 관련 ViewSet
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from companies.models import Company
from .models import Policy, PolicyExposure
from .serializers import PolicySerializer
from companies.models import CompanyUser

logger = logging.getLogger('policies')


class PolicyExposureViewSet(viewsets.ViewSet):
    """
    정책 노출 관리 ViewSet
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request, policy_id=None):
        """
        특정 정책의 노출 현황 조회
        """
        try:
            # 정책 존재 확인
            policy = Policy.objects.get(pk=policy_id)
            
            # 현재 사용자의 회사 정보
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            # 본사만 노출 현황을 볼 수 있음
            if not (company_user.company.code and company_user.company.code.startswith('A-')):
                return Response({
                    'success': False,
                    'error': '본사만 정책 노출 현황을 조회할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 노출된 협력사들 조회 (협력사만 - B-코드)
            exposures = PolicyExposure.objects.filter(
                policy=policy,
                is_active=True,
                agency__code__startswith='B-'  # 협력사만 필터링
            ).select_related('agency')
            
            return Response({
                'success': True,
                'data': {
                    'policy': {
                        'id': str(policy.id),
                        'title': policy.title
                    },
                    'exposures': [
                        {
                            'id': str(exposure.id),
                            'agency': {
                                'id': str(exposure.agency.id),
                                'name': exposure.agency.name,
                                'code': exposure.agency.code
                            },
                            'exposed_at': exposure.exposed_at.isoformat(),
                            'exposed_by': exposure.exposed_by.username if exposure.exposed_by else None
                        }
                        for exposure in exposures
                    ]
                }
            })
            
        except Policy.DoesNotExist:
            return Response({
                'success': False,
                'error': '정책을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except CompanyUser.DoesNotExist:
            return Response({
                'success': False,
                'error': '유효한 회사 사용자가 아닙니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f'정책 노출 현황 조회 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, policy_id=None):
        """
        정책을 협력사에 노출
        """
        try:
            # 정책 존재 확인
            policy = Policy.objects.get(pk=policy_id)
            
            # 현재 사용자의 회사 정보
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            # 본사만 정책을 노출할 수 있음
            if not (company_user.company.code and company_user.company.code.startswith('A-')):
                return Response({
                    'success': False,
                    'error': '본사만 정책을 노출할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            agency_ids = request.data.get('agency_ids', [])
            if not agency_ids:
                return Response({
                    'success': False,
                    'error': '노출할 협력사를 선택해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 협력사들 확인
            agencies = Company.objects.filter(
                id__in=agency_ids,
                code__startswith='B-'  # 협력사 코드
            )
            
            if len(agencies) != len(agency_ids):
                return Response({
                    'success': False,
                    'error': '일부 협력사를 찾을 수 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 정책 노출 생성
            exposures_created = []
            retail_exposures_created = []
            
            for agency in agencies:
                # 협력사에 정책 노출
                exposure, created = PolicyExposure.objects.get_or_create(
                    policy=policy,
                    agency=agency,
                    defaults={
                        'is_active': True,
                        'exposed_by': request.user
                    }
                )
                
                if created:
                    exposures_created.append({
                        'agency_name': agency.name,
                        'agency_code': agency.code
                    })
                else:
                    # 기존 노출을 다시 활성화
                    exposure.is_active = True
                    exposure.exposed_by = request.user
                    exposure.save()
                
                # 협력사 하위 판매점들에게도 자동으로 정책 노출
                retail_companies = Company.objects.filter(
                    parent_company=agency,
                    code__startswith='C-'  # 판매점 코드
                )
                
                for retail in retail_companies:
                    retail_exposure, retail_created = PolicyExposure.objects.get_or_create(
                        policy=policy,
                        agency=retail,  # 판매점도 agency 필드에 저장 (모델 구조상)
                        defaults={
                            'is_active': True,
                            'exposed_by': request.user
                        }
                    )
                    
                    if retail_created:
                        retail_exposures_created.append({
                            'retail_name': retail.name,
                            'retail_code': retail.code,
                            'parent_agency': agency.name
                        })
            
            total_retail_count = len(retail_exposures_created)
            message = f'{len(exposures_created)}개 협력사에 정책이 노출되었습니다.'
            if total_retail_count > 0:
                message += f' (하위 판매점 {total_retail_count}개 자동 노출)'
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'exposures_created': exposures_created,
                    'retail_exposures_created': retail_exposures_created
                }
            })
            
        except Policy.DoesNotExist:
            return Response({
                'success': False,
                'error': '정책을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except CompanyUser.DoesNotExist:
            return Response({
                'success': False,
                'error': '유효한 회사 사용자가 아닙니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f'정책 노출 생성 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '노출 설정 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, policy_pk=None, pk=None):
        """
        정책 노출 해제
        """
        try:
            # 정책 노출 확인
            exposure = PolicyExposure.objects.get(
                pk=pk,
                policy_id=policy_pk
            )
            
            # 현재 사용자의 회사 정보
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            # 본사만 노출을 해제할 수 있음
            if not (company_user.company.code and company_user.company.code.startswith('A-')):
                return Response({
                    'success': False,
                    'error': '본사만 정책 노출을 해제할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 노출 해제 (삭제하지 않고 비활성화)
            exposure.is_active = False
            exposure.save()
            
            return Response({
                'success': True,
                'message': f'{exposure.agency.name}에서 정책 노출이 해제되었습니다.'
            })
            
        except PolicyExposure.DoesNotExist:
            return Response({
                'success': False,
                'error': '정책 노출을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except CompanyUser.DoesNotExist:
            return Response({
                'success': False,
                'error': '유효한 회사 사용자가 아닙니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f'정책 노출 해제 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '노출 해제 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

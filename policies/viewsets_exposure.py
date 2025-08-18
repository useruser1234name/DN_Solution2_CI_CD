"""
정책 노출 관련 ViewSet

정책을 협력사에 노출하고, 협력사에서 판매점으로 정책이 자동으로 노출되는 기능을 관리합니다.
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
    
    정책을 협력사에 노출하고, 협력사에서 판매점으로 정책이 자동으로 노출되는 기능을 관리합니다.
    본사 사용자만 정책 노출을 설정할 수 있습니다.
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request, policy_id=None):
        """
        특정 정책의 노출 현황 조회
        
        현재 정책이 노출된 협력사 목록을 반환합니다.
        본사 사용자만 조회할 수 있습니다.
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
        정책을 협력사에 노출 설정/해제
        
        요청 본문의 agency_ids에 포함된 협력사들은 노출 활성화,
        포함되지 않은 협력사들은 노출 비활성화 처리합니다.
        
        이 메소드는 노출 설정과 해제를 모두 처리합니다:
        1. 현재 노출 중이지만 요청에 없는 협력사 -> 노출 해제
        2. 요청에는 있지만 현재 노출 중이 아닌 협력사 -> 노출 활성화
        3. 이미 노출 중이고 계속 노출할 협력사 -> 유지
        
        협력사에 정책을 노출하면 하위 판매점에도 자동으로 정책이 노출됩니다.
        협력사의 정책 노출을 해제하면 하위 판매점의 노출도 함께 해제됩니다.
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
            
            # 요청에서 노출할 협력사 ID 목록 가져오기
            agency_ids = request.data.get('agency_ids', [])
            
            # 현재 노출된 협력사 목록 조회 (협력사만 - B-코드)
            current_exposures = PolicyExposure.objects.filter(
                policy=policy,
                agency__code__startswith='B-',  # 협력사만 필터링
                is_active=True
            ).select_related('agency')
            
            current_agency_ids = [str(exposure.agency.id) for exposure in current_exposures]
            
            logger.info(f"정책 '{policy.title}' 노출 업데이트 - 현재: {len(current_agency_ids)}개, 요청: {len(agency_ids)}개")
            
            # 1. 노출 해제할 협력사 처리 (현재 노출 중이지만 요청에 없는 협력사)
            to_deactivate_ids = [agency_id for agency_id in current_agency_ids if agency_id not in agency_ids]
            
            if to_deactivate_ids:
                # 노출 해제할 협력사 조회
                deactivate_agencies = Company.objects.filter(id__in=to_deactivate_ids)
                deactivate_agency_names = [agency.name for agency in deactivate_agencies]
                
                # 노출 해제
                deactivated_count = PolicyExposure.objects.filter(
                    policy=policy,
                    agency__id__in=to_deactivate_ids
                ).update(is_active=False)
                
                logger.info(f"정책 '{policy.title}' 노출 해제: {deactivated_count}개 협력사 - {', '.join(deactivate_agency_names)}")
                
                # 하위 판매점 노출도 해제
                retail_deactivated_count = PolicyExposure.objects.filter(
                    policy=policy,
                    agency__parent_company__id__in=to_deactivate_ids,
                    agency__code__startswith='C-'  # 판매점 코드
                ).update(is_active=False)
                
                logger.info(f"정책 '{policy.title}' 하위 판매점 노출 해제: {retail_deactivated_count}개")
            
            # 2. 노출 활성화할 협력사 처리 (요청에는 있지만 현재 노출 중이 아닌 협력사)
            to_activate_ids = [agency_id for agency_id in agency_ids if agency_id not in current_agency_ids]
            
            exposures_created = []
            retail_exposures_created = []
            
            if to_activate_ids:
                # 활성화할 협력사 조회
                agencies = Company.objects.filter(
                    id__in=to_activate_ids,
                    code__startswith='B-'  # 협력사 코드
                )
                
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
                        else:
                            # 기존 노출을 다시 활성화
                            retail_exposure.is_active = True
                            retail_exposure.save()
            
            # 3. 이미 노출 중이고 계속 노출할 협력사 처리 (요청에도 있고 현재도 노출 중인 협력사)
            to_keep_ids = [agency_id for agency_id in agency_ids if agency_id in current_agency_ids]
            kept_count = len(to_keep_ids)
            
            # 응답 메시지 생성
            messages = []
            
            if exposures_created:
                messages.append(f"{len(exposures_created)}개 협력사 노출 추가")
            
            if to_deactivate_ids:
                messages.append(f"{len(to_deactivate_ids)}개 협력사 노출 해제")
            
            if kept_count:
                messages.append(f"{kept_count}개 협력사 노출 유지")
            
            if retail_exposures_created:
                messages.append(f"{len(retail_exposures_created)}개 하위 판매점 노출 추가")
            
            message = ", ".join(messages) if messages else "변경사항 없음"
            
            return Response({
                'success': True,
                'message': message,
                'data': {
                    'exposures_created': exposures_created,
                    'exposures_deactivated': len(to_deactivate_ids),
                    'exposures_kept': kept_count,
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
            logger.error(f'정책 노출 설정 오류: {str(e)}')
            return Response({
                'success': False,
                'error': '노출 설정 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, policy_pk=None, pk=None, policy_id=None):
        """
        정책 노출 해제
        
        URL 패턴에 따라 policy_pk 또는 policy_id를 사용
        
        두 가지 방식으로 작동:
        1. pk가 제공된 경우: 특정 노출 레코드 하나를 비활성화
           - 협력사인 경우 하위 판매점도 함께 비활성화
        2. pk가 없는 경우: 요청 본문의 agency_ids를 사용하여 여러 협력사의 노출을 일괄 비활성화
           - 각 협력사의 하위 판매점도 함께 비활성화
        
        참고: 이 메소드는 create 메소드로 대체될 수 있으며, 
        create 메소드는 노출 설정과 해제를 모두 처리합니다.
        """
        try:
            # URL 패턴에 따라 정책 ID 결정
            policy_identifier = policy_pk or policy_id
            
            # 정책 존재 확인
            policy = Policy.objects.get(pk=policy_identifier)
            
            # 현재 사용자의 회사 정보
            company_user = CompanyUser.objects.get(django_user=request.user)
            
            # 본사만 노출을 해제할 수 있음
            if not (company_user.company.code and company_user.company.code.startswith('A-')):
                return Response({
                    'success': False,
                    'error': '본사만 정책 노출을 해제할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # pk가 제공된 경우 (특정 노출 해제)
            if pk:
                # 정책 노출 확인
                exposure = PolicyExposure.objects.get(
                    pk=pk,
                    policy_id=policy_identifier
                )
                
                # 노출 해제 (삭제하지 않고 비활성화)
                exposure.is_active = False
                exposure.save()
                
                # 협력사인 경우 하위 판매점도 노출 해제
                if exposure.agency.code and exposure.agency.code.startswith('B-'):
                    # 하위 판매점 찾기
                    retail_companies = Company.objects.filter(
                        parent_company=exposure.agency
                    )
                    
                    # 하위 판매점 노출 해제
                    retail_exposures = PolicyExposure.objects.filter(
                        policy=policy,
                        agency__in=retail_companies
                    )
                    
                    retail_count = retail_exposures.update(is_active=False)
                    logger.info(f"정책 노출 해제: {policy.title} -> {exposure.agency.name} (하위 판매점 {retail_count}개 포함)")
                    
                    return Response({
                        'success': True,
                        'message': f'{exposure.agency.name}에서 정책 노출이 해제되었습니다. (하위 판매점 {retail_count}개 포함)'
                    })
                
                logger.info(f"정책 노출 해제: {policy.title} -> {exposure.agency.name}")
                return Response({
                    'success': True,
                    'message': f'{exposure.agency.name}에서 정책 노출이 해제되었습니다.'
                })
            
            # pk가 제공되지 않은 경우 (요청 본문에서 agency_ids 사용)
            else:
                agency_ids = request.data.get('agency_ids', [])
                if not agency_ids:
                    return Response({
                        'success': False,
                        'error': '노출 해제할 협력사를 선택해주세요.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # 협력사 노출 해제
                exposures = PolicyExposure.objects.filter(
                    policy=policy,
                    agency__id__in=agency_ids
                )
                
                if not exposures.exists():
                    return Response({
                        'success': False,
                        'error': '해당 협력사에 노출된 정책이 없습니다.'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # 협력사 목록 저장
                agencies = Company.objects.filter(id__in=agency_ids)
                agency_names = [agency.name for agency in agencies]
                
                # 노출 해제
                agency_count = exposures.update(is_active=False)
                
                # 하위 판매점 노출 해제
                retail_exposures = PolicyExposure.objects.filter(
                    policy=policy,
                    agency__parent_company__id__in=agency_ids
                )
                
                retail_count = retail_exposures.update(is_active=False)
                
                logger.info(f"정책 노출 일괄 해제: {policy.title} -> {agency_count}개 협력사 (하위 판매점 {retail_count}개 포함)")
                return Response({
                    'success': True,
                    'message': f'{agency_count}개 협력사에서 정책 노출이 해제되었습니다. (하위 판매점 {retail_count}개 포함)'
                })
            
        except Policy.DoesNotExist:
            return Response({
                'success': False,
                'error': '정책을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
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

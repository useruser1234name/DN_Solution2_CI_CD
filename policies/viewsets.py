# -*- coding: utf-8 -*-
"""
정책 관리 REST API ViewSet
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from django.db.models import Q
from .models import Policy, PolicyAssignment
from .serializers import PolicySerializer
import logging

logger = logging.getLogger('policies')


class PolicyViewSet(viewsets.ModelViewSet):
    """정책 REST API ViewSet"""
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]  # JSON만 렌더링
    
    def get_serializer_context(self):
        """시리얼라이저에 request context 전달"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """사용자 권한에 따른 정책 필터링"""
        user = self.request.user
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            company = company_user.company
            
            # 본사는 모든 정책 조회 가능
            if company.type == 'headquarters':
                return Policy.objects.all()
            else:
                # 협력사는 노출된 정책만 조회
                if company.type == 'agency':
                    # 협력사는 본사가 노출한 정책들만 조회
                    from .models import PolicyExposure
                    return Policy.objects.filter(
                        exposures__agency=company,
                        exposures__is_active=True
                    ).distinct()
                else:
                    # 판매점은 자신에게 노출된 정책과 상위 협력사에 노출된 정책 모두 조회
                    from .models import PolicyExposure
                    
                    # 판매점의 상위 협력사 확인
                    parent_agency = company.parent_company
                    
                    if parent_agency and parent_agency.type == 'agency':
                        # 판매점 자신에게 직접 노출된 정책 또는 상위 협력사에 노출된 정책 조회
                        return Policy.objects.filter(
                            Q(exposures__agency=company, exposures__is_active=True) |
                            Q(exposures__agency=parent_agency, exposures__is_active=True)
                        ).distinct()
                    else:
                        # 상위 협력사가 없는 경우 자신에게 직접 노출된 정책만 조회
                        return Policy.objects.filter(
                            exposures__agency=company,
                            exposures__is_active=True
                        ).distinct()
        return Policy.objects.none()
    
    def list(self, request, *args, **kwargs):
        """정책 목록 조회"""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"정책 목록 조회 실패: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        """정책 생성"""
        try:
            # 권한 확인 - 본사만 정책 생성 가능
            if not hasattr(request.user, 'companyuser'):
                return Response({
                    'success': False,
                    'error': '권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            company_user = request.user.companyuser
            if company_user.company.type != 'headquarters':
                return Response({
                    'success': False,
                    'error': '본사만 정책을 생성할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # 정책 생성 (created_by만 설정)
                policy = serializer.save(created_by=request.user)
                
                logger.info(f"정책 생성 성공: {policy.title} (ID: {policy.id})")
                
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'id': str(policy.id)
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"정책 생성 실패: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """정책 수정"""
        try:
            instance = self.get_object()
            
            # 권한 확인
            if not hasattr(request.user, 'companyuser'):
                return Response({
                    'success': False,
                    'error': '권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            company_user = request.user.companyuser
            # 본사만 정책 수정 가능
            if company_user.company.type != 'headquarters':
                return Response({
                    'success': False,
                    'error': '본사만 정책을 수정할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                policy = serializer.save()
                logger.info(f"정책 수정 성공: {policy.title} (ID: {policy.id})")
                
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"정책 수정 실패: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """정책 삭제"""
        try:
            instance = self.get_object()
            
            # 권한 확인
            if not hasattr(request.user, 'companyuser'):
                return Response({
                    'success': False,
                    'error': '권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            company_user = request.user.companyuser
            # 본사만 정책 삭제 가능
            if company_user.company.type != 'headquarters':
                return Response({
                    'success': False,
                    'error': '본사만 정책을 삭제할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            policy_title = instance.title
            policy_id = instance.id
            instance.delete()
            
            logger.info(f"정책 삭제 성공: {policy_title} (ID: {policy_id})")
            
            return Response({
                'success': True,
                'message': '정책이 삭제되었습니다.'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"정책 삭제 실패: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # rebate-matrix 액션 제거됨 - policies/views.py의 PolicyRebateMatrixView에서 처리

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """정책 할당"""
        policy = self.get_object()
        company_id = request.data.get('company_id')
        
        try:
            from companies.models import Company
            target_company = Company.objects.get(id=company_id)
            
            # 권한 확인
            if not hasattr(request.user, 'companyuser'):
                return Response({
                    'success': False,
                    'error': '권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            company_user = request.user.companyuser
            
            # 본사는 모든 회사에 할당 가능
            # 다른 회사는 자신의 하위 회사에만 할당 가능
            if company_user.company.type != 'headquarters':
                if target_company.parent_company != company_user.company:
                    return Response({
                        'success': False,
                        'error': '하위 회사에만 정책을 할당할 수 있습니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # 정책 할당
            assignment, created = PolicyAssignment.objects.get_or_create(
                policy=policy,
                company=target_company,
                defaults={'assigned_to_name': target_company.name}
            )
            
            if created:
                logger.info(f"정책 할당: {policy.title} -> {target_company.name}")
                message = '정책이 할당되었습니다.'
            else:
                message = '이미 할당된 정책입니다.'
            
            return Response({
                'success': True,
                'message': message
            })
            
        except Company.DoesNotExist:
            return Response({
                'success': False,
                'error': '회사를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"정책 할당 실패: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
from django.db import transaction
from .models import Policy, PolicyAssignment, PolicyExposure
from .serializers import PolicySerializer, PolicyAssignmentSerializer, PolicyAssignmentListSerializer
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
        # 슈퍼유저/스태프는 전체 조회 허용
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return Policy.objects.all()
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            company = company_user.company
            
            # 본사는 모든 정책 조회 가능
            if company.type == 'headquarters':
                return Policy.objects.all()
            else:
                # 협력사/판매점: 할당 또는 노출된 정책 + 활성 상태만 조회
                if company.type == 'agency':
                    return Policy.objects.filter(
                        Q(assignments__company=company) |
                        Q(exposures__agency=company, exposures__is_active=True),
                        is_active=True
                    ).distinct()
                else:
                    # 판매점은 자신에게 할당된 정책 또는
                    # 자신/상위 협력사에 노출된 정책 모두 조회
                    
                    # 판매점의 상위 협력사 확인
                    parent_agency = company.parent_company
                    
                    if parent_agency and parent_agency.type == 'agency':
                        return Policy.objects.filter(
                            Q(assignments__company=company) |
                            Q(exposures__agency=company, exposures__is_active=True) |
                            Q(exposures__agency=parent_agency, exposures__is_active=True),
                            is_active=True
                        ).distinct()
                    else:
                        # 상위 협력사가 없는 경우 자신에게 직접 할당/노출된 정책만 조회
                        return Policy.objects.filter(
                            Q(assignments__company=company) |
                            Q(exposures__agency=company, exposures__is_active=True),
                            is_active=True
                        ).distinct()
        # 회사 정보가 없는 인증 사용자: 활성+노출 정책만 노출 (안전 기본값)
        return Policy.objects.filter(is_active=True, status='active', expose=True)
    
    def list(self, request, *args, **kwargs):
        """정책 목록 조회"""
        try:
            queryset = self.get_queryset()
            # 추가 필터: 상태/노출
            only_active = request.query_params.get('only_active')
            exposed = request.query_params.get('exposed')
            if only_active in ['1', 'true', 'True']:
                queryset = queryset.filter(is_active=True)
            # 노출(expose)은 본사 계정에서만 직접 필터
            if exposed in ['1', 'true', 'True']:
                user = request.user
                is_hq = False
                if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
                    is_hq = True
                elif hasattr(user, 'companyuser'):
                    is_hq = getattr(user.companyuser.company, 'type', '') == 'headquarters'
                if is_hq:
                    queryset = queryset.filter(expose=True)
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
                'error': '정책 생성 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get', 'post', 'delete'], url_path='assignments')
    def assignments(self, request, pk=None):
        """정책 배정 하위 리소스: 리스트/생성/삭제"""
        policy = self.get_object()

        # 권한 컨텍스트
        user = request.user
        company_user = getattr(user, 'companyuser', None)

        # 리스트
        if request.method == 'GET':
            qs = PolicyAssignment.objects.filter(policy=policy).select_related('company', 'policy')
            # 협력사는 자기/하위만 노출
            if company_user and company_user.company.type == 'agency':
                qs = qs.filter(company__in=[company_user.company] + list(company_user.company.company_set.all()))
            elif company_user and company_user.company.type == 'retail':
                qs = qs.filter(company=company_user.company)

            serializer = PolicyAssignmentListSerializer(qs, many=True)
            return Response({'success': True, 'data': serializer.data})

        # 생성
        if request.method == 'POST':
            if not company_user:
                return Response({'success': False, 'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

            if company_user.company.type not in ['headquarters', 'agency']:
                return Response({'success': False, 'error': '배정 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

            company_id = request.data.get('company') or request.data.get('company_id')
            custom_rebate = request.data.get('custom_rebate', None)
            expose_to_child = request.data.get('expose_to_child', True)

            if not company_id:
                return Response({'success': False, 'error': 'company_id가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

            from companies.models import Company
            try:
                target_company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return Response({'success': False, 'error': '대상 업체를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

            # 권한: 협력사는 자기 하위만
            if company_user.company.type == 'agency' and target_company.parent_company != company_user.company:
                return Response({'success': False, 'error': '하위 업체에만 배정할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

            # 생성 or 중복 검사
            obj, created = PolicyAssignment.objects.get_or_create(
                policy=policy,
                company=target_company,
                defaults={
                    'assigned_to_name': target_company.name,
                    'custom_rebate': custom_rebate,
                    'expose_to_child': expose_to_child,
                }
            )
            if not created:
                return Response({'success': False, 'error': '이미 배정되어 있습니다.'}, status=status.HTTP_409_CONFLICT)

            serializer = PolicyAssignmentListSerializer(obj)
            return Response({'success': True, 'data': serializer.data, 'assignment_count': policy.get_assignment_count()}, status=status.HTTP_201_CREATED)

        # 삭제 (배치)
        if request.method == 'DELETE':
            if not company_user:
                return Response({'success': False, 'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
            ids = request.data.get('ids') or request.data.get('company_ids')
            if not ids or not isinstance(ids, list):
                return Response({'success': False, 'error': 'ids 리스트가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                PolicyAssignment.objects.filter(policy=policy, company_id__in=ids).delete()
            return Response({'success': True, 'assignment_count': policy.get_assignment_count()}, status=status.HTTP_200_OK)

        return Response({'success': False, 'error': '허용되지 않은 메서드'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
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
    
    @action(detail=False, methods=['get'], url_path='visibility-diagnostics')
    def visibility_diagnostics(self, request):
        """현재 사용자 기준 정책 가시성 진단 API"""
        try:
            user = request.user
            diagnostics = []
            policies = Policy.objects.all()
            company = getattr(getattr(user, 'companyuser', None), 'company', None)

            for p in policies:
                entry = {
                    'id': str(p.id),
                    'title': p.title,
                    'status': p.status,
                    'is_active': p.is_active,
                    'expose_flag': p.expose,
                    'matched_by': None,
                    'hidden_reason': None,
                }

                if not p.is_active or p.status != 'active':
                    entry['hidden_reason'] = 'policy_inactive'
                if company is None:
                    # 회사정보 없으면 expose_flag로만 판단
                    if p.is_active and p.status == 'active' and p.expose:
                        entry['matched_by'] = 'expose_flag'
                    else:
                        entry['hidden_reason'] = entry['hidden_reason'] or 'no_company_and_not_exposed'
                else:
                    if company.type == 'headquarters':
                        entry['matched_by'] = 'headquarters'
                    elif company.type == 'agency':
                        has_assign = p.assignments.filter(company=company).exists()
                        has_exposure = p.exposures.filter(agency=company, is_active=True).exists()
                        if has_assign:
                            entry['matched_by'] = 'direct_assignment'
                        elif has_exposure:
                            entry['matched_by'] = 'direct_exposure'
                        else:
                            entry['hidden_reason'] = entry['hidden_reason'] or 'no_direct_assignment_or_exposure'
                    elif company.type == 'retail':
                        parent_agency = company.parent_company
                        has_assign = p.assignments.filter(company=company).exists()
                        direct_exp = p.exposures.filter(agency=company, is_active=True).exists()
                        parent_exp = bool(parent_agency and p.exposures.filter(agency=parent_agency, is_active=True).exists())
                        if has_assign:
                            entry['matched_by'] = 'direct_assignment'
                        elif direct_exp:
                            entry['matched_by'] = 'direct_exposure'
                        elif parent_exp:
                            entry['matched_by'] = 'parent_exposure'
                        else:
                            entry['hidden_reason'] = entry['hidden_reason'] or 'no_assignment_or_exposure'

                diagnostics.append(entry)

            return Response({'success': True, 'data': diagnostics})
        except Exception as e:
            logger.error(f"가시성 진단 실패: {str(e)}")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # rebate-matrix 액션 제거됨 - policies/views.py의 PolicyRebateMatrixView에서 처리

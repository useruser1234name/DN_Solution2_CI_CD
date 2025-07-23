# policies/views.py
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from companies.models import Company
from .models import Policy, PolicyAssignment
from .serializers import (
    PolicySerializer, PolicyAssignmentSerializer,
    PolicyHtmlGenerateSerializer, PolicyBulkAssignmentSerializer,
    PolicyExposeToggleSerializer, PolicyBulkDeleteSerializer
)

logger = logging.getLogger('policies')


class PolicyViewSet(viewsets.ModelViewSet):
    """
    정책 관리를 위한 ViewSet
    정책의 CRUD 작업과 HTML 자동 생성, 배정 관리 기능 제공
    """
    
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['form_type', 'expose', 'created_by']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 관련 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related('created_by').prefetch_related('assignments__company')
        
        logger.info(f"정책 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """정책 생성"""
        logger.info(f"정책 생성 요청 시작 - 사용자: {request.user}")
        
        try:
            # 생성자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['created_by'] = request.user.id
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                policy = serializer.save()
            
            logger.info(f"정책 생성 성공: {policy.title} (ID: {policy.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"정책 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "정책 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """정책 정보 수정"""
        instance = self.get_object()
        logger.info(f"정책 정보 수정 요청: {instance.title} (ID: {instance.id})")
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                policy = serializer.save()
            
            logger.info(f"정책 정보 수정 성공: {policy.title}")
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"정책 정보 수정 실패: {str(e)} - 정책: {instance.title}")
            return Response(
                {"error": "정책 정보 수정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """정책 삭제"""
        instance = self.get_object()
        logger.info(f"정책 삭제 요청: {instance.title} (ID: {instance.id})")
        
        try:
            # 연관된 배정 정보 확인
            assignments_count = instance.assignments.count()
            
            if assignments_count > 0:
                logger.warning(f"배정된 업체가 있는 정책 삭제 시도: {instance.title} (배정 수: {assignments_count})")
                return Response(
                    {"error": f"이 정책은 {assignments_count}개 업체에 배정되어 있습니다. 먼저 배정을 해제해주세요."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                policy_title = instance.title
                instance.delete()
            
            logger.info(f"정책 삭제 성공: {policy_title}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"정책 삭제 실패: {str(e)} - 정책: {instance.title}")
            return Response(
                {"error": "정책 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def generate_html(self, request, pk=None):
        """
        정책 HTML 상세페이지 생성/재생성 기능
        정책 데이터를 기반으로 HTML 템플릿 자동 생성
        """
        policy = self.get_object()
        logger.info(f"정책 HTML 생성 요청: {policy.title}")
        
        try:
            # 기존 HTML이 있더라도 강제 재생성
            old_html = policy.html_content
            policy.html_content = None
            policy.generate_html_content()
            policy.save()
            
            logger.info(f"정책 HTML 생성 성공: {policy.title}")
            
            return Response({
                'message': f'{policy.title}의 HTML 상세페이지가 생성되었습니다.',
                'policy_id': str(policy.id),
                'html_length': len(policy.html_content) if policy.html_content else 0,
                'regenerated': bool(old_html)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"정책 HTML 생성 실패: {str(e)} - 정책: {policy.title}")
            return Response(
                {"error": "HTML 생성 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def toggle_expose(self, request, pk=None):
        """
        정책 노출 상태 전환 기능
        정책의 프론트엔드 노출 여부를 On/Off로 전환
        """
        policy = self.get_object()
        logger.info(f"정책 노출 상태 전환 요청: {policy.title} (현재 상태: {policy.expose})")
        
        try:
            success = policy.toggle_expose()
            
            if success:
                expose_text = "노출" if policy.expose else "비노출"
                logger.info(f"정책 노출 상태 전환 성공: {policy.title} - {expose_text}")
                
                return Response({
                    'message': f'{policy.title}의 노출 상태가 {expose_text}으로 변경되었습니다.',
                    'policy_id': str(policy.id),
                    'new_expose_status': policy.expose
                }, status=status.HTTP_200_OK)
            else:
                logger.error(f"정책 노출 상태 전환 실패: {policy.title}")
                return Response(
                    {"error": "노출 상태 전환 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f"정책 노출 상태 전환 중 예외 발생: {str(e)} - 정책: {policy.title}")
            return Response(
                {"error": "노출 상태 전환 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        정책 일괄 삭제 기능
        여러 정책을 선택하여 동시에 삭제
        """
        logger.info(f"정책 일괄 삭제 요청 - 사용자: {request.user}")
        
        serializer = PolicyBulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"정책 일괄 삭제 요청 데이터 검증 실패: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        policy_ids = serializer.validated_data['policy_ids']
        force_delete = serializer.validated_data['force_delete']
        
        try:
            with transaction.atomic():
                policies = Policy.objects.filter(id__in=policy_ids)
                deleted_policies = []
                failed_policies = []
                
                for policy in policies:
                    try:
                        # 배정된 업체가 있는지 확인
                        assignments_count = policy.assignments.count()
                        if assignments_count > 0 and not force_delete:
                            failed_policies.append({
                                'id': str(policy.id),
                                'title': policy.title,
                                'reason': f'{assignments_count}개 업체에 배정됨'
                            })
                            continue
                        
                        # 강제 삭제 시 배정 정보도 함께 삭제됨 (CASCADE)
                        deleted_policies.append({
                            'id': str(policy.id),
                            'title': policy.title
                        })
                        policy.delete()
                    
                    except Exception as e:
                        logger.error(f"개별 정책 삭제 실패: {policy.title} - {str(e)}")
                        failed_policies.append({
                            'id': str(policy.id),
                            'title': policy.title,
                            'reason': str(e)
                        })
                
                logger.info(f"정책 일괄 삭제 완료 - 성공: {len(deleted_policies)}, 실패: {len(failed_policies)}")
                
                return Response({
                    'message': f'{len(deleted_policies)}개 정책이 삭제되었습니다.',
                    'deleted': deleted_policies,
                    'failed': failed_policies
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"정책 일괄 삭제 중 전체 오류 발생: {str(e)}")
            return Response(
                {"error": "일괄 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """
        특정 정책의 배정 목록 조회
        """
        policy = self.get_object()
        logger.info(f"정책 배정 목록 조회: {policy.title}")
        
        try:
            assignments = policy.assignments.all().select_related('company').order_by('-assigned_at')
            serializer = PolicyAssignmentSerializer(assignments, many=True)
            
            return Response({
                'policy_id': str(policy.id),
                'policy_title': policy.title,
                'assignments': serializer.data,
                'total_count': len(serializer.data)
            })
        
        except Exception as e:
            logger.error(f"정책 배정 목록 조회 실패: {str(e)} - 정책: {policy.title}")
            return Response(
                {"error": "배정 목록 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def bulk_assign(self, request, pk=None):
        """
        정책을 여러 업체에 일괄 배정
        """
        policy = self.get_object()
        logger.info(f"정책 일괄 배정 요청: {policy.title}")
        
        try:
            # 요청 데이터에 정책 ID 추가
            mutable_data = request.data.copy()
            mutable_data['policy_id'] = str(policy.id)
            
            serializer = PolicyBulkAssignmentSerializer(data=mutable_data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            company_ids = serializer.validated_data['company_ids']
            custom_rebate = serializer.validated_data.get('custom_rebate')
            expose_to_child = serializer.validated_data['expose_to_child']
            
            with transaction.atomic():
                companies = Company.objects.filter(id__in=company_ids, status=True)
                created_assignments = []
                failed_assignments = []
                
                for company in companies:
                    try:
                        # 중복 배정 확인
                        existing = PolicyAssignment.objects.filter(policy=policy, company=company).exists()
                        if existing:
                            failed_assignments.append({
                                'company_id': str(company.id),
                                'company_name': company.name,
                                'reason': '이미 배정됨'
                            })
                            continue
                        
                        # 배정 생성
                        assignment = PolicyAssignment.objects.create(
                            policy=policy,
                            company=company,
                            custom_rebate=custom_rebate,
                            expose_to_child=expose_to_child
                        )
                        
                        created_assignments.append({
                            'assignment_id': str(assignment.id),
                            'company_id': str(company.id),
                            'company_name': company.name,
                            'effective_rebate': float(assignment.get_effective_rebate())
                        })
                    
                    except Exception as e:
                        logger.error(f"개별 정책 배정 실패: {policy.title} → {company.name} - {str(e)}")
                        failed_assignments.append({
                            'company_id': str(company.id),
                            'company_name': company.name,
                            'reason': str(e)
                        })
                
                logger.info(f"정책 일괄 배정 완료: {policy.title} - 성공: {len(created_assignments)}, 실패: {len(failed_assignments)}")
                
                return Response({
                    'message': f'{policy.title}이 {len(created_assignments)}개 업체에 배정되었습니다.',
                    'created': created_assignments,
                    'failed': failed_assignments
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"정책 일괄 배정 중 오류 발생: {str(e)} - 정책: {policy.title}")
            return Response(
                {"error": "일괄 배정 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PolicyAssignmentViewSet(viewsets.ModelViewSet):
    """
    정책 배정 관리를 위한 ViewSet
    업체에 정책을 배정하고 관리하는 기능 제공
    """
    
    queryset = PolicyAssignment.objects.all()
    serializer_class = PolicyAssignmentSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['policy', 'company', 'expose_to_child']
    search_fields = ['policy__title', 'company__name']
    ordering_fields = ['assigned_at']
    ordering = ['-assigned_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 관련 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related('policy', 'company')
        
        logger.info(f"정책 배정 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """정책 배정 생성"""
        logger.info(f"정책 배정 생성 요청 - 사용자: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                assignment = serializer.save()
            
            logger.info(f"정책 배정 생성 성공: {assignment.policy.title} → {assignment.company.name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"정책 배정 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "정책 배정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """정책 배정 정보 수정"""
        instance = self.get_object()
        logger.info(f"정책 배정 수정 요청: {instance.policy.title} → {instance.company.name}")
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                assignment = serializer.save()
            
            logger.info(f"정책 배정 수정 성공: {assignment.policy.title} → {assignment.company.name}")
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"정책 배정 수정 실패: {str(e)} - 배정: {instance.policy.title} → {instance.company.name}")
            return Response(
                {"error": "정책 배정 수정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """정책 배정 해제"""
        instance = self.get_object()
        logger.info(f"정책 배정 해제 요청: {instance.policy.title} → {instance.company.name}")
        
        try:
            with transaction.atomic():
                policy_title = instance.policy.title
                company_name = instance.company.name
                instance.delete()
            
            logger.info(f"정책 배정 해제 성공: {policy_title} → {company_name}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"정책 배정 해제 실패: {str(e)} - 배정: {instance.policy.title} → {instance.company.name}")
            return Response(
                {"error": "정책 배정 해제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """
        특정 업체에 배정된 정책 목록 조회
        """
        company_id = request.query_params.get('company_id')
        
        if not company_id:
            return Response(
                {"error": "company_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            company = get_object_or_404(Company, id=company_id)
            logger.info(f"업체별 정책 배정 목록 조회: {company.name}")
            
            assignments = self.get_queryset().filter(company=company).order_by('-assigned_at')
            serializer = self.get_serializer(assignments, many=True)
            
            return Response({
                'company_id': str(company.id),
                'company_name': company.name,
                'assignments': serializer.data,
                'total_count': len(serializer.data)
            })
        
        except Exception as e:
            logger.error(f"업체별 정책 배정 목록 조회 실패: {str(e)} - 업체 ID: {company_id}")
            return Response(
                {"error": "배정 목록 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def by_policy(self, request):
        """
        특정 정책이 배정된 업체 목록 조회
        """
        policy_id = request.query_params.get('policy_id')
        
        if not policy_id:
            return Response(
                {"error": "policy_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책별 업체 배정 목록 조회: {policy.title}")
            
            assignments = self.get_queryset().filter(policy=policy).order_by('-assigned_at')
            serializer = self.get_serializer(assignments, many=True)
            
            return Response({
                'policy_id': str(policy.id),
                'policy_title': policy.title,
                'assignments': serializer.data,
                'total_count': len(serializer.data)
            })
        
        except Exception as e:
            logger.error(f"정책별 업체 배정 목록 조회 실패: {str(e)} - 정책 ID: {policy_id}")
            return Response(
                {"error": "배정 목록 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
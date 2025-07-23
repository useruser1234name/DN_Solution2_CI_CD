# companies/views.py
import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Company, CompanyUser, CompanyMessage
from .serializers import (
    CompanySerializer, CompanyUserSerializer, CompanyMessageSerializer,
    CompanyBulkDeleteSerializer, CompanyStatusToggleSerializer
)

logger = logging.getLogger('companies')


class CompanyViewSet(viewsets.ModelViewSet):
    """
    업체 관리를 위한 ViewSet
    업체의 CRUD 작업과 추가 기능들을 제공
    """
    
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'status', 'visible']
    search_fields = ['name', 'default_courier']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 관련 사용자 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.prefetch_related('users')
        
        logger.info(f"업체 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """업체 생성"""
        logger.info(f"업체 생성 요청 시작 - 사용자: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                company = serializer.save()
            
            logger.info(f"업체 생성 성공: {company.name} (ID: {company.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"업체 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "업체 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """업체 정보 수정"""
        instance = self.get_object()
        logger.info(f"업체 정보 수정 요청: {instance.name} (ID: {instance.id})")
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                company = serializer.save()
            
            logger.info(f"업체 정보 수정 성공: {company.name}")
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"업체 정보 수정 실패: {str(e)} - 업체: {instance.name}")
            return Response(
                {"error": "업체 정보 수정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """업체 삭제"""
        instance = self.get_object()
        logger.info(f"업체 삭제 요청: {instance.name} (ID: {instance.id})")
        
        try:
            # 연관된 데이터 확인
            users_count = instance.users.count()
            messages_count = instance.messages.count()
            
            if users_count > 0:
                logger.warning(f"사용자가 있는 업체 삭제 시도: {instance.name} (사용자 수: {users_count})")
                return Response(
                    {"error": f"이 업체에는 {users_count}명의 사용자가 있습니다. 먼저 사용자를 삭제해주세요."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                instance.delete()
            
            logger.info(f"업체 삭제 성공: {instance.name}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"업체 삭제 실패: {str(e)} - 업체: {instance.name}")
            return Response(
                {"error": "업체 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        업체 일괄 삭제 기능
        여러 업체를 선택하여 동시에 삭제
        """
        logger.info(f"업체 일괄 삭제 요청 - 사용자: {request.user}")
        
        serializer = CompanyBulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"업체 일괄 삭제 요청 데이터 검증 실패: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        company_ids = serializer.validated_data['company_ids']
        
        try:
            with transaction.atomic():
                companies = Company.objects.filter(id__in=company_ids)
                deleted_companies = []
                failed_companies = []
                
                for company in companies:
                    try:
                        # 연관된 사용자가 있는지 확인
                        if company.users.exists():
                            failed_companies.append({
                                'id': str(company.id),
                                'name': company.name,
                                'reason': '연관된 사용자가 있음'
                            })
                            continue
                        
                        deleted_companies.append({
                            'id': str(company.id),
                            'name': company.name
                        })
                        company.delete()
                    
                    except Exception as e:
                        logger.error(f"개별 업체 삭제 실패: {company.name} - {str(e)}")
                        failed_companies.append({
                            'id': str(company.id),
                            'name': company.name,
                            'reason': str(e)
                        })
                
                logger.info(f"업체 일괄 삭제 완료 - 성공: {len(deleted_companies)}, 실패: {len(failed_companies)}")
                
                return Response({
                    'message': f'{len(deleted_companies)}개 업체가 삭제되었습니다.',
                    'deleted': deleted_companies,
                    'failed': failed_companies
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"업체 일괄 삭제 중 전체 오류 발생: {str(e)}")
            return Response(
                {"error": "일괄 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        업체 운영 상태 전환 기능
        업체의 운영 상태를 On/Off로 전환
        """
        company = self.get_object()
        logger.info(f"업체 상태 전환 요청: {company.name} (현재 상태: {company.status})")
        
        try:
            old_status = company.status
            success = company.toggle_status()
            
            if success:
                status_text = "운영중" if company.status else "중단"
                logger.info(f"업체 상태 전환 성공: {company.name} - {status_text}")
                
                return Response({
                    'message': f'{company.name}의 운영 상태가 {status_text}으로 변경되었습니다.',
                    'company_id': str(company.id),
                    'new_status': company.status
                }, status=status.HTTP_200_OK)
            else:
                logger.error(f"업체 상태 전환 실패: {company.name}")
                return Response(
                    {"error": "상태 전환 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f"업체 상태 전환 중 예외 발생: {str(e)} - 업체: {company.name}")
            return Response(
                {"error": "상태 전환 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """
        특정 업체의 사용자 목록 조회
        """
        company = self.get_object()
        logger.info(f"업체 사용자 목록 조회: {company.name}")
        
        try:
            users = company.users.all().order_by('-created_at')
            serializer = CompanyUserSerializer(users, many=True)
            
            return Response({
                'company_id': str(company.id),
                'company_name': company.name,
                'users': serializer.data
            })
        
        except Exception as e:
            logger.error(f"업체 사용자 목록 조회 실패: {str(e)} - 업체: {company.name}")
            return Response(
                {"error": "사용자 목록 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompanyUserViewSet(viewsets.ModelViewSet):
    """
    업체 사용자 관리를 위한 ViewSet
    업체별 사용자의 CRUD 작업을 제공
    """
    
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'role']
    search_fields = ['username', 'company__name']
    ordering_fields = ['username', 'created_at', 'last_login']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 업체 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related('company')
        
        logger.info(f"업체 사용자 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """업체 사용자 생성"""
        logger.info(f"업체 사용자 생성 요청 시작 - 관리자: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                user = serializer.save()
            
            logger.info(f"업체 사용자 생성 성공: {user.username} - {user.company.name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"업체 사용자 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "사용자 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """업체 사용자 삭제"""
        instance = self.get_object()
        logger.info(f"업체 사용자 삭제 요청: {instance.username} ({instance.company.name})")
        
        try:
            with transaction.atomic():
                username = instance.username
                company_name = instance.company.name
                instance.delete()
            
            logger.info(f"업체 사용자 삭제 성공: {username} ({company_name})")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"업체 사용자 삭제 실패: {str(e)} - 사용자: {instance.username}")
            return Response(
                {"error": "사용자 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompanyMessageViewSet(viewsets.ModelViewSet):
    """
    업체 메시지 관리를 위한 ViewSet
    업체에 발송되는 메시지의 CRUD 작업을 제공
    """
    
    queryset = CompanyMessage.objects.all()
    serializer_class = CompanyMessageSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_bulk', 'company', 'sent_by']
    search_fields = ['message', 'company__name']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 관련 정보를 미리 로드
        queryset = queryset.select_related('company', 'sent_by')
        
        logger.info(f"업체 메시지 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """메시지 생성 및 발송"""
        logger.info(f"업체 메시지 발송 요청 - 발송자: {request.user}")
        
        try:
            # 발송자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['sent_by'] = request.user.id
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                message = serializer.save()
            
            message_type = "일괄" if message.is_bulk else "개별"
            target = "전체 업체" if message.is_bulk else message.company.name
            
            logger.info(f"업체 메시지 발송 성공: {message_type} - {target}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"업체 메시지 발송 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "메시지 발송 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def send_bulk_message(self, request):
        """
        전체 업체에 일괄 메시지 발송
        """
        logger.info(f"일괄 메시지 발송 요청 - 발송자: {request.user}")
        
        try:
            # 일괄 발송 플래그 설정
            mutable_data = request.data.copy()
            mutable_data['is_bulk'] = True
            mutable_data['sent_by'] = request.user.id
            mutable_data.pop('company', None)  # 일괄 발송시 업체 정보 제거
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                message = serializer.save()
            
            # 활성화된 업체 수 조회
            active_companies_count = Company.objects.filter(status=True).count()
            
            logger.info(f"일괄 메시지 발송 완료: {message.message[:50]}... ({active_companies_count}개 업체)")
            
            return Response({
                'message': f'전체 {active_companies_count}개 업체에 메시지가 발송되었습니다.',
                'message_id': str(message.id),
                'target_count': active_companies_count
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"일괄 메시지 발송 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "일괄 메시지 발송 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
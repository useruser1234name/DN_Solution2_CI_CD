"""
일반 주문 관리 시스템 ViewSet
Order 모델에 대한 CRUD 및 상태 관리 API 제공
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Order, OrderMemo, Invoice
from .serializers import OrderSerializer, OrderMemoSerializer, InvoiceSerializer
from companies.models import Company

logger = logging.getLogger('orders')


class OrderViewSet(viewsets.ModelViewSet):
    """
    주문 관리 ViewSet
    
    주문 생성, 조회, 수정, 삭제 및 상태 관리를 제공합니다.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자 권한에 따른 주문 목록 반환"""
        user = self.request.user
        
        try:
            # CompanyUser를 통해 회사 정보 가져오기
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
        except CompanyUser.DoesNotExist:
            logger.warning(f"사용자 {user.username}의 회사 정보를 찾을 수 없습니다.")
            return Order.objects.none()
        
        if company.type == 'headquarters':
            # 본사: 모든 주문 조회 가능
            return Order.objects.all().select_related('policy', 'company', 'created_by')
        elif company.type == 'agency':
            # 협력사: 자신과 하위 판매점 주문 조회 가능
            return Order.objects.filter(
                company__in=[company] + list(company.child_companies.all())
            ).select_related('policy', 'company', 'created_by')
        else:  # retail
            # 판매점: 자신의 주문만 조회 가능
            return Order.objects.filter(company=company).select_related('policy', 'company', 'created_by')
    
    def perform_create(self, serializer):
        """주문 생성 시 추가 처리"""
        user = self.request.user
        
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
        except CompanyUser.DoesNotExist:
            logger.warning(f"사용자 {user.username}의 회사 정보를 찾을 수 없습니다.")
            company = None
        
        order = serializer.save(
            created_by=user,
            company=company
        )
        
        # 리베이트 자동 계산
        order.calculate_rebate()
        
        logger.info(f"새 주문 생성: {order.customer_name} by {user.username}")
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """주문 승인 (본사만 가능)"""
        if not self._check_headquarters_permission(request):
            return Response({
                'error': '본사 권한이 필요합니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order = self.get_object()
        
        try:
            order.approve(user=request.user)
            return Response({
                'message': '주문이 승인되었습니다.',
                'status': order.status
            })
        except Exception as e:
            logger.error(f"주문 승인 실패: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def final_approve(self, request, pk=None):
        """최종 승인 - 정산 생성 트리거 (본사만 가능)"""
        if not self._check_headquarters_permission(request):
            return Response({
                'error': '본사 권한이 필요합니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order = self.get_object()
        
        try:
            with transaction.atomic():
                order.final_approve(user=request.user)
                
            return Response({
                'message': '주문이 최종 승인되었습니다. 정산이 생성되었습니다.',
                'status': order.status
            })
        except Exception as e:
            logger.error(f"최종 승인 실패: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """주문 상태 변경 - 강화된 버전"""
        order = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if not new_status:
            return Response({
                'error': '상태 값이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 상태 전환 가능 여부 확인 (권한 포함)
        if not order.can_transition_to(new_status, request.user):
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=request.user)
                user_info = f"{request.user.username} ({company_user.company.name})"
            except CompanyUser.DoesNotExist:
                user_info = request.user.username
            
            return Response({
                'error': f'사용자 {user_info}는 현재 상태({order.get_status_display()})에서 {dict(Order.STATUS_CHOICES)[new_status]}로 변경할 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            order.update_status(new_status, user=request.user, reason=reason)
            
            # 성공 메시지 생성
            status_display = order.get_status_display()
            success_message = f'주문 상태가 {status_display}로 변경되었습니다.'
            
            # 상태별 추가 메시지
            if new_status == 'final_approved':
                success_message += ' 정산이 생성되었습니다.'
            elif new_status == 'cancelled':
                success_message += ' 관련 정산이 취소되었습니다.'
            
            return Response({
                'message': success_message,
                'status': order.status,
                'status_display': status_display
            })
        except ValidationError as e:
            logger.error(f"상태 변경 실패: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"상태 변경 중 오류: {str(e)}")
            return Response({
                'error': '상태 변경 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def add_memo(self, request, pk=None):
        """주문 메모 추가"""
        order = self.get_object()
        memo_content = request.data.get('memo')
        
        if not memo_content:
            return Response({
                'error': '메모 내용이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            memo = OrderMemo.objects.create(
                order=order,
                memo=memo_content,
                created_by=request.user
            )
            
            serializer = OrderMemoSerializer(memo)
            return Response({
                'message': '메모가 추가되었습니다.',
                'memo': serializer.data
            })
        except Exception as e:
            logger.error(f"메모 추가 실패: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def memos(self, request, pk=None):
        """주문 메모 목록 조회"""
        order = self.get_object()
        memos = order.memos.all()
        serializer = OrderMemoSerializer(memos, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_invoice(self, request, pk=None):
        """송장 정보 등록"""
        order = self.get_object()
        
        # 이미 송장이 등록된 경우 확인
        if hasattr(order, 'invoice'):
            return Response({
                'error': '이미 송장이 등록된 주문입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = InvoiceSerializer(data=request.data)
        if serializer.is_valid():
            try:
                invoice = serializer.save(order=order)
                return Response({
                    'message': '송장이 등록되었습니다.',
                    'invoice': InvoiceSerializer(invoice).data
                })
            except Exception as e:
                logger.error(f"송장 등록 실패: {str(e)}")
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': '입력 데이터가 올바르지 않습니다.',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def invoice(self, request, pk=None):
        """송장 정보 조회"""
        order = self.get_object()
        
        if hasattr(order, 'invoice'):
            serializer = InvoiceSerializer(order.invoice)
            return Response(serializer.data)
        else:
            return Response({
                'message': '등록된 송장이 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def status_counts(self, request):
        """상태별 주문 수 조회"""
        queryset = self.get_queryset()
        status_counts = {}
        for status_value, status_display in Order.STATUS_CHOICES:
            status_counts[status_value] = queryset.filter(status=status_value).count()
        return Response({
            'success': True,
            'data': status_counts
        })
    
    def _check_headquarters_permission(self, request):
        """본사 권한 확인"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            return company_user.company.type == 'headquarters'
        except CompanyUser.DoesNotExist:
            return False


class OrderMemoViewSet(viewsets.ModelViewSet):
    """주문 메모 ViewSet"""
    serializer_class = OrderMemoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자가 접근 가능한 주문의 메모만 반환"""
        user = self.request.user
        
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
        except CompanyUser.DoesNotExist:
            return OrderMemo.objects.none()
        
        if company.type == 'headquarters':
            return OrderMemo.objects.all().select_related('order', 'created_by')
        elif company.type == 'agency':
            return OrderMemo.objects.filter(
                order__company__in=[company] + list(company.child_companies.all())
            ).select_related('order', 'created_by')
        else:  # retail
            return OrderMemo.objects.filter(order__company=company).select_related('order', 'created_by')


class InvoiceViewSet(viewsets.ModelViewSet):
    """송장 ViewSet"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자가 접근 가능한 주문의 송장만 반환"""
        user = self.request.user
        
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
        except CompanyUser.DoesNotExist:
            return Invoice.objects.none()
        
        if company.type == 'headquarters':
            return Invoice.objects.all().select_related('order')
        elif company.type == 'agency':
            return Invoice.objects.filter(
                order__company__in=[company] + list(company.child_companies.all())
            ).select_related('order')
        else:  # retail
            return Invoice.objects.filter(order__company=company).select_related('order')
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """배송 완료 처리"""
        invoice = self.get_object()
        delivered_at = request.data.get('delivered_at')
        
        try:
            success = invoice.mark_as_delivered(delivered_at=delivered_at)
            if success:
                return Response({
                    'message': '배송 완료 처리되었습니다.',
                    'delivered_at': invoice.delivered_at
                })
            else:
                return Response({
                    'error': '배송 완료 처리에 실패했습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"배송 완료 처리 실패: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

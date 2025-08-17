"""
주문 관리 시스템 뷰

이 모듈은 주문 관련 API 엔드포인트를 제공합니다.
주문 생성, 조회, 수정, 삭제 및 상태 관리 기능을 포함합니다.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Order, OrderMemo, Invoice, OrderRequest
from .serializers import (
    OrderSerializer, OrderMemoSerializer, InvoiceSerializer,
    OrderStatusUpdateSerializer, OrderBulkStatusUpdateSerializer,
    OrderBulkDeleteSerializer
)

logger = logging.getLogger('orders')


from .utils import get_visible_orders

class OrderViewSet(viewsets.ModelViewSet):
    """
    주문 관리 ViewSet
    
    주문의 CRUD 작업과 상태 관리 기능을 제공합니다.
    """
    queryset = Order.objects.select_related('policy', 'company', 'created_by').prefetch_related('memos')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자 권한에 따른 쿼리셋 필터링"""
        queryset = get_visible_orders(self.request.user)
        # N+1 쿼리 방지를 위한 select_related/prefetch_related 추가
        queryset = queryset.select_related(
            'policy',
            'policy__created_by',
            'company',
            'company__parent_company',
            'created_by'
        ).prefetch_related(
            'memos',
            'memos__created_by',
            'sensitive_data'
        )
        return queryset
    
    def perform_create(self, serializer):
        """주문 생성 시 생성자 정보 추가"""
        serializer.save(created_by=self.request.user)
        logger.info(f"새 주문 생성: {serializer.instance.customer_name}")
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """주문 상태 업데이트"""
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['new_status']
            memo = serializer.validated_data.get('memo', '')
            
            try:
                order.update_status(new_status, request.user)
                
                # 메모 추가
                if memo:
                    OrderMemo.objects.create(
                        order=order,
                        memo=f"상태 변경: {order.get_status_display()} - {memo}",
                        created_by=request.user
                    )
                
                return Response({
                    'success': True,
                    'message': f'주문 상태가 {order.get_status_display()}로 변경되었습니다.',
                    'status': order.status
                })
            except Exception as e:
                return Response({
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_update_status(self, request):
        """주문 일괄 상태 업데이트"""
        serializer = OrderBulkStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            order_ids = serializer.validated_data['order_ids']
            new_status = serializer.validated_data['new_status']
            
            orders = Order.objects.filter(id__in=order_ids)
            updated_count = 0
            
            for order in orders:
                try:
                    order.update_status(new_status, request.user)
                    updated_count += 1
                except Exception as e:
                    logger.warning(f"주문 상태 변경 실패: {order.id} - {str(e)}")
            
            return Response({
                'success': True,
                'message': f'{updated_count}개 주문의 상태가 변경되었습니다.',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """주문 일괄 삭제"""
        serializer = OrderBulkDeleteSerializer(data=request.data)
        
        if serializer.is_valid():
            order_ids = serializer.validated_data['order_ids']
            force_delete = serializer.validated_data['force_delete']
            
            orders = Order.objects.filter(id__in=order_ids)
            deleted_count = 0
            
            for order in orders:
                # 완료된 주문은 force_delete가 True일 때만 삭제
                if order.status == 'completed' and not force_delete:
                    continue
                
                try:
                    order.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"주문 삭제 실패: {order.id} - {str(e)}")
            
            return Response({
                'success': True,
                'message': f'{deleted_count}개 주문이 삭제되었습니다.',
                'deleted_count': deleted_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """주문 승인 (본사만 가능)"""
        order = self.get_object()
        
        try:
            # 권한 확인 - 본사만 승인 가능
            if not request.user.is_superuser:
                try:
                    from companies.models import CompanyUser
                    company_user = CompanyUser.objects.get(django_user=request.user)
                    if company_user.company.type != 'headquarters':
                        return Response({
                            'success': False,
                            'message': '본사 관리자만 주문을 승인할 수 있습니다.'
                        }, status=status.HTTP_403_FORBIDDEN)
                except CompanyUser.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': '업체 정보를 찾을 수 없습니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # 주문 승인
            order.approve(request.user)
            
            # 승인 메모 추가
            memo_text = request.data.get('memo', '주문이 승인되었습니다.')
            OrderMemo.objects.create(
                order=order,
                memo=f"[승인] {memo_text}",
                created_by=request.user
            )
            
            return Response({
                'success': True,
                'message': '주문이 승인되었습니다.',
                'status': order.status
            })
            
        except Exception as e:
            logger.error(f"주문 승인 실패: {str(e)} - 주문: {order.customer_name}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """주문 반려 (본사만 가능)"""
        order = self.get_object()
        
        try:
            # 권한 확인 - 본사만 반려 가능
            if not request.user.is_superuser:
                try:
                    from companies.models import CompanyUser
                    company_user = CompanyUser.objects.get(django_user=request.user)
                    if company_user.company.type != 'headquarters':
                        return Response({
                            'success': False,
                            'message': '본사 관리자만 주문을 반려할 수 있습니다.'
                        }, status=status.HTTP_403_FORBIDDEN)
                except CompanyUser.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': '업체 정보를 찾을 수 없습니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # 대기 중인 주문만 반려 가능
            if order.status != 'pending':
                return Response({
                    'success': False,
                    'message': '대기 중인 주문만 반려할 수 있습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 주문 반려 (취소 상태로 변경)
            order.update_status('cancelled', request.user)
            
            # 반려 메모 추가
            memo_text = request.data.get('memo', '주문이 반려되었습니다.')
            OrderMemo.objects.create(
                order=order,
                memo=f"[반려] {memo_text}",
                created_by=request.user
            )
            
            return Response({
                'success': True,
                'message': '주문이 반려되었습니다.',
                'status': order.status
            })
            
        except Exception as e:
            logger.error(f"주문 반려 실패: {str(e)} - 주문: {order.customer_name}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """주문 통계 조회"""
        from django.db.models import Count, Q
        
        queryset = self.get_queryset()
        
        # 상태별 통계
        stats = queryset.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            approved=Count('id', filter=Q(status='approved')),
            processing=Count('id', filter=Q(status='processing')),
            shipped=Count('id', filter=Q(status='shipped')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
        )
        
        # 반려는 취소된 것으로 간주
        stats['rejected'] = stats['cancelled']
        
        return Response({
            'success': True,
            'data': stats
        })


class OrderMemoViewSet(viewsets.ModelViewSet):
    """
    주문 메모 관리 ViewSet
    """
    queryset = OrderMemo.objects.select_related('order', 'created_by')
    serializer_class = OrderMemoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """사용자가 볼 수 있는 주문의 메모만 필터링"""
        visible_orders = get_visible_orders(self.request.user)
        return self.queryset.filter(order__in=visible_orders)
    
    def perform_create(self, serializer):
        """메모 생성 시 작성자 정보 추가"""
        serializer.save(created_by=self.request.user)
        logger.info(f"주문 메모 생성: {serializer.instance.order.customer_name}")


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    송장 관리 ViewSet
    """
    queryset = Invoice.objects.select_related('order')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """사용자가 볼 수 있는 주문의 송장만 필터링"""
        visible_orders = get_visible_orders(self.request.user)
        return self.queryset.filter(order__in=visible_orders)
    
    def perform_create(self, serializer):
        """송장 생성 시 자동으로 주문 상태 업데이트"""
        invoice = serializer.save()
        logger.info(f"송장 생성: {invoice.order.customer_name} - {invoice.courier}")
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """배송 완료 처리"""
        invoice = self.get_object()
        
        try:
            success = invoice.mark_as_delivered()
            if success:
                return Response({
                    'success': True,
                    'message': '배송 완료 처리되었습니다.'
                })
            else:
                return Response({
                    'success': False,
                    'message': '배송 완료 처리에 실패했습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class OrderRequestViewSet(viewsets.ModelViewSet):
    """
    주문 요청 관리 ViewSet
    """
    queryset = OrderRequest.objects.select_related('order', 'processed_by')
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """사용자가 볼 수 있는 주문의 요청만 필터링"""
        visible_orders = get_visible_orders(self.request.user)
        return self.queryset.filter(order__in=visible_orders)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """요청 승인"""
        order_request = self.get_object()
        
        try:
            order_request.approve(request.user)
            return Response({
                'success': True,
                'message': '요청이 승인되었습니다.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """요청 거절"""
        order_request = self.get_object()
        
        try:
            order_request.reject(request.user)
            return Response({
                'success': True,
                'message': '요청이 거절되었습니다.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """요청 완료"""
        order_request = self.get_object()
        
        try:
            order_request.complete(request.user)
            return Response({
                'success': True,
                'message': '요청이 완료되었습니다.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

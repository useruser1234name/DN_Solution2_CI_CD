# orders/views.py
import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from companies.models import Company
from policies.models import Policy
from .models import Order, OrderMemo, Invoice
from .serializers import (
    OrderSerializer, OrderMemoSerializer, InvoiceSerializer,
    OrderStatusUpdateSerializer, OrderBulkStatusUpdateSerializer,
    OrderBulkDeleteSerializer
)

logger = logging.getLogger('orders')


class OrderViewSet(viewsets.ModelViewSet):
    """
    주문서 관리를 위한 ViewSet
    주문서의 CRUD 작업과 상태 관리, 검색 기능 제공
    """
    
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'status', 'apply_type', 'carrier', 'company', 'policy', 'created_by'
    ]
    search_fields = [
        'customer_name', 'customer_phone', 'model_name', 'memo'
    ]
    ordering_fields = [
        'customer_name', 'created_at', 'updated_at', 'status'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self):
        """쿼리셋 최적화 및 필터링"""
        queryset = super().get_queryset()
        
        # 관련 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related(
            'policy', 'company', 'created_by'
        ).prefetch_related(
            'order_memos', 'invoice'
        )
        
        # 추가 필터링 옵션
        # 기간별 필터링
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                logger.warning(f"잘못된 시작일 형식: {start_date}")
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                logger.warning(f"잘못된 종료일 형식: {end_date}")
        
        # 송장 존재 여부 필터링
        has_invoice = self.request.query_params.get('has_invoice')
        if has_invoice is not None:
            if has_invoice.lower() == 'true':
                queryset = queryset.filter(invoice__isnull=False)
            elif has_invoice.lower() == 'false':
                queryset = queryset.filter(invoice__isnull=True)
        
        logger.info(f"주문서 목록 조회 요청 - 사용자: {self.request.user}, 필터 적용된 수: {queryset.count()}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """주문서 생성"""
        logger.info(f"주문서 생성 요청 시작 - 사용자: {request.user}")
        
        try:
            # 접수자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['created_by'] = request.user.id
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                order = serializer.save()
            
            logger.info(f"주문서 생성 성공: {order.customer_name} - {order.model_name} (ID: {order.id})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"주문서 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "주문서 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """주문서 정보 수정"""
        instance = self.get_object()
        logger.info(f"주문서 정보 수정 요청: {instance.customer_name} (ID: {instance.id})")
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                order = serializer.save()
            
            logger.info(f"주문서 정보 수정 성공: {order.customer_name}")
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"주문서 정보 수정 실패: {str(e)} - 주문: {instance.customer_name}")
            return Response(
                {"error": "주문서 정보 수정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """주문서 삭제"""
        instance = self.get_object()
        logger.info(f"주문서 삭제 요청: {instance.customer_name} (ID: {instance.id})")
        
        try:
            # 완료된 주문 삭제 방지
            if instance.status == 'completed' and not request.data.get('force_delete', False):
                logger.warning(f"완료된 주문 삭제 시도: {instance.customer_name}")
                return Response(
                    {"error": "완료된 주문은 삭제할 수 없습니다. 강제 삭제를 원하면 force_delete=true를 설정하세요."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 연관된 메모와 송장 수 확인
            memo_count = instance.order_memos.count()
            has_invoice = hasattr(instance, 'invoice') and instance.invoice is not None
            
            with transaction.atomic():
                customer_name = instance.customer_name
                instance.delete()
            
            logger.info(f"주문서 삭제 성공: {customer_name} (메모: {memo_count}개, 송장: {'있음' if has_invoice else '없음'})")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"주문서 삭제 실패: {str(e)} - 주문: {instance.customer_name}")
            return Response(
                {"error": "주문서 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        주문 상태 업데이트 기능
        주문의 처리 상태를 안전하게 변경
        """
        order = self.get_object()
        logger.info(f"주문 상태 업데이트 요청: {order.customer_name} (현재 상태: {order.status})")
        
        try:
            # 요청 데이터에 주문 ID 추가
            mutable_data = request.data.copy()
            mutable_data['order_id'] = str(order.id)
            
            serializer = OrderStatusUpdateSerializer(data=mutable_data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            new_status = serializer.validated_data['new_status']
            memo_text = serializer.validated_data.get('memo', '')
            
            with transaction.atomic():
                # 상태 업데이트
                success = order.update_status(new_status, request.user)
                
                if not success:
                    return Response(
                        {"error": f"상태를 {order.get_status_display()}에서 {dict(Order.STATUS_CHOICES)[new_status]}(으)로 변경할 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 상태 변경 메모 자동 추가
                if memo_text:
                    OrderMemo.objects.create(
                        order=order,
                        memo=f"[상태 변경] {dict(Order.STATUS_CHOICES)[new_status]}: {memo_text}",
                        created_by=request.user
                    )
                else:
                    OrderMemo.objects.create(
                        order=order,
                        memo=f"[상태 변경] {dict(Order.STATUS_CHOICES)[new_status]}",
                        created_by=request.user
                    )
            
            logger.info(f"주문 상태 업데이트 성공: {order.customer_name} -> {order.get_status_display()}")
            
            return Response({
                'message': f'{order.customer_name}의 상태가 {order.get_status_display()}(으)로 변경되었습니다.',
                'order_id': str(order.id),
                'new_status': order.status,
                'new_status_display': order.get_status_display()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"주문 상태 업데이트 중 오류 발생: {str(e)} - 주문: {order.customer_name}")
            return Response(
                {"error": "상태 업데이트 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_status_update(self, request):
        """
        주문 일괄 상태 업데이트 기능
        여러 주문의 상태를 동시에 변경
        """
        logger.info(f"주문 일괄 상태 업데이트 요청 - 사용자: {request.user}")
        
        serializer = OrderBulkStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"주문 일괄 상태 업데이트 요청 데이터 검증 실패: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_ids = serializer.validated_data['order_ids']
        new_status = serializer.validated_data['new_status']
        
        try:
            with transaction.atomic():
                orders = Order.objects.filter(id__in=order_ids)
                updated_orders = []
                failed_orders = []
                
                for order in orders:
                    try:
                        success = order.update_status(new_status, request.user)
                        
                        if success:
                            # 상태 변경 메모 자동 추가
                            OrderMemo.objects.create(
                                order=order,
                                memo=f"[일괄 상태 변경] {order.get_status_display()}",
                                created_by=request.user
                            )
                            
                            updated_orders.append({
                                'order_id': str(order.id),
                                'customer_name': order.customer_name,
                                'new_status': order.status
                            })
                        else:
                            failed_orders.append({
                                'order_id': str(order.id),
                                'customer_name': order.customer_name,
                                'reason': '유효하지 않은 상태 전환'
                            })
                    
                    except Exception as e:
                        logger.error(f"개별 주문 상태 업데이트 실패: {order.customer_name} - {str(e)}")
                        failed_orders.append({
                            'order_id': str(order.id),
                            'customer_name': order.customer_name,
                            'reason': str(e)
                        })
                
                logger.info(f"주문 일괄 상태 업데이트 완료 - 성공: {len(updated_orders)}, 실패: {len(failed_orders)}")
                
                return Response({
                    'message': f'{len(updated_orders)}개 주문의 상태가 {dict(Order.STATUS_CHOICES)[new_status]}(으)로 변경되었습니다.',
                    'updated': updated_orders,
                    'failed': failed_orders
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"주문 일괄 상태 업데이트 중 전체 오류 발생: {str(e)}")
            return Response(
                {"error": "일괄 상태 업데이트 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """
        주문 일괄 삭제 기능
        여러 주문을 선택하여 동시에 삭제
        """
        logger.info(f"주문 일괄 삭제 요청 - 사용자: {request.user}")
        
        serializer = OrderBulkDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"주문 일괄 삭제 요청 데이터 검증 실패: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        order_ids = serializer.validated_data['order_ids']
        force_delete = serializer.validated_data['force_delete']
        
        try:
            with transaction.atomic():
                orders = Order.objects.filter(id__in=order_ids)
                deleted_orders = []
                failed_orders = []
                
                for order in orders:
                    try:
                        # 완료된 주문 삭제 방지 (강제 삭제 옵션 있을 때 제외)
                        if order.status == 'completed' and not force_delete:
                            failed_orders.append({
                                'order_id': str(order.id),
                                'customer_name': order.customer_name,
                                'reason': '완료된 주문'
                            })
                            continue
                        
                        deleted_orders.append({
                            'order_id': str(order.id),
                            'customer_name': order.customer_name
                        })
                        order.delete()
                    
                    except Exception as e:
                        logger.error(f"개별 주문 삭제 실패: {order.customer_name} - {str(e)}")
                        failed_orders.append({
                            'order_id': str(order.id),
                            'customer_name': order.customer_name,
                            'reason': str(e)
                        })
                
                logger.info(f"주문 일괄 삭제 완료 - 성공: {len(deleted_orders)}, 실패: {len(failed_orders)}")
                
                return Response({
                    'message': f'{len(deleted_orders)}개 주문이 삭제되었습니다.',
                    'deleted': deleted_orders,
                    'failed': failed_orders
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"주문 일괄 삭제 중 전체 오류 발생: {str(e)}")
            return Response(
                {"error": "일괄 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def memos(self, request, pk=None):
        """
        특정 주문의 메모 목록 조회
        """
        order = self.get_object()
        logger.info(f"주문 메모 목록 조회: {order.customer_name}")
        
        try:
            memos = order.order_memos.all().order_by('-created_at')
            serializer = OrderMemoSerializer(memos, many=True)
            
            return Response({
                'order_id': str(order.id),
                'customer_name': order.customer_name,
                'memos': serializer.data,
                'total_count': len(serializer.data)
            })
        
        except Exception as e:
            logger.error(f"주문 메모 목록 조회 실패: {str(e)} - 주문: {order.customer_name}")
            return Response(
                {"error": "메모 목록 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        주문 통계 조회 기능
        주문 상태별, 기간별 통계 제공
        """
        logger.info(f"주문 통계 조회 요청 - 사용자: {request.user}")
        
        try:
            # 기본 통계
            total_orders = Order.objects.count()
            
            # 상태별 통계
            status_stats = {}
            for status_code, status_name in Order.STATUS_CHOICES:
                count = Order.objects.filter(status=status_code).count()
                status_stats[status_code] = {
                    'name': status_name,
                    'count': count
                }
            
            # 최근 7일간 일별 주문 수
            daily_stats = []
            for i in range(7):
                date = timezone.now().date() - timedelta(days=i)
                count = Order.objects.filter(created_at__date=date).count()
                daily_stats.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': count
                })
            
            # 업체별 주문 수 (상위 10개)
            company_stats = Order.objects.values(
                'company__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # 통신사별 통계
            carrier_stats = {}
            for carrier_code, carrier_name in Order.CARRIER_CHOICES:
                count = Order.objects.filter(carrier=carrier_code).count()
                carrier_stats[carrier_code] = {
                    'name': carrier_name,
                    'count': count
                }
            
            logger.info("주문 통계 조회 완료")
            
            return Response({
                'total_orders': total_orders,
                'status_statistics': status_stats,
                'daily_statistics': daily_stats,
                'company_statistics': list(company_stats),
                'carrier_statistics': carrier_stats,
                'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        except Exception as e:
            logger.error(f"주문 통계 조회 실패: {str(e)}")
            return Response(
                {"error": "통계 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderMemoViewSet(viewsets.ModelViewSet):
    """
    주문 메모 관리를 위한 ViewSet
    주문 처리 과정의 메모와 기록 관리 기능 제공
    """
    
    queryset = OrderMemo.objects.all()
    serializer_class = OrderMemoSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['order', 'created_by']
    search_fields = ['memo', 'order__customer_name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """쿼리셋 최적화"""
        queryset = super().get_queryset()
        # 관련 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related('order', 'created_by')
        
        logger.info(f"주문 메모 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """주문 메모 생성"""
        logger.info(f"주문 메모 생성 요청 - 사용자: {request.user}")
        
        try:
            # 작성자 정보 자동 설정
            mutable_data = request.data.copy()
            mutable_data['created_by'] = request.user.id
            
            serializer = self.get_serializer(data=mutable_data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                memo = serializer.save()
            
            logger.info(f"주문 메모 생성 성공: {memo.order.customer_name}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"주문 메모 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "메모 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """주문 메모 삭제"""
        instance = self.get_object()
        logger.info(f"주문 메모 삭제 요청: {instance.order.customer_name} (메모 ID: {instance.id})")
        
        try:
            with transaction.atomic():
                customer_name = instance.order.customer_name
                memo_preview = instance.memo[:50]
                instance.delete()
            
            logger.info(f"주문 메모 삭제 성공: {customer_name} - {memo_preview}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"주문 메모 삭제 실패: {str(e)} - 메모 ID: {instance.id}")
            return Response(
                {"error": "메모 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    송장 정보 관리를 위한 ViewSet
    배송 처리 및 송장 추적 기능 제공
    """
    
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    # 필터링, 검색, 정렬 설정
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['courier', 'order__company', 'order__status']
    search_fields = ['invoice_number', 'order__customer_name', 'recipient_name']
    ordering_fields = ['sent_at', 'delivered_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        """쿼리셋 최적화 및 필터링"""
        queryset = super().get_queryset()
        # 관련 정보를 미리 로드하여 N+1 쿼리 문제 방지
        queryset = queryset.select_related('order', 'order__company')
        
        # 배송 완료 여부 필터링
        is_delivered = self.request.query_params.get('is_delivered')
        if is_delivered is not None:
            if is_delivered.lower() == 'true':
                queryset = queryset.filter(delivered_at__isnull=False)
            elif is_delivered.lower() == 'false':
                queryset = queryset.filter(delivered_at__isnull=True)
        
        logger.info(f"송장 목록 조회 요청 - 사용자: {self.request.user}")
        return queryset
    
    def create(self, request, *args, **kwargs):
        """송장 생성"""
        logger.info(f"송장 생성 요청 - 사용자: {request.user}")
        
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                invoice = serializer.save()
            
            logger.info(f"송장 생성 성공: {invoice.order.customer_name} - {invoice.courier} ({invoice.invoice_number})")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"송장 생성 실패: {str(e)} - 요청 데이터: {request.data}")
            return Response(
                {"error": "송장 생성 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """송장 정보 수정"""
        instance = self.get_object()
        logger.info(f"송장 정보 수정 요청: {instance.order.customer_name} - {instance.invoice_number}")
        
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            
            with transaction.atomic():
                invoice = serializer.save()
            
            logger.info(f"송장 정보 수정 성공: {invoice.order.customer_name}")
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"송장 정보 수정 실패: {str(e)} - 송장: {instance.invoice_number}")
            return Response(
                {"error": "송장 정보 수정 중 오류가 발생했습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """송장 삭제"""
        instance = self.get_object()
        logger.info(f"송장 삭제 요청: {instance.order.customer_name} - {instance.invoice_number}")
        
        try:
            with transaction.atomic():
                customer_name = instance.order.customer_name
                invoice_number = instance.invoice_number
                
                # 주문 상태를 처리중으로 되돌리기
                if instance.order.status == 'completed':
                    instance.order.update_status('processing')
                
                instance.delete()
            
            logger.info(f"송장 삭제 성공: {customer_name} - {invoice_number}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"송장 삭제 실패: {str(e)} - 송장: {instance.invoice_number}")
            return Response(
                {"error": "송장 삭제 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        """
        배송 완료 처리 기능
        송장의 배송 완료 상태로 변경
        """
        invoice = self.get_object()
        logger.info(f"배송 완료 처리 요청: {invoice.order.customer_name} - {invoice.invoice_number}")
        
        try:
            # 이미 배송 완료된 경우
            if invoice.is_delivered():
                return Response(
                    {"message": f"이미 배송 완료된 주문입니다. (완료일: {invoice.delivered_at.strftime('%Y-%m-%d %H:%M:%S')})"},
                    status=status.HTTP_200_OK
                )
            
            # 배송 완료 일시 설정
            delivered_at = request.data.get('delivered_at')
            if delivered_at:
                try:
                    delivered_at = datetime.strptime(delivered_at, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    delivered_at = None
            
            with transaction.atomic():
                success = invoice.mark_as_delivered(delivered_at)
                
                if success:
                    # 배송 완료 메모 자동 추가
                    OrderMemo.objects.create(
                        order=invoice.order,
                        memo=f"[배송 완료] {invoice.get_courier_display()} - {invoice.invoice_number}",
                        created_by=request.user
                    )
            
            if success:
                logger.info(f"배송 완료 처리 성공: {invoice.order.customer_name}")
                return Response({
                    'message': f'{invoice.order.customer_name}의 배송이 완료되었습니다.',
                    'order_id': str(invoice.order.id),
                    'invoice_number': invoice.invoice_number,
                    'delivered_at': invoice.delivered_at.strftime('%Y-%m-%d %H:%M:%S')
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "배송 완료 처리 중 오류가 발생했습니다."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            logger.error(f"배송 완료 처리 중 예외 발생: {str(e)} - 송장: {invoice.invoice_number}")
            return Response(
                {"error": "배송 완료 처리 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def delivery_statistics(self, request):
        """
        배송 통계 조회 기능
        택배사별, 배송 상태별 통계 제공
        """
        logger.info(f"배송 통계 조회 요청 - 사용자: {request.user}")
        
        try:
            # 기본 통계
            total_invoices = Invoice.objects.count()
            delivered_count = Invoice.objects.filter(delivered_at__isnull=False).count()
            in_transit_count = total_invoices - delivered_count
            
            # 택배사별 통계
            courier_stats = {}
            for courier_code, courier_name in Invoice.COURIER_CHOICES:
                total = Invoice.objects.filter(courier=courier_code).count()
                delivered = Invoice.objects.filter(courier=courier_code, delivered_at__isnull=False).count()
                courier_stats[courier_code] = {
                    'name': courier_name,
                    'total': total,
                    'delivered': delivered,
                    'in_transit': total - delivered
                }
            
            # 최근 7일간 일별 배송 완료 수
            delivery_daily_stats = []
            for i in range(7):
                date = timezone.now().date() - timedelta(days=i)
                count = Invoice.objects.filter(delivered_at__date=date).count()
                delivery_daily_stats.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'delivered_count': count
                })
            
            logger.info("배송 통계 조회 완료")
            
            return Response({
                'total_invoices': total_invoices,
                'delivered_count': delivered_count,
                'in_transit_count': in_transit_count,
                'delivery_rate': round((delivered_count / total_invoices * 100), 2) if total_invoices > 0 else 0,
                'courier_statistics': courier_stats,
                'daily_delivery_statistics': delivery_daily_stats,
                'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        except Exception as e:
            logger.error(f"배송 통계 조회 실패: {str(e)}")
            return Response(
                {"error": "배송 통계 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
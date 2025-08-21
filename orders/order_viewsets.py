"""
일반 주문 관리 ViewSet 추가
기존 TelecomOrder와 별도로 Order 모델을 관리
"""

import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ValidationError

from .models import Order, OrderMemo, Invoice, OrderRequest
from .serializers import OrderSerializer, OrderMemoSerializer
from companies.models import Company, CompanyUser
from policies.models import Policy

logger = logging.getLogger('orders')


class OrderViewSet(viewsets.ModelViewSet):
    """일반 주문 관리 ViewSet"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """권한에 따른 주문 필터링"""
        user = self.request.user
        
        # 슈퍼유저는 모든 주문 조회
        if user.is_superuser:
            return Order.objects.all()
        
        # CompanyUser 확인
        if not hasattr(user, 'companyuser'):
            return Order.objects.none()
        
        company_user = user.companyuser
        company = company_user.company
        
        # 회사 타입에 따른 필터링
        if company.type == 'headquarters':
            # 본사는 모든 주문 조회 가능
            return Order.objects.all()
        elif company.type == 'agency':
            # 협력사는 자신과 하위 판매점의 주문만 조회
            return Order.objects.filter(
                Q(company=company) |
                Q(company__parent_company=company)
            )
        else:  # retail
            # 판매점은 자신의 주문만 조회
            return Order.objects.filter(company=company)
    
    def perform_create(self, serializer):
        """주문 생성 시 추가 처리"""
        # 생성자 정보 자동 설정
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """주문 승인 (본사만 가능)"""
        order = self.get_object()
        
        try:
            # 본사 권한 확인
            if not self._is_headquarters_user(request.user):
                return Response({
                    'success': False,
                    'message': '본사 관리자만 주문을 승인할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 주문 승인
            order.approve(request.user)
            
            return Response({
                'success': True,
                'message': '주문이 승인되었습니다.',
                'data': {
                    'order_id': str(order.id),
                    'status': order.status,
                    'customer_name': order._mask_customer_name()
                }
            })
            
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"주문 승인 실패: {str(e)} - 주문 ID: {pk}")
            return Response({
                'success': False,
                'message': '주문 승인 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def final_approve(self, request, pk=None):
        """최종 승인 - 정산 생성 (본사만 가능)"""
        order = self.get_object()
        
        try:
            # 본사 권한 확인
            if not self._is_headquarters_user(request.user):
                return Response({
                    'success': False,
                    'message': '본사 관리자만 최종 승인할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 최종 승인 처리
            order.final_approve(request.user)
            
            return Response({
                'success': True,
                'message': '주문이 최종 승인되어 정산이 생성되었습니다.',
                'data': {
                    'order_id': str(order.id),
                    'status': order.status,
                    'customer_name': order._mask_customer_name()
                }
            })
            
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"주문 최종 승인 실패: {str(e)} - 주문 ID: {pk}")
            return Response({
                'success': False,
                'message': '주문 최종 승인 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """주문 상태 업데이트"""
        order = self.get_object()
        new_status = request.data.get('status')
        
        try:
            # 상태 전환 가능 여부 확인
            if not order.can_transition_to(new_status):
                return Response({
                    'success': False,
                    'message': f'현재 상태({order.get_status_display()})에서 {new_status}로 변경할 수 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 상태 업데이트
            order.update_status(new_status, request.user)
            
            return Response({
                'success': True,
                'message': f'주문 상태가 {order.get_status_display()}(으)로 변경되었습니다.',
                'data': {
                    'order_id': str(order.id),
                    'status': order.status,
                    'status_display': order.get_status_display()
                }
            })
            
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"주문 상태 업데이트 실패: {str(e)} - 주문 ID: {pk}")
            return Response({
                'success': False,
                'message': '상태 업데이트 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def memos(self, request, pk=None):
        """주문 메모 목록 조회"""
        order = self.get_object()
        memos = order.memos.all().order_by('-created_at')
        
        serializer = OrderMemoSerializer(memos, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_memo(self, request, pk=None):
        """주문 메모 추가"""
        order = self.get_object()
        memo_content = request.data.get('memo')
        
        if not memo_content or not memo_content.strip():
            return Response({
                'success': False,
                'message': '메모 내용을 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            memo = OrderMemo.objects.create(
                order=order,
                memo=memo_content.strip(),
                created_by=request.user
            )
            
            serializer = OrderMemoSerializer(memo)
            return Response({
                'success': True,
                'message': '메모가 추가되었습니다.',
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"주문 메모 추가 실패: {str(e)} - 주문 ID: {pk}")
            return Response({
                'success': False,
                'message': '메모 추가 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status_counts(self, request):
        """상태별 주문 수 조회"""
        queryset = self.get_queryset()
        
        status_counts = {}
        for status_code, status_name in Order.STATUS_CHOICES:
            count = queryset.filter(status=status_code).count()
            status_counts[status_code] = {
                'name': status_name,
                'count': count
            }
        
        return Response({
            'success': True,
            'data': status_counts
        })
    
    def _is_headquarters_user(self, user):
        """본사 사용자인지 확인"""
        if user.is_superuser:
            return True
        
        try:
            company_user = CompanyUser.objects.get(django_user=user)
            return company_user.company.type == 'headquarters'
        except CompanyUser.DoesNotExist:
            return False


# 기존 TelecomOrder 관련 뷰들은 그대로 유지

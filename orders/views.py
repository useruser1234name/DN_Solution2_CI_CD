"""
통신사 주문 관리 시스템 뷰
주문서 생성, 조회, 상태 관리 등을 처리
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .telecom_order_models import TelecomOrder, OrderStatusHistory
from policies.models import Policy, OrderFormTemplate

logger = logging.getLogger('orders')


class TelecomOrderCreateView(APIView):
    """통신사 주문 생성 API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            policy_id = data.get('policy_id')
            
            # 정책 조회
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 주문 생성
            order = TelecomOrder.objects.create(
                policy=policy,
                company=request.user.company,
                created_by=request.user,
                carrier=policy.carrier,
                subscription_type=policy.join_type,
                order_data=data,  # JSON 필드에 전체 주문 데이터 저장
                current_status='received'
            )
            
            # 초기 상태 이력 생성
            OrderStatusHistory.objects.create(
                order=order,
                status='received',
                description='주문 접수',
                updated_by=request.user,
                user_role=request.user.role if hasattr(request.user, 'role') else 'user',
                department='판매점',
                ip_address=self.get_client_ip(request)
            )
            
            logger.info(f"새 주문 생성: {order.order_number} by {request.user.username}")
            
            return Response({
                'success': True,
                'data': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'status': order.current_status
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"주문 생성 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '주문 생성 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 조회"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TelecomOrderStatusUpdateView(APIView):
    """통신사 주문 상태 업데이트 API (본사 전용)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, order_id):
        try:
            # 본사 권한 확인
            if not hasattr(request.user, 'company') or request.user.company.type != 'headquarters':
                return Response({
                    'success': False,
                    'message': '본사 권한이 필요합니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            data = request.data
            new_status = data.get('status')
            description = data.get('description', '')
            
            # 주문 조회
            order = get_object_or_404(TelecomOrder, id=order_id)
            
            # 상태 변경 검증
            if not self.can_transition_status(order.current_status, new_status):
                return Response({
                    'success': False,
                    'message': f'현재 상태({order.current_status})에서 {new_status}로 변경할 수 없습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 상태 업데이트
            old_status = order.current_status
            order.current_status = new_status
            
            # 개통 완료시 개통일자 설정
            if new_status == 'activation_complete':
                from django.utils import timezone
                order.activation_date = timezone.now()
            
            order.save()
            
            # 상태 이력 생성
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                description=description or f'{old_status} → {new_status}',
                updated_by=request.user,
                user_role=request.user.role if hasattr(request.user, 'role') else 'admin',
                department='본사',
                ip_address=self.get_client_ip(request)
            )
            
            logger.info(f"주문 상태 변경: {order.order_number} {old_status} → {new_status} by {request.user.username}")
            
            return Response({
                'success': True,
                'data': {
                    'order_id': str(order.id),
                    'old_status': old_status,
                    'new_status': new_status,
                    'updated_at': order.updated_at
                }
            })
            
        except Exception as e:
            logger.error(f"주문 상태 업데이트 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '상태 업데이트 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def can_transition_status(self, current_status, new_status):
        """상태 전이 가능 여부 확인"""
        transitions = {
            'received': ['activation_request', 'cancelled'],
            'activation_request': ['activating', 'pending', 'cancelled'],
            'activating': ['activation_complete', 'pending', 'cancelled'],
            'activation_complete': ['cancelled'],
            'pending': ['activation_request', 'cancelled'],
            'cancelled': [],  # 취소된 주문은 더 이상 변경 불가
            'rejected': []    # 반려된 주문은 더 이상 변경 불가
        }
        
        return new_status in transitions.get(current_status, [])
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 조회"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TelecomOrderDetailView(APIView):
    """통신사 주문 상세 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            order = get_object_or_404(TelecomOrder, id=order_id)
            
            # 권한 확인 (본사 또는 해당 주문의 업체)
            if (hasattr(request.user, 'company') and 
                request.user.company.type != 'headquarters' and 
                order.company != request.user.company):
                return Response({
                    'success': False,
                    'message': '접근 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 상태 이력 조회
            status_history = OrderStatusHistory.objects.filter(
                order=order
            ).order_by('-created_at')
            
            return Response({
                'success': True,
                'data': {
                    'order': {
                        'id': str(order.id),
                        'order_number': order.order_number,
                        'current_status': order.current_status,
                        'policy_title': order.policy.title,
                        'carrier': order.carrier,
                        'subscription_type': order.subscription_type,
                        'company_name': order.company.name,
                        'created_by': order.created_by.username,
                        'received_date': order.received_date,
                        'activation_date': order.activation_date,
                        'order_data': order.order_data
                    },
                    'status_history': [
                        {
                            'timestamp': history.created_at,
                            'status': history.status,
                            'description': history.description,
                            'updated_by': history.updated_by.username if history.updated_by else 'System',
                            'user_role': history.user_role,
                            'department': history.department
                        }
                        for history in status_history
                    ]
                }
            })
            
        except Exception as e:
            logger.error(f"주문 상세 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '주문 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TelecomOrderListView(APIView):
    """통신사 주문 목록 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # 기본 쿼리셋
            queryset = TelecomOrder.objects.all()
            
            # 권한에 따른 필터링
            if hasattr(request.user, 'company'):
                if request.user.company.type != 'headquarters':
                    # 본사가 아니면 자신의 업체 주문만 조회
                    queryset = queryset.filter(company=request.user.company)
            
            # 필터링 파라미터
            status_filter = request.GET.get('status')
            if status_filter:
                queryset = queryset.filter(current_status=status_filter)
            
            carrier_filter = request.GET.get('carrier')
            if carrier_filter:
                queryset = queryset.filter(carrier=carrier_filter)
            
            # 페이지네이션
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            orders = queryset.order_by('-received_date')[start_index:end_index]
            
            return Response({
                'success': True,
                'data': {
                    'orders': [
                        {
                            'id': str(order.id),
                            'order_number': order.order_number,
                            'current_status': order.current_status,
                            'policy_title': order.policy.title,
                            'carrier': order.carrier,
                            'company_name': order.company.name,
                            'created_by': order.created_by.username,
                            'received_date': order.received_date,
                            'activation_date': order.activation_date
                        }
                        for order in orders
                    ],
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_count': total_count,
                        'total_pages': (total_count + page_size - 1) // page_size
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"주문 목록 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '주문 목록을 불러오는 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
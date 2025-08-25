"""
주문 관리 시스템 뷰
통합된 Order 모델을 사용한 주문서 생성, 조회, 상태 관리 등을 처리
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from policies.models import Policy, OrderFormTemplate

logger = logging.getLogger('orders')


class OrderFormTemplateView(APIView):
    """주문서 양식 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """정책별 주문서 양식 조회"""
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 정책에 연결된 주문서 양식 조회
            form_template = policy.order_form_template
            
            if not form_template:
                return Response({
                    'error': '해당 정책에 주문서 양식이 설정되지 않았습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 양식 데이터 반환
            template_data = {
                'id': str(form_template.id),
                'name': form_template.name,
                'description': form_template.description,
                'form_fields': form_template.form_fields,
                'policy_info': {
                    'id': str(policy.id),
                    'title': policy.title,
                    'carrier': policy.carrier,
                    'subscription_type': policy.subscription_type,
                    'contract_period': policy.contract_period
                }
            }
            
            logger.info(f"주문서 양식 조회 성공: {policy.title} - {form_template.name}")
            
            return Response({
                'success': True,
                'data': template_data
            })
            
        except Exception as e:
            logger.error(f"주문서 양식 조회 실패: {str(e)} - 정책 ID: {policy_id}")
            return Response({
                'error': '주문서 양식 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 참고: TelecomOrder 관련 뷰들은 Order 모델 통합으로 인해 제거됨
# 새로운 주문 관리는 orders/order_views.py의 OrderViewSet을 사용
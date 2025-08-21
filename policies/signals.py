"""
정책 관련 시그널 처리
정책 저장 시 자동으로 최신 주문서 양식을 적용하기 위한 시그널 핸들러
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Policy
from .utils.order_form_manager import OrderFormManager

logger = logging.getLogger('policies')


@receiver(post_save, sender=Policy)
def ensure_latest_order_form(sender, instance, created, **kwargs):
    """
    정책이 저장될 때마다 최신 주문서 양식이 적용되어 있는지 확인하고,
    없거나 오래된 경우 최신 양식을 적용합니다.
    
    Args:
        sender: 시그널을 보낸 모델 (Policy)
        instance: 저장된 Policy 인스턴스
        created: 새로 생성된 인스턴스인지 여부
    """
    try:
        # OrderFormManager를 사용하여 주문서 양식 관리
        OrderFormManager.ensure_latest_order_form(instance)
        
        if created:
            logger.info(f"새 정책 '{instance.title}'에 기본 주문서 양식이 자동 적용되었습니다.")
        
    except Exception as e:
        logger.error(f"주문서 양식 자동 적용 중 오류 발생: {str(e)} - 정책: {instance.title}")

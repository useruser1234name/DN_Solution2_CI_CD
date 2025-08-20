"""
통신사 주문 관리 시스템 모델

이 모듈은 통신사 주문서 관리를 위한 모델들을 정의합니다.
주문 상태 추적, 이력 관리, 바코드 정보 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from companies.models import Company
from policies.models import Policy, CarrierPlan

logger = logging.getLogger('orders')


class TelecomOrder(models.Model):
    """
    통신사 주문서 모델
    통신사 가입 주문 정보를 관리
    """
    
    # 주문 상태 선택지
    STATUS_CHOICES = [
        ('received', '접수'),
        ('activation_request', '개통 요청'),
        ('activating', '개통중'),
        ('activation_complete', '개통 완료'),
        ('cancelled', '취소'),
        ('pending', '보류'),
        ('rejected', '반려'),
    ]
    
    # 가입 유형 선택지
    SUBSCRIPTION_TYPE_CHOICES = [
        ('MNP', '번호이동'),
        ('device_change', '기기변경'),
        ('new', '신규가입'),
    ]
    
    # 고객 유형 선택지
    CUSTOMER_TYPE_CHOICES = [
        ('adult', '성인일반'),
        ('corporate', '법인'),
        ('foreigner', '외국인'),
        ('minor', '미성년자'),
    ]
    
    # 기본 키는 UUID 사용
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="주문의 고유 식별자"
    )
    
    # 주문 번호 (자동 생성)
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="주문번호",
        help_text="자동 생성된 주문번호"
    )
    
    # 정책 연결
    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name='telecom_orders',
        verbose_name="정책",
        help_text="적용된 정책"
    )
    
    # 업체 정보
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='telecom_orders',
        verbose_name="접수 업체",
        help_text="주문을 접수한 업체"
    )
    
    # 접수자 정보
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_telecom_orders',
        verbose_name="접수자 (1차 ID)",
        help_text="주문을 접수한 사용자"
    )
    
    # 주문 상태
    current_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='received',
        verbose_name="현재 상태",
        help_text="주문의 현재 상태"
    )
    
    # ========== 자동 입력 정보 ==========
    received_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="접수일자",
        help_text="주문 접수 일시"
    )
    
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="개통일자",
        help_text="실제 개통 완료 일시"
    )
    
    carrier = models.CharField(
        max_length=10,
        verbose_name="통신사",
        help_text="정책에서 자동 입력"
    )
    
    subscription_type = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TYPE_CHOICES,
        verbose_name="가입유형",
        help_text="정책에서 자동 입력"
    )
    
    # 주문 데이터 (JSON 형태로 저장)
    order_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="주문 데이터",
        help_text="주문서 양식에서 제출된 모든 데이터"
    )
    
    # 시간 정보
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    def __str__(self):
        return f"{self.order_number} - {self.get_current_status_display()}"
    
    def save(self, *args, **kwargs):
        # 주문번호 자동 생성
        if not self.order_number:
            prefix = self.carrier[:2].upper()
            timestamp = timezone.now().strftime('%y%m%d%H%M')
            random_suffix = uuid.uuid4().hex[:4].upper()
            self.order_number = f"{prefix}-{timestamp}-{random_suffix}"
        
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """
    주문 상태 이력 모델
    모든 상태 변경을 추적하여 누적 관리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="상태 이력의 고유 식별자"
    )
    
    # 주문 연결
    order = models.ForeignKey(
        TelecomOrder,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="주문",
        help_text="상태 이력이 속한 주문"
    )
    
    # 상태 정보
    status = models.CharField(
        max_length=30,
        choices=TelecomOrder.STATUS_CHOICES,
        verbose_name="상태",
        help_text="변경된 상태"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="설명",
        help_text="상태 변경에 대한 설명"
    )
    
    # 변경자 정보
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_status_updates',
        verbose_name="변경자",
        help_text="상태를 변경한 사용자"
    )
    
    user_role = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="사용자 역할",
        help_text="변경자의 역할"
    )
    
    department = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="부서",
        help_text="변경자의 부서"
    )
    
    # IP 주소
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP 주소",
        help_text="변경이 발생한 IP 주소"
    )
    
    # 시간 정보
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시",
        help_text="상태 변경 일시"
    )
    
    class Meta:
        verbose_name = "주문 상태 이력"
        verbose_name_plural = "주문 상태 이력"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
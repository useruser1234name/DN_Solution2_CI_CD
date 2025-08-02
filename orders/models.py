"""
주문 관리 시스템 모델

이 모듈은 고객 주문 관리를 위한 모델들을 정의합니다.
주문 상태 관리, 송장 등록, 자동 메시지 발송 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from companies.models import Company
from policies.models import Policy

logger = logging.getLogger(__name__)


class Order(models.Model):
    """
    주문 모델
    
    고객 주문을 관리하는 핵심 모델입니다.
    주문 상태 관리, 송장 등록, 자동 메시지 발송 등을 포함합니다.
    """
    
    STATUS_CHOICES = [
        ('pending', '접수대기'),
        ('processing', '처리중'),
        ('shipped', '배송중'),
        ('completed', '완료'),
        ('cancelled', '취소'),
        ('return_requested', '반품요청'),
        ('exchanged', '교환완료'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        verbose_name='적용 정책'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='주문 업체'
    )
    customer_info = models.JSONField(verbose_name='고객 정보')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='주문 상태'
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='송장번호'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='총 금액'
    )
    rebate_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='리베이트 금액'
    )
    notes = models.TextField(blank=True, verbose_name='메모')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='주문일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '주문'
        verbose_name_plural = '주문'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['company']),
            models.Index(fields=['status']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"주문 #{self.id} - {self.customer_info.get('name', 'Unknown')}"
    
    def clean(self):
        """주문 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 금액 검증
        if self.total_amount <= 0:
            raise ValidationError("총 금액은 0보다 커야 합니다.")
        
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
        
        # 비활성 업체에 주문 생성 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 주문을 생성할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 리베이트 계산"""
        self.full_clean()
        is_new = self.pk is None
        
        # 리베이트 금액 자동 계산
        if is_new:
            self.calculate_rebate()
        
        if is_new:
            logger.info(f"[Order.save] 새 주문 생성 - ID: {self.id}, 고객: {self.customer_info.get('name', 'Unknown')}")
        else:
            logger.info(f"[Order.save] 주문 수정 - ID: {self.id}, 상태: {self.status}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Order.delete] 주문 삭제 - ID: {self.id}")
        super().delete(*args, **kwargs)
    
    def calculate_rebate(self):
        """리베이트 금액 계산"""
        # 정책 배정에서 실제 리베이트율 가져오기
        try:
            assignment = PolicyAssignment.objects.get(policy=self.policy, company=self.company)
            rebate_rate = assignment.get_effective_rebate()
        except PolicyAssignment.DoesNotExist:
            rebate_rate = self.policy.rebate_rate
        
        self.rebate_amount = (self.total_amount * rebate_rate) / 100
    
    def update_status(self, new_status, user=None):
        """
        주문 상태 업데이트
        
        Args:
            new_status: 새로운 상태
            user: 상태 변경자
        
        Raises:
            ValidationError: 유효하지 않은 상태 전환인 경우
        """
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValidationError("유효하지 않은 주문 상태입니다.")
        
        # 상태 전환 규칙 검증
        if not self.can_transition_to(new_status):
            raise ValidationError(f"'{self.get_status_display()}'에서 '{dict(self.STATUS_CHOICES)[new_status]}'로 변경할 수 없습니다.")
        
        old_status = self.status
        self.status = new_status
        self.save()
        
        logger.info(f"[Order.update_status] 주문 상태 변경 - ID: {self.id}, {old_status} → {new_status}, 변경자: {user.username if user else 'Unknown'}")
    
    def can_transition_to(self, new_status):
        """
        상태 전환 가능 여부 검증
        
        Args:
            new_status: 새로운 상태
        
        Returns:
            bool: 전환 가능 여부
        """
        # 상태 전환 규칙 정의
        transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['completed', 'return_requested'],
            'completed': ['return_requested'],
            'cancelled': [],
            'return_requested': ['exchanged'],
            'exchanged': [],
        }
        
        return new_status in transitions.get(self.status, [])
    
    def add_tracking_number(self, tracking_number, user=None):
        """
        송장번호 등록
        
        Args:
            tracking_number: 송장번호
            user: 등록자
        """
        self.tracking_number = tracking_number
        self.update_status('shipped', user)
        
        logger.info(f"[Order.add_tracking_number] 송장번호 등록 - ID: {self.id}, 송장번호: {tracking_number}")


class OrderMemo(models.Model):
    """
    주문 메모 모델
    
    주문 처리 과정에서 발생하는 메모를 기록합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='memos',
        verbose_name='주문'
    )
    content = models.TextField(verbose_name='메모 내용')
    created_by = models.ForeignKey(
        'companies.CompanyUser',
        on_delete=models.CASCADE,
        verbose_name='작성자'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    
    class Meta:
        verbose_name = '주문 메모'
        verbose_name_plural = '주문 메모'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"메모 - {self.order.id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[OrderMemo.save] 새 주문 메모 생성 - 주문: {self.order.id}, 작성자: {self.created_by.username}")
        else:
            logger.info(f"[OrderMemo.save] 주문 메모 수정 - 주문: {self.order.id}, 작성자: {self.created_by.username}")
        
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    송장 모델
    
    송장 정보를 관리하고 배송 완료 여부를 추적합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        verbose_name='주문'
    )
    tracking_number = models.CharField(max_length=100, verbose_name='송장번호')
    courier = models.CharField(max_length=50, verbose_name='택배사')
    is_delivered = models.BooleanField(default=False, verbose_name='배송완료 여부')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='배송완료일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '송장'
        verbose_name_plural = '송장'
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['courier']),
            models.Index(fields=['is_delivered']),
        ]
    
    def __str__(self):
        return f"송장 - {self.tracking_number} ({self.courier})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Invoice.save] 새 송장 생성 - 송장번호: {self.tracking_number}, 택배사: {self.courier}")
        else:
            logger.info(f"[Invoice.save] 송장 수정 - 송장번호: {self.tracking_number}, 택배사: {self.courier}")
        
        super().save(*args, **kwargs)
    
    def mark_as_delivered(self):
        """배송완료 처리"""
        self.is_delivered = True
        self.delivered_at = timezone.now()
        self.save()
        
        # 주문 상태를 완료로 변경
        self.order.update_status('completed')
        
        logger.info(f"[Invoice.mark_as_delivered] 배송완료 처리 - 송장번호: {self.tracking_number}")


class OrderRequest(models.Model):
    """
    주문 요청 모델
    
    고객의 교환/취소 요청을 관리합니다.
    """
    
    REQUEST_TYPES = [
        ('exchange', '교환'),
        ('cancel', '취소'),
        ('return', '반품'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '요청대기'),
        ('approved', '승인됨'),
        ('rejected', '거절됨'),
        ('completed', '완료'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='주문'
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name='요청 유형')
    reason = models.TextField(verbose_name='요청 사유')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='처리 상태'
    )
    processed_by = models.ForeignKey(
        'companies.CompanyUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='처리자'
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='요청일시')
    
    class Meta:
        verbose_name = '주문 요청'
        verbose_name_plural = '주문 요청'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['request_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_request_type_display()} 요청 - {self.order.id}"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[OrderRequest.save] 새 주문 요청 생성 - 주문: {self.order.id}, 유형: {self.request_type}")
        else:
            logger.info(f"[OrderRequest.save] 주문 요청 수정 - 주문: {self.order.id}, 상태: {self.status}")
        
        super().save(*args, **kwargs)
    
    def approve(self, processor):
        """
        요청 승인
        
        Args:
            processor: 처리자 (CompanyUser 인스턴스)
        """
        from django.utils import timezone
        
        self.status = 'approved'
        self.processed_by = processor
        self.processed_at = timezone.now()
        self.save()
        
        # 주문 상태 업데이트
        if self.request_type == 'cancel':
            self.order.update_status('cancelled', processor.django_user)
        elif self.request_type == 'return':
            self.order.update_status('return_requested', processor.django_user)
        
        logger.info(f"[OrderRequest.approve] 주문 요청 승인 - 주문: {self.order.id}, 처리자: {processor.username}")
    
    def reject(self, processor):
        """
        요청 거절
        
        Args:
            processor: 처리자 (CompanyUser 인스턴스)
        """
        from django.utils import timezone
        
        self.status = 'rejected'
        self.processed_by = processor
        self.processed_at = timezone.now()
        self.save()
        
        logger.info(f"[OrderRequest.reject] 주문 요청 거절 - 주문: {self.order.id}, 처리자: {processor.username}")

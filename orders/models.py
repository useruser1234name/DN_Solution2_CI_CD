"""
주문 관리 시스템 모델

이 모듈은 고객 주문 관리를 위한 모델들을 정의합니다.
주문 상태 관리, 송장 등록, 자동 메시지 발송 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from companies.models import Company
from policies.models import Policy

logger = logging.getLogger('orders')


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
    customer_name = models.CharField(max_length=100, verbose_name='고객명')
    customer_phone = models.CharField(max_length=20, verbose_name='고객 연락처')
    customer_email = models.EmailField(blank=True, verbose_name='고객 이메일')
    customer_address = models.TextField(verbose_name='배송 주소')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='주문 상태'
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
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='주문 생성자'
    )
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
            models.Index(fields=['customer_name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d')})"
    
    def clean(self):
        """주문 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 고객명 필수 입력
        if not self.customer_name or not self.customer_name.strip():
            raise ValidationError("고객명은 필수 입력 사항입니다.")
        
        # 연락처 필수 입력
        if not self.customer_phone or not self.customer_phone.strip():
            raise ValidationError("고객 연락처는 필수 입력 사항입니다.")
        
        # 배송 주소 필수 입력
        if not self.customer_address or not self.customer_address.strip():
            raise ValidationError("배송 주소는 필수 입력 사항입니다.")
        
        # 금액 검증
        if self.total_amount <= 0:
            raise ValidationError("총 금액은 0보다 커야 합니다.")
        
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 검증"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Order.save] 새 주문 생성 - 고객: {self.customer_name}, 금액: {self.total_amount}")
        else:
            logger.info(f"[Order.save] 주문 수정 - 고객: {self.customer_name}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Order.delete] 주문 삭제 - 고객: {self.customer_name}")
        super().delete(*args, **kwargs)
    
    def calculate_rebate(self):
        """리베이트 금액 계산"""
        try:
            # 정책의 리베이트 설정에 따라 계산
            if self.company.type == 'agency':
                rebate_rate = self.policy.rebate_agency
            elif self.company.type == 'retail':
                rebate_rate = self.policy.rebate_retail
            else:
                rebate_rate = 0
            
            self.rebate_amount = rebate_rate
            self.save()
            
            logger.info(f"리베이트 계산 완료: {self.customer_name} - {self.rebate_amount}원")
            return self.rebate_amount
        
        except Exception as e:
            logger.error(f"리베이트 계산 실패: {str(e)} - 주문: {self.customer_name}")
            return 0
    
    def update_status(self, new_status, user=None):
        """주문 상태 업데이트"""
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValidationError("유효하지 않은 주문 상태입니다.")
        
        old_status = self.status
        self.status = new_status
        self.save()
        
        logger.info(f"주문 상태 변경: {self.customer_name} - {old_status} → {new_status}")
        
        # 상태 변경 시 메모 추가
        if user:
            OrderMemo.objects.create(
                order=self,
                memo=f"주문 상태가 '{self.get_status_display()}'로 변경되었습니다.",
                created_by=user
            )
    
    def can_transition_to(self, new_status):
        """상태 전환 가능 여부 확인"""
        valid_transitions = {
            'pending': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['completed', 'return_requested'],
            'completed': ['return_requested'],
            'cancelled': [],
            'return_requested': ['exchanged'],
            'exchanged': ['completed'],
        }
        
        return new_status in valid_transitions.get(self.status, [])


class OrderMemo(models.Model):
    """
    주문 메모 모델
    
    주문에 대한 메모와 상태 변경 이력을 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='memos',
        verbose_name='주문'
    )
    memo = models.TextField(verbose_name='메모 내용')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='작성자'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    
    class Meta:
        verbose_name = "주문 메모"
        verbose_name_plural = "주문 메모 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.customer_name} - {self.memo[:50]}"
    
    def clean(self):
        """메모 내용 검증"""
        if not self.memo or not self.memo.strip():
            raise ValidationError("메모 내용은 필수 입력 사항입니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"주문 메모 생성: {self.order.customer_name} - {self.memo[:30]}")
        else:
            logger.info(f"주문 메모 수정: {self.order.customer_name}")
        
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    송장 모델
    
    송장 정보를 관리하고 배송 완료 여부를 추적합니다.
    """
    
    COURIER_CHOICES = [
        ('cj', 'CJ대한통운'),
        ('hanjin', '한진택배'),
        ('lotte', '롯데택배'),
        ('logen', '로젠택배'),
        ('epost', '우체국택배'),
        ('daesin', '대신택배'),
        ('hyundai', '현대택배'),
        ('kg', 'KG로지스'),
        ('kde', '경동택배'),
        ('dongbu', '동부택배'),
        ('other', '기타'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name='주문'
    )
    courier = models.CharField(
        max_length=20,
        choices=COURIER_CHOICES,
        verbose_name='택배사'
    )
    invoice_number = models.CharField(max_length=100, verbose_name='송장번호')
    recipient_name = models.CharField(max_length=100, blank=True, verbose_name='수취인명')
    recipient_phone = models.CharField(max_length=20, blank=True, verbose_name='수취인 연락처')
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='발송일시')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='배송완료일시')
    
    class Meta:
        verbose_name = "송장"
        verbose_name_plural = "송장 목록"
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['courier', 'invoice_number']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['delivered_at']),
        ]
    
    def __str__(self):
        return f"{self.order.customer_name} - {self.get_courier_display()} ({self.invoice_number})"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.invoice_number or not self.invoice_number.strip():
            raise ValidationError("송장 번호는 필수 입력 사항입니다.")
        
        # 동일 송장번호 중복 검사 (같은 택배사 내에서)
        existing = Invoice.objects.filter(
            courier=self.courier,
            invoice_number=self.invoice_number
        ).exclude(id=self.id)
        
        if existing.exists():
            raise ValidationError("동일한 택배사에서 중복된 송장 번호가 존재합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 주문 상태 자동 완료 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            
            # 수취인 정보가 없으면 주문 고객 정보 사용
            if not self.recipient_name:
                self.recipient_name = self.order.customer_name
            
            if not self.recipient_phone:
                self.recipient_phone = self.order.customer_phone
            
            super().save(*args, **kwargs)
            
            # 주문 상태를 완료로 자동 변경
            if self.order.status != 'completed':
                self.order.update_status('completed')
            
            if is_new:
                logger.info(f"송장이 등록되었습니다: {self.order.customer_name} - {self.get_courier_display()} ({self.invoice_number})")
            else:
                logger.info(f"송장 정보가 수정되었습니다: {self.order.customer_name} (송장 ID: {self.id})")
        
        except Exception as e:
            logger.error(f"송장 저장 중 오류 발생: {str(e)} - 주문: {self.order.customer_name}")
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅 처리"""
        customer_name = self.order.customer_name
        invoice_info = f"{self.get_courier_display()} ({self.invoice_number})"
        
        try:
            super().delete(*args, **kwargs)
            logger.info(f"송장이 삭제되었습니다: {customer_name} - {invoice_info}")
        
        except Exception as e:
            logger.error(f"송장 삭제 중 오류 발생: {str(e)} - 고객: {customer_name}")
            raise
    
    def mark_as_delivered(self, delivered_at=None):
        """배송 완료 처리"""
        try:
            from django.utils import timezone
            
            if delivered_at is None:
                delivered_at = timezone.now()
            
            self.delivered_at = delivered_at
            self.save()
            
            logger.info(f"배송 완료 처리: {self.order.customer_name} - {self.invoice_number}")
            return True
        
        except Exception as e:
            logger.error(f"배송 완료 처리 중 오류 발생: {str(e)} - 송장: {self.invoice_number}")
            return False
    
    def is_delivered(self):
        """배송 완료 여부 확인"""
        return self.delivered_at is not None
    
    def get_delivery_status(self):
        """배송 상태 텍스트 반환"""
        if self.is_delivered():
            return "배송완료"
        else:
            return "배송중"


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
        related_name='requests',
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
        User,
        on_delete=models.SET_NULL,
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
            models.Index(fields=['order', 'request_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.customer_name} - {self.get_request_type_display()} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"주문 요청 생성: {self.order.customer_name} - {self.get_request_type_display()}")
        else:
            logger.info(f"주문 요청 수정: {self.order.customer_name} - {self.get_status_display()}")
        
        super().save(*args, **kwargs)
    
    def approve(self, processor):
        """요청 승인"""
        from django.utils import timezone
        
        self.status = 'approved'
        self.processed_by = processor
        self.processed_at = timezone.now()
        self.save()
        
        logger.info(f"주문 요청 승인: {self.order.customer_name} - {self.get_request_type_display()}")
    
    def reject(self, processor):
        """요청 거절"""
        from django.utils import timezone
        
        self.status = 'rejected'
        self.processed_by = processor
        self.processed_at = timezone.now()
        self.save()
        
        logger.info(f"주문 요청 거절: {self.order.customer_name} - {self.get_request_type_display()}")
    
    def complete(self, processor):
        """요청 완료"""
        from django.utils import timezone
        
        self.status = 'completed'
        self.processed_by = processor
        self.processed_at = timezone.now()
        self.save()
        
        logger.info(f"주문 요청 완료: {self.order.customer_name} - {self.get_request_type_display()}")

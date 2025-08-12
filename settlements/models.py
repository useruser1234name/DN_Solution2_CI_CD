"""
정산 시스템 모델
주문 완료 시 자동 정산 및 계층별 리베이트 분배
"""

import uuid
import logging
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from companies.models import Company
from orders.models import Order
from policies.models import Policy, RebateMatrix

logger = logging.getLogger(__name__)


class Settlement(models.Model):
    """
    정산 모델
    주문 완료 시 자동으로 생성되며 계층별 리베이트를 관리
    """
    
    STATUS_CHOICES = [
        ('pending', '정산 대기'),
        ('approved', '승인됨'),
        ('paid', '지급 완료'),
        ('cancelled', '취소됨'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='정산 ID'
    )
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name='주문'
    )
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='settlements',
        verbose_name='정산 대상 업체'
    )
    
    # 리베이트 금액
    rebate_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='리베이트 금액'
    )
    
    # 정산 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='정산 상태'
    )
    
    # 승인 정보
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_settlements',
        verbose_name='승인자'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='승인일시'
    )
    
    # 지급 정보
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='지급일시'
    )
    
    # 메모
    notes = models.TextField(
        blank=True,
        verbose_name='메모'
    )
    
    # 시간 정보
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    class Meta:
        verbose_name = '정산'
        verbose_name_plural = '정산 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'company']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        unique_together = ['order', 'company']
    
    def __str__(self):
        return f"{self.company.name} - {self.rebate_amount:,}원 ({self.get_status_display()})"
    
    def clean(self):
        """유효성 검증"""
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
        
        # 이미 지급된 정산은 수정 불가
        if self.pk and self.status == 'paid':
            existing = Settlement.objects.get(pk=self.pk)
            if existing.status == 'paid':
                raise ValidationError("이미 지급 완료된 정산은 수정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"정산 생성: {self.company.name} - {self.rebate_amount:,}원")
            else:
                logger.info(f"정산 수정: {self.company.name} - {self.status}")
        
        except Exception as e:
            logger.error(f"정산 저장 실패: {str(e)}")
            raise
    
    def approve(self, user):
        """정산 승인"""
        if self.status != 'pending':
            raise ValidationError("대기 중인 정산만 승인할 수 있습니다.")
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        
        logger.info(f"정산 승인: {self.company.name} - {self.rebate_amount:,}원")
    
    def mark_as_paid(self):
        """지급 완료 처리"""
        if self.status != 'approved':
            raise ValidationError("승인된 정산만 지급 처리할 수 있습니다.")
        
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()
        
        logger.info(f"정산 지급 완료: {self.company.name} - {self.rebate_amount:,}원")
    
    def cancel(self, reason=''):
        """정산 취소"""
        if self.status == 'paid':
            raise ValidationError("이미 지급된 정산은 취소할 수 없습니다.")
        
        self.status = 'cancelled'
        if reason:
            self.notes = f"취소 사유: {reason}\n{self.notes}"
        self.save()
        
        logger.info(f"정산 취소: {self.company.name} - {self.rebate_amount:,}원")
    
    @classmethod
    def create_for_order(cls, order):
        """
        주문에 대한 정산 생성
        계층 구조에 따라 리베이트 분배
        """
        if order.status not in ['completed', 'shipped']:
            raise ValidationError("완료되거나 배송 중인 주문만 정산할 수 있습니다.")
        
        settlements = []
        
        try:
            with transaction.atomic():
                # 주문 업체의 계층 구조 파악
                order_company = order.company
                policy = order.policy
                
                # 리베이트 매트릭스에서 금액 조회
                # 실제 구현에서는 주문의 요금제, 가입기간 정보가 필요
                # 여기서는 기본 리베이트 사용
                total_rebate = order.rebate_amount or Decimal('0')
                
                if order_company.company_type == 'retail':
                    # 판매점인 경우
                    # 1. 판매점 정산
                    retail_settlement = cls.objects.create(
                        order=order,
                        company=order_company,
                        rebate_amount=total_rebate * Decimal('0.7')  # 70%
                    )
                    settlements.append(retail_settlement)
                    
                    # 2. 협력사 정산 (있는 경우)
                    if order_company.parent_company:
                        agency_settlement = cls.objects.create(
                            order=order,
                            company=order_company.parent_company,
                            rebate_amount=total_rebate * Decimal('0.3')  # 30%
                        )
                        settlements.append(agency_settlement)
                
                elif order_company.company_type == 'agency':
                    # 협력사인 경우
                    agency_settlement = cls.objects.create(
                        order=order,
                        company=order_company,
                        rebate_amount=total_rebate
                    )
                    settlements.append(agency_settlement)
                
                elif order_company.company_type == 'headquarters':
                    # 본사인 경우 (직접 판매)
                    hq_settlement = cls.objects.create(
                        order=order,
                        company=order_company,
                        rebate_amount=total_rebate
                    )
                    settlements.append(hq_settlement)
                
                logger.info(f"주문 {order.id}에 대한 정산 {len(settlements)}건 생성 완료")
                
        except Exception as e:
            logger.error(f"정산 생성 실패: {str(e)}")
            raise
        
        return settlements


class SettlementBatch(models.Model):
    """
    정산 배치 모델
    여러 정산을 묶어서 일괄 처리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='배치 ID'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='배치명'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='설명'
    )
    
    # 정산 기간
    start_date = models.DateField(
        verbose_name='시작일'
    )
    
    end_date = models.DateField(
        verbose_name='종료일'
    )
    
    # 총 금액
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='총 정산 금액'
    )
    
    # 생성 정보
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='생성자'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    # 승인 정보
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_batches',
        verbose_name='승인자'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='승인일시'
    )
    
    class Meta:
        verbose_name = '정산 배치'
        verbose_name_plural = '정산 배치 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date} ~ {self.end_date})"
    
    def clean(self):
        """유효성 검증"""
        if self.start_date > self.end_date:
            raise ValidationError("시작일이 종료일보다 늦을 수 없습니다.")
    
    def calculate_total(self):
        """배치에 포함된 정산들의 총액 계산"""
        total = self.settlements.filter(
            status__in=['approved', 'paid']
        ).aggregate(
            total=models.Sum('rebate_amount')
        )['total'] or Decimal('0')
        
        self.total_amount = total
        self.save()
        
        return total
    
    def approve_all(self, user):
        """배치의 모든 정산 승인"""
        pending_settlements = self.settlements.filter(status='pending')
        count = 0
        
        for settlement in pending_settlements:
            try:
                settlement.approve(user)
                count += 1
            except Exception as e:
                logger.error(f"정산 승인 실패: {settlement.id} - {str(e)}")
        
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        
        logger.info(f"배치 '{self.title}' 승인 완료: {count}건")
        return count


class SettlementBatchItem(models.Model):
    """
    정산 배치 항목
    배치와 개별 정산을 연결
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    batch = models.ForeignKey(
        SettlementBatch,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='배치'
    )
    
    settlement = models.ForeignKey(
        Settlement,
        on_delete=models.CASCADE,
        related_name='batch_items',
        verbose_name='정산'
    )
    
    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='추가일시'
    )
    
    class Meta:
        verbose_name = '정산 배치 항목'
        verbose_name_plural = '정산 배치 항목'
        unique_together = ['batch', 'settlement']
        indexes = [
            models.Index(fields=['batch', 'settlement']),
        ]
    
    def __str__(self):
        return f"{self.batch.title} - {self.settlement}"
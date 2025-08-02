"""
재고 관리 시스템 모델

이 모듈은 기기 및 재고 관리를 위한 모델들을 정의합니다.
기기 등록, 재고 추적, 권한별 접근 제어 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from companies.models import Company

logger = logging.getLogger(__name__)


class Device(models.Model):
    """
    기기 모델
    
    기기 정보를 관리하는 핵심 모델입니다.
    기기 유형, 상태, 소유 업체 등을 관리합니다.
    """
    
    DEVICE_TYPES = [
        ('phone', '휴대폰'),
        ('tablet', '태블릿'),
        ('laptop', '노트북'),
        ('desktop', '데스크톱'),
        ('accessory', '액세서리'),
        ('other', '기타'),
    ]
    
    STATUS_CHOICES = [
        ('available', '사용가능'),
        ('in_use', '사용중'),
        ('maintenance', '정비중'),
        ('retired', '폐기'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='소유 업체'
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, verbose_name='기기 유형')
    model_name = models.CharField(max_length=100, verbose_name='모델명')
    serial_number = models.CharField(max_length=100, unique=True, verbose_name='시리얼번호')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='상태'
    )
    purchase_date = models.DateField(verbose_name='구매일')
    warranty_expiry = models.DateField(null=True, blank=True, verbose_name='보증만료일')
    notes = models.TextField(blank=True, verbose_name='메모')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '기기'
        verbose_name_plural = '기기'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['device_type']),
            models.Index(fields=['status']),
            models.Index(fields=['serial_number']),
        ]
    
    def __str__(self):
        return f"{self.model_name} ({self.get_device_type_display()})"
    
    def clean(self):
        """기기 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 시리얼번호 중복 검사
        if Device.objects.filter(serial_number=self.serial_number).exclude(pk=self.pk).exists():
            raise ValidationError("이미 등록된 시리얼번호입니다.")
        
        # 비활성 업체에 기기 등록 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 기기를 등록할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Device.save] 새 기기 등록 - 모델: {self.model_name}, 업체: {self.company.name}")
        else:
            logger.info(f"[Device.save] 기기 수정 - 모델: {self.model_name}, 상태: {self.status}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Device.delete] 기기 삭제 - 모델: {self.model_name}, 시리얼번호: {self.serial_number}")
        super().delete(*args, **kwargs)
    
    @property
    def is_available(self):
        """사용 가능 여부"""
        return self.status == 'available'
    
    @property
    def is_warranty_valid(self):
        """보증 유효 여부"""
        from django.utils import timezone
        if not self.warranty_expiry:
            return False
        return self.warranty_expiry >= timezone.now().date()


class Inventory(models.Model):
    """
    재고 모델
    
    각 업체별 재고를 관리합니다.
    권한별 접근 제어를 포함합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='소유 업체'
    )
    product_name = models.CharField(max_length=200, verbose_name='상품명')
    product_code = models.CharField(max_length=100, verbose_name='상품코드')
    quantity = models.IntegerField(default=0, verbose_name='수량')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='단가'
    )
    min_stock = models.IntegerField(default=0, verbose_name='최소재고')
    max_stock = models.IntegerField(default=1000, verbose_name='최대재고')
    location = models.CharField(max_length=100, blank=True, verbose_name='보관위치')
    notes = models.TextField(blank=True, verbose_name='메모')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '재고'
        verbose_name_plural = '재고'
        unique_together = ['company', 'product_code']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['product_code']),
            models.Index(fields=['quantity']),
        ]
    
    def __str__(self):
        return f"{self.product_name} ({self.company.name}) - {self.quantity}개"
    
    def clean(self):
        """재고 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 수량 검증
        if self.quantity < 0:
            raise ValidationError("수량은 0 이상이어야 합니다.")
        
        if self.min_stock < 0:
            raise ValidationError("최소재고는 0 이상이어야 합니다.")
        
        if self.max_stock <= self.min_stock:
            raise ValidationError("최대재고는 최소재고보다 커야 합니다.")
        
        # 비활성 업체에 재고 등록 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 재고를 등록할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Inventory.save] 새 재고 등록 - 상품: {self.product_name}, 업체: {self.company.name}")
        else:
            logger.info(f"[Inventory.save] 재고 수정 - 상품: {self.product_name}, 수량: {self.quantity}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Inventory.delete] 재고 삭제 - 상품: {self.product_name}, 업체: {self.company.name}")
        super().delete(*args, **kwargs)
    
    @property
    def total_value(self):
        """총 재고 가치"""
        return self.quantity * self.unit_price
    
    @property
    def is_low_stock(self):
        """재고 부족 여부"""
        return self.quantity <= self.min_stock
    
    @property
    def is_overstock(self):
        """재고 과다 여부"""
        return self.quantity >= self.max_stock
    
    def add_stock(self, quantity, user=None):
        """
        재고 추가
        
        Args:
            quantity: 추가할 수량
            user: 처리자
        """
        if quantity <= 0:
            raise ValidationError("추가할 수량은 0보다 커야 합니다.")
        
        self.quantity += quantity
        self.save()
        
        logger.info(f"[Inventory.add_stock] 재고 추가 - 상품: {self.product_name}, 수량: +{quantity}, 처리자: {user.username if user else 'Unknown'}")
    
    def remove_stock(self, quantity, user=None):
        """
        재고 차감
        
        Args:
            quantity: 차감할 수량
            user: 처리자
        """
        if quantity <= 0:
            raise ValidationError("차감할 수량은 0보다 커야 합니다.")
        
        if self.quantity < quantity:
            raise ValidationError("현재 재고보다 많은 수량을 차감할 수 없습니다.")
        
        self.quantity -= quantity
        self.save()
        
        logger.info(f"[Inventory.remove_stock] 재고 차감 - 상품: {self.product_name}, 수량: -{quantity}, 처리자: {user.username if user else 'Unknown'}")


class DeviceLog(models.Model):
    """
    기기 로그 모델
    
    기기 사용 이력을 관리합니다.
    """
    
    LOG_TYPES = [
        ('checkout', '대여'),
        ('checkin', '반납'),
        ('maintenance', '정비'),
        ('repair', '수리'),
        ('retire', '폐기'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        verbose_name='기기'
    )
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, verbose_name='로그 유형')
    user = models.ForeignKey(
        'companies.CompanyUser',
        on_delete=models.CASCADE,
        verbose_name='처리자'
    )
    notes = models.TextField(blank=True, verbose_name='메모')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='처리일시')
    
    class Meta:
        verbose_name = '기기 로그'
        verbose_name_plural = '기기 로그'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device']),
            models.Index(fields=['log_type']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.device.model_name} - {self.get_log_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[DeviceLog.save] 새 기기 로그 생성 - 기기: {self.device.model_name}, 유형: {self.log_type}, 처리자: {self.user.username}")
        else:
            logger.info(f"[DeviceLog.save] 기기 로그 수정 - 기기: {self.device.model_name}, 유형: {self.log_type}")
        
        super().save(*args, **kwargs)


class InventoryTransaction(models.Model):
    """
    재고 거래 모델
    
    재고 입출고 이력을 관리합니다.
    """
    
    TRANSACTION_TYPES = [
        ('in', '입고'),
        ('out', '출고'),
        ('adjustment', '조정'),
        ('return', '반품'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        verbose_name='재고'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='거래 유형')
    quantity = models.IntegerField(verbose_name='수량')
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='단가'
    )
    user = models.ForeignKey(
        'companies.CompanyUser',
        on_delete=models.CASCADE,
        verbose_name='처리자'
    )
    reference = models.CharField(max_length=100, blank=True, verbose_name='참조번호')
    notes = models.TextField(blank=True, verbose_name='메모')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='거래일시')
    
    class Meta:
        verbose_name = '재고 거래'
        verbose_name_plural = '재고 거래'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['inventory']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.inventory.product_name} - {self.get_transaction_type_display()} ({self.quantity}개)"
    
    def clean(self):
        """거래 생성 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 수량 검증
        if self.quantity == 0:
            raise ValidationError("수량은 0이 될 수 없습니다.")
        
        # 출고 시 재고 확인
        if self.transaction_type in ['out', 'adjustment'] and self.quantity > 0:
            if self.inventory.quantity < self.quantity:
                raise ValidationError("현재 재고보다 많은 수량을 출고할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 재고 업데이트"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            # 재고 업데이트
            if self.transaction_type == 'in':
                self.inventory.add_stock(self.quantity, self.user.django_user)
            elif self.transaction_type == 'out':
                self.inventory.remove_stock(self.quantity, self.user.django_user)
            elif self.transaction_type == 'adjustment':
                if self.quantity > 0:
                    self.inventory.add_stock(self.quantity, self.user.django_user)
                else:
                    self.inventory.remove_stock(abs(self.quantity), self.user.django_user)
            
            logger.info(f"[InventoryTransaction.save] 새 재고 거래 생성 - 상품: {self.inventory.product_name}, 유형: {self.transaction_type}, 수량: {self.quantity}")
        else:
            logger.info(f"[InventoryTransaction.save] 재고 거래 수정 - 상품: {self.inventory.product_name}, 유형: {self.transaction_type}")
        
        super().save(*args, **kwargs)
    
    @property
    def total_amount(self):
        """거래 총액"""
        return self.quantity * self.unit_price

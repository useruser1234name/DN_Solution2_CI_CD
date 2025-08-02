"""
정책 관리 시스템 모델

이 모듈은 상품 정책 관리를 위한 모델들을 정의합니다.
리베이트 설정, HTML 자동 생성, 접수 방식 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from companies.models import Company

logger = logging.getLogger(__name__)


class Policy(models.Model):
    """
    정책 모델
    
    상품 정책을 관리하는 핵심 모델입니다.
    리베이트 설정, HTML 자동 생성, 접수 방식 등을 포함합니다.
    """
    
    RECEPTION_TYPES = [
        ('general', '일반'),
        ('link', '링크'),
        ('registration', '등록'),
        ('egg', '에그'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='등록 업체'
    )
    title = models.CharField(max_length=200, verbose_name='정책 제목')
    description = models.TextField(verbose_name='정책 설명')
    rebate_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name='기본 리베이트율 (%)'
    )
    reception_type = models.CharField(
        max_length=20, 
        choices=RECEPTION_TYPES,
        verbose_name='접수 방식'
    )
    html_content = models.TextField(blank=True, verbose_name='HTML 내용')
    is_shared = models.BooleanField(default=False, verbose_name='공유 여부')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '정책'
        verbose_name_plural = '정책'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['reception_type']),
            models.Index(fields=['is_shared']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.company.name})"
    
    def clean(self):
        """정책 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 리베이트율 범위 검증
        if self.rebate_rate < 0 or self.rebate_rate > 100:
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 비활성 업체에 정책 등록 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 정책을 등록할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 HTML 자동 생성"""
        self.full_clean()
        is_new = self.pk is None
        
        # HTML 내용 자동 생성
        if not self.html_content:
            self.html_content = self.generate_html_content()
        
        if is_new:
            logger.info(f"[Policy.save] 새 정책 생성 - 제목: {self.title}, 업체: {self.company.name}")
        else:
            logger.info(f"[Policy.save] 정책 수정 - 제목: {self.title}, 업체: {self.company.name}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Policy.delete] 정책 삭제 - 제목: {self.title}, 업체: {self.company.name}")
        super().delete(*args, **kwargs)
    
    def generate_html_content(self):
        """
        HTML 내용 자동 생성
        
        Returns:
            str: 생성된 HTML 내용
        """
        html_template = f"""
        <div class="policy-detail">
            <h2>{self.title}</h2>
            <div class="policy-info">
                <p><strong>업체:</strong> {self.company.name}</p>
                <p><strong>리베이트율:</strong> {self.rebate_rate}%</p>
                <p><strong>접수방식:</strong> {self.get_reception_type_display()}</p>
            </div>
            <div class="policy-description">
                <h3>정책 설명</h3>
                <p>{self.description}</p>
            </div>
            <div class="policy-actions">
                <button class="btn btn-primary" onclick="applyPolicy('{self.id}')">정책 신청</button>
            </div>
        </div>
        """
        return html_template
    
    def toggle_share(self):
        """공유 상태 토글"""
        self.is_shared = not self.is_shared
        self.save()
        logger.info(f"[Policy.toggle_share] 정책 공유 상태 변경 - 제목: {self.title}, 공유: {self.is_shared}")
    
    def toggle_active(self):
        """활성화 상태 토글"""
        self.is_active = not self.is_active
        self.save()
        logger.info(f"[Policy.toggle_active] 정책 활성화 상태 변경 - 제목: {self.title}, 활성화: {self.is_active}")


class PolicyAssignment(models.Model):
    """
    정책 배정 모델
    
    특정 정책을 특정 업체에 배정하고 커스텀 리베이트율을 설정합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        verbose_name='정책'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='배정 업체'
    )
    custom_rebate_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='커스텀 리베이트율 (%)'
    )
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='배정일시')
    
    class Meta:
        verbose_name = '정책 배정'
        verbose_name_plural = '정책 배정'
        unique_together = ['policy', 'company']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['company']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} → {self.company.name}"
    
    def clean(self):
        """정책 배정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 커스텀 리베이트율 범위 검증
        if self.custom_rebate_rate and (self.custom_rebate_rate < 0 or self.custom_rebate_rate > 100):
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 비활성 업체에 정책 배정 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 정책을 배정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[PolicyAssignment.save] 새 정책 배정 - 정책: {self.policy.title}, 업체: {self.company.name}")
        else:
            logger.info(f"[PolicyAssignment.save] 정책 배정 수정 - 정책: {self.policy.title}, 업체: {self.company.name}")
        
        super().save(*args, **kwargs)
    
    def get_effective_rebate(self):
        """
        실제 적용되는 리베이트율 반환
        
        Returns:
            Decimal: 커스텀 리베이트율이 있으면 커스텀값, 없으면 기본값
        """
        return self.custom_rebate_rate if self.custom_rebate_rate else self.policy.rebate_rate


class PolicyShare(models.Model):
    """
    정책 공유 모델
    
    검증된 업체 간 정책 공유를 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='shared_from',
        verbose_name='원본 정책'
    )
    target_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='대상 업체'
    )
    shared_rebate_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='공유 리베이트율 (%)'
    )
    is_approved = models.BooleanField(default=False, verbose_name='승인 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='공유 요청일시')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='승인일시')
    
    class Meta:
        verbose_name = '정책 공유'
        verbose_name_plural = '정책 공유'
        unique_together = ['source_policy', 'target_company']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_policy']),
            models.Index(fields=['target_company']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.source_policy.title} → {self.target_company.name}"
    
    def clean(self):
        """정책 공유 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 리베이트율 범위 검증
        if self.shared_rebate_rate < 0 or self.shared_rebate_rate > 100:
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 같은 업체 간 공유 금지
        if self.source_policy.company == self.target_company:
            raise ValidationError("같은 업체 간에는 정책을 공유할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[PolicyShare.save] 새 정책 공유 요청 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
        else:
            logger.info(f"[PolicyShare.save] 정책 공유 수정 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
        
        super().save(*args, **kwargs)
    
    def approve(self):
        """정책 공유 승인"""
        from django.utils import timezone
        
        self.is_approved = True
        self.approved_at = timezone.now()
        self.save()
        
        logger.info(f"[PolicyShare.approve] 정책 공유 승인 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
    
    def reject(self):
        """정책 공유 거절"""
        self.is_approved = False
        self.save()
        
        logger.info(f"[PolicyShare.reject] 정책 공유 거절 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")

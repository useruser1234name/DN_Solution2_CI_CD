"""
업체 관리 시스템 모델

이 모듈은 업체 및 사용자 관리를 위한 핵심 모델들을 정의합니다.
단일 책임 원칙을 준수하여 각 모델이 명확한 역할을 가지도록 설계되었습니다.
"""

import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger(__name__)


class Company(models.Model):
    """
    업체 모델
    
    본사, 협력사, 대리점, 판매점을 관리하는 핵심 모델입니다.
    계층 구조를 통해 상위-하위 관계를 관리합니다.
    """
    
    COMPANY_TYPES = [
        ('headquarters', '본사'),
        ('agency', '협력사'),
        ('dealer', '대리점'),
        ('retail', '판매점'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name='업체 코드')
    name = models.CharField(max_length=100, verbose_name='업체명')
    type = models.CharField(max_length=20, choices=COMPANY_TYPES, verbose_name='업체 유형')
    parent_company = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        verbose_name='상위 업체'
    )
    status = models.BooleanField(default=True, verbose_name='운영 상태')
    visible = models.BooleanField(default=True, verbose_name='노출 여부')
    default_courier = models.CharField(max_length=50, blank=True, verbose_name='기본 택배사')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '업체'
        verbose_name_plural = '업체'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['type']),
            models.Index(fields=['parent_company']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def clean(self):
        """업체 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 본사는 상위 업체를 가질 수 없음
        if self.type == 'headquarters' and self.parent_company:
            raise ValidationError("본사는 상위 업체를 가질 수 없습니다.")
        
        # 협력사는 본사를 상위 업체로 가져야 함
        if self.type == 'agency' and (not self.parent_company or self.parent_company.type != 'headquarters'):
            raise ValidationError("협력사는 본사를 상위 업체로 가져야 합니다.")
        
        # 판매점은 협력사를 상위 업체로 가져야 함
        if self.type == 'retail' and (not self.parent_company or self.parent_company.type != 'agency'):
            raise ValidationError("판매점은 협력사를 상위 업체로 가져야 합니다.")
        
        # 대리점은 본사를 상위 업체로 가져야 함
        if self.type == 'dealer' and (not self.parent_company or self.parent_company.type != 'headquarters'):
            raise ValidationError("대리점은 본사를 상위 업체로 가져야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 검증"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Company.save] 새 업체 생성 - 코드: {self.code}, 이름: {self.name}, 유형: {self.type}")
        else:
            logger.info(f"[Company.save] 업체 수정 - 코드: {self.code}, 이름: {self.name}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Company.delete] 업체 삭제 - 코드: {self.code}, 이름: {self.name}")
        super().delete(*args, **kwargs)
    
    @property
    def child_companies(self):
        """하위 업체 목록"""
        return Company.objects.filter(parent_company=self)
    
    @property
    def is_headquarters(self):
        """본사 여부"""
        return self.type == 'headquarters'
    
    @property
    def is_agency(self):
        """협력사 여부"""
        return self.type == 'agency'
    
    @property
    def is_dealer(self):
        """대리점 여부"""
        return self.type == 'dealer'
    
    @property
    def is_retail(self):
        """판매점 여부"""
        return self.type == 'retail'


class CompanyUser(models.Model):
    """
    업체 사용자 모델
    
    각 업체에 소속된 사용자를 관리합니다.
    승인 시스템을 통해 사용자 가입을 제어합니다.
    """
    
    ROLES = [
        ('admin', '관리자'),
        ('staff', '직원'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '승인 대기'),
        ('approved', '승인됨'),
        ('rejected', '거절됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE,
        verbose_name='소속 업체'
    )
    django_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='Django 사용자'
    )
    username = models.CharField(max_length=50, unique=True, verbose_name='사용자명')
    role = models.CharField(max_length=10, choices=ROLES, verbose_name='역할')
    is_approved = models.BooleanField(default=False, verbose_name='승인 여부')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='승인 상태'
    )
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='마지막 로그인')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '업체 사용자'
        verbose_name_plural = '업체 사용자'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['company']),
            models.Index(fields=['role']),
            models.Index(fields=['status']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.company.name})"
    
    def clean(self):
        """사용자 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 사용자명 중복 검사
        if CompanyUser.objects.filter(username=self.username).exclude(pk=self.pk).exists():
            raise ValidationError("이미 사용 중인 사용자명입니다.")
        
        # 비활성 업체에 사용자 추가 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 사용자를 추가할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 검증"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[CompanyUser.save] 새 사용자 생성 - 사용자명: {self.username}, 업체: {self.company.name}")
        else:
            logger.info(f"[CompanyUser.save] 사용자 수정 - 사용자명: {self.username}, 업체: {self.company.name}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[CompanyUser.delete] 사용자 삭제 - 사용자명: {self.username}, 업체: {self.company.name}")
        super().delete(*args, **kwargs)
    
    def can_be_approved_by(self, approver):
        """
        특정 사용자가 이 사용자를 승인할 수 있는지 검증
        
        Args:
            approver: 승인자 (CompanyUser 인스턴스)
        
        Returns:
            bool: 승인 가능 여부
        """
        # 슈퍼유저는 모든 사용자 승인 가능
        if approver.django_user.is_superuser:
            return True
        
        # 본사 관리자는 모든 사용자 승인 가능
        if approver.company.is_headquarters and approver.role == 'admin':
            return True
        
        # 협력사 관리자는 하위 판매점 사용자만 승인 가능
        if approver.company.is_agency and approver.role == 'admin':
            return self.company.parent_company == approver.company
        
        # 판매점 관리자는 직원만 승인 가능
        if approver.company.is_retail and approver.role == 'admin':
            return self.company == approver.company and self.role == 'staff'
        
        return False
    
    def approve(self, approver):
        """
        사용자 승인
        
        Args:
            approver: 승인자 (CompanyUser 인스턴스)
        
        Raises:
            ValidationError: 승인 권한이 없는 경우
        """
        if not self.can_be_approved_by(approver):
            raise ValidationError("승인 권한이 없습니다.")
        
        self.is_approved = True
        self.status = 'approved'
        self.save()
        
        logger.info(f"[CompanyUser.approve] 사용자 승인 - 사용자명: {self.username}, 승인자: {approver.username}")
    
    def reject(self, approver):
        """
        사용자 거절
        
        Args:
            approver: 거절자 (CompanyUser 인스턴스)
        
        Raises:
            ValidationError: 거절 권한이 없는 경우
        """
        if not self.can_be_approved_by(approver):
            raise ValidationError("거절 권한이 없습니다.")
        
        self.is_approved = False
        self.status = 'rejected'
        self.save()
        
        logger.info(f"[CompanyUser.reject] 사용자 거절 - 사용자명: {self.username}, 거절자: {approver.username}")


class CompanyMessage(models.Model):
    """
    업체 메시지 모델
    
    업체 간 공지사항 및 메시지를 관리합니다.
    일괄 발송과 개별 발송을 지원합니다.
    """
    
    MESSAGE_TYPES = [
        ('notice', '공지사항'),
        ('policy', '정책안내'),
        ('alert', '알림'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.TextField(verbose_name='메시지 내용')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, verbose_name='메시지 유형')
    is_bulk = models.BooleanField(default=False, verbose_name='일괄 발송 여부')
    sent_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='발송자'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='수신 업체'
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='발송일시')
    
    class Meta:
        verbose_name = '업체 메시지'
        verbose_name_plural = '업체 메시지'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['message_type']),
            models.Index(fields=['is_bulk']),
            models.Index(fields=['company']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.message[:50]}..."
    
    def clean(self):
        """메시지 생성 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 일괄 발송 시 개별 업체 지정 불가
        if self.is_bulk and self.company:
            raise ValidationError("일괄 발송 시 개별 업체를 지정할 수 없습니다.")
        
        # 개별 발송 시 업체 지정 필수
        if not self.is_bulk and not self.company:
            raise ValidationError("개별 발송 시 수신 업체를 지정해야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[CompanyMessage.save] 새 메시지 생성 - 유형: {self.message_type}, 발송자: {self.sent_by.username}")
        else:
            logger.info(f"[CompanyMessage.save] 메시지 수정 - 유형: {self.message_type}, 발송자: {self.sent_by.username}")
        
        super().save(*args, **kwargs)

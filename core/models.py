"""
Core models - 추상 베이스 모델
모든 앱에서 공통으로 사용하는 기본 모델
"""

import uuid
import logging
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TimestampedModel(models.Model):
    """
    타임스탬프 추상 모델
    생성일시와 수정일시를 자동으로 관리
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['-updated_at']),
        ]


class UUIDModel(TimestampedModel):
    """
    UUID 기반 추상 모델
    기본 키로 UUID 사용
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='고유 식별자'
    )
    
    class Meta:
        abstract = True


class LoggedModel(UUIDModel):
    """
    로깅 기능이 포함된 추상 모델
    생성, 수정, 삭제 시 자동 로깅
    """
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """저장 시 자동 검증 및 로깅"""
        is_new = self.pk is None
        
        # 모델 검증
        try:
            self.full_clean()
        except ValidationError as e:
            logger.error(f"{self.__class__.__name__} 검증 실패: {e}")
            raise
        
        # 로깅
        if is_new:
            logger.info(f"[CREATE] {self.__class__.__name__}: {self}")
        else:
            logger.info(f"[UPDATE] {self.__class__.__name__}: {self}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 자동 로깅"""
        logger.warning(f"[DELETE] {self.__class__.__name__}: {self}")
        super().delete(*args, **kwargs)


class SoftDeleteModel(LoggedModel):
    """
    소프트 삭제 모델
    실제로 삭제하지 않고 삭제 표시만 함
    """
    is_deleted = models.BooleanField(default=False, verbose_name='삭제 여부')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='삭제일시')
    deleted_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted_items',
        verbose_name='삭제자'
    )
    
    class Meta:
        abstract = True
    
    def delete(self, user=None, hard_delete=False):
        """소프트 삭제"""
        if hard_delete:
            super().delete()
        else:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            if user:
                self.deleted_by = user
            self.save()
            logger.info(f"[SOFT DELETE] {self.__class__.__name__}: {self}")
    
    def restore(self):
        """삭제 복원"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
        logger.info(f"[RESTORE] {self.__class__.__name__}: {self}")
    
    @classmethod
    def active_objects(cls):
        """활성(삭제되지 않은) 객체만 반환"""
        return cls.objects.filter(is_deleted=False)


class AuditModel(SoftDeleteModel):
    """
    감사 추적 모델
    생성자와 수정자를 자동으로 기록
    """
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_items',
        verbose_name='생성자'
    )
    modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_modified_items',
        verbose_name='수정자'
    )
    
    class Meta:
        abstract = True
    
    def save(self, user=None, *args, **kwargs):
        """저장 시 생성자/수정자 자동 설정"""
        is_new = self.pk is None
        
        if user:
            if is_new:
                self.created_by = user
            else:
                self.modified_by = user
        
        super().save(*args, **kwargs)


class StatusModel(models.Model):
    """
    상태 관리 추상 모델
    """
    STATUS_CHOICES = [
        ('active', '활성'),
        ('inactive', '비활성'),
        ('pending', '대기'),
        ('suspended', '중지'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='상태'
    )
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='상태 변경일시'
    )
    status_reason = models.TextField(
        blank=True,
        verbose_name='상태 변경 사유'
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['status']),
        ]
    
    def change_status(self, new_status, reason=''):
        """상태 변경"""
        old_status = self.status
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.status_reason = reason
        self.save()
        
        logger.info(
            f"[STATUS CHANGE] {self.__class__.__name__} {self.pk}: "
            f"{old_status} -> {new_status} (Reason: {reason})"
        )
    
    @property
    def is_active(self):
        """활성 상태 여부"""
        return self.status == 'active'


class SlugModel(models.Model):
    """
    슬러그 필드를 포함한 추상 모델
    URL-friendly 식별자 제공
    """
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name='슬러그'
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """저장 시 슬러그 자동 생성"""
        if not self.slug:
            from django.utils.text import slugify
            import random
            import string
            
            # 기본 슬러그 생성
            base_slug = slugify(str(self))
            if not base_slug:
                base_slug = 'item'
            
            # 유니크한 슬러그 생성
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)


class HierarchicalModel(models.Model):
    """
    계층 구조 추상 모델
    트리 구조를 구현하는 모델
    """
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='상위 항목'
    )
    level = models.PositiveIntegerField(
        default=0,
        verbose_name='계층 레벨'
    )
    path = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='경로'
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['parent', 'level']),
            models.Index(fields=['path']),
        ]
    
    def save(self, *args, **kwargs):
        """저장 시 레벨과 경로 자동 계산"""
        if self.parent:
            self.level = self.parent.level + 1
            parent_path = self.parent.path or str(self.parent.pk)
            self.path = f"{parent_path}/{self.pk}"
        else:
            self.level = 0
            self.path = str(self.pk) if self.pk else ''
        
        super().save(*args, **kwargs)
    
    def get_ancestors(self):
        """모든 상위 항목 조회"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_descendants(self):
        """모든 하위 항목 조회"""
        descendants = []
        
        def collect_descendants(node):
            for child in node.children.all():
                descendants.append(child)
                collect_descendants(child)
        
        collect_descendants(self)
        return descendants
    
    def get_siblings(self):
        """같은 레벨의 형제 항목 조회"""
        if self.parent:
            return self.parent.children.exclude(pk=self.pk)
        return self.__class__.objects.filter(parent__isnull=True).exclude(pk=self.pk)


# 보안 로그 모델
class SecurityLog(TimestampedModel):
    """
    보안 이벤트 로그 모델
    보안 관련 이벤트를 기록
    """
    EVENT_TYPES = [
        ('login_success', '로그인 성공'),
        ('login_failed', '로그인 실패'),
        ('logout', '로그아웃'),
        ('password_change', '비밀번호 변경'),
        ('permission_denied', '권한 거부'),
        ('suspicious_activity', '의심스러운 활동'),
        ('sql_injection_attempt', 'SQL Injection 시도'),
        ('xss_attempt', 'XSS 시도'),
        ('csrf_failure', 'CSRF 실패'),
    ]
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name='이벤트 유형'
    )
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='사용자'
    )
    ip_address = models.GenericIPAddressField(verbose_name='IP 주소')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    path = models.CharField(max_length=255, verbose_name='요청 경로')
    method = models.CharField(max_length=10, verbose_name='HTTP 메서드')
    details = models.JSONField(default=dict, verbose_name='상세 정보')
    
    class Meta:
        verbose_name = '보안 로그'
        verbose_name_plural = '보안 로그'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.ip_address} ({self.created_at})"

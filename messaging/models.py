"""
메시지 관리 시스템 모델

이 모듈은 SMS 발송, 예약 발송, 메시지 템플릿 등을 관리합니다.
외부 SMS API 연동을 위한 구조를 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from companies.models import Company, CompanyUser

logger = logging.getLogger(__name__)


class MessageTemplate(models.Model):
    """
    메시지 템플릿 모델
    
    재사용 가능한 메시지 템플릿을 관리합니다.
    """
    
    TEMPLATE_TYPES = [
        ('order_status', '주문상태'),
        ('approval', '승인'),
        ('notification', '알림'),
        ('marketing', '마케팅'),
        ('custom', '커스텀'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='템플릿명')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='템플릿 유형')
    content = models.TextField(verbose_name='메시지 내용')
    variables = models.JSONField(default=dict, verbose_name='변수 목록')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_by = models.ForeignKey(
        CompanyUser,
        on_delete=models.CASCADE,
        verbose_name='생성자'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '메시지 템플릿'
        verbose_name_plural = '메시지 템플릿'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def clean(self):
        """템플릿 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 템플릿명 중복 검사
        if MessageTemplate.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError("이미 존재하는 템플릿명입니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[MessageTemplate.save] 새 메시지 템플릿 생성 - 이름: {self.name}, 유형: {self.template_type}")
        else:
            logger.info(f"[MessageTemplate.save] 메시지 템플릿 수정 - 이름: {self.name}, 유형: {self.template_type}")
        
        super().save(*args, **kwargs)
    
    def render_content(self, **kwargs):
        """
        템플릿 내용 렌더링
        
        Args:
            **kwargs: 템플릿 변수들
        
        Returns:
            str: 렌더링된 메시지 내용
        """
        content = self.content
        for key, value in kwargs.items():
            content = content.replace(f"{{{key}}}", str(value))
        return content


class Message(models.Model):
    """
    메시지 모델
    
    실제 발송되는 메시지를 관리합니다.
    """
    
    MESSAGE_TYPES = [
        ('sms', 'SMS'),
        ('lms', 'LMS'),
        ('mms', 'MMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '발송대기'),
        ('sending', '발송중'),
        ('sent', '발송완료'),
        ('failed', '발송실패'),
        ('cancelled', '발송취소'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='템플릿'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, verbose_name='메시지 유형')
    recipient_phone = models.CharField(max_length=20, verbose_name='수신번호')
    content = models.TextField(verbose_name='메시지 내용')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='발송 상태'
    )
    sent_by = models.ForeignKey(
        CompanyUser,
        on_delete=models.CASCADE,
        verbose_name='발송자'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='발송 업체'
    )
    external_id = models.CharField(max_length=100, blank=True, verbose_name='외부 시스템 ID')
    error_message = models.TextField(blank=True, verbose_name='에러 메시지')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='발송일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '메시지'
        verbose_name_plural = '메시지'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message_type']),
            models.Index(fields=['status']),
            models.Index(fields=['recipient_phone']),
            models.Index(fields=['sent_by']),
            models.Index(fields=['company']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.recipient_phone} ({self.get_status_display()})"
    
    def clean(self):
        """메시지 생성 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 전화번호 형식 검증
        if not self.recipient_phone or len(self.recipient_phone) < 10:
            raise ValidationError("유효한 전화번호를 입력해주세요.")
        
        # 메시지 내용 길이 검증
        if len(self.content) > 2000:
            raise ValidationError("메시지 내용이 너무 깁니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[Message.save] 새 메시지 생성 - 수신번호: {self.recipient_phone}, 유형: {self.message_type}")
        else:
            logger.info(f"[Message.save] 메시지 수정 - 수신번호: {self.recipient_phone}, 상태: {self.status}")
        
        super().save(*args, **kwargs)
    
    def send(self):
        """
        메시지 발송
        
        실제 SMS API를 호출하여 메시지를 발송합니다.
        """
        try:
            # 외부 SMS API 호출 (실제 구현 시)
            # response = sms_api.send_message(self.recipient_phone, self.content)
            
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.save()
            
            logger.info(f"[Message.send] 메시지 발송 성공 - ID: {self.id}, 수신번호: {self.recipient_phone}")
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.save()
            
            logger.error(f"[Message.send] 메시지 발송 실패 - ID: {self.id}, 에러: {str(e)}")
    
    def cancel(self):
        """메시지 발송 취소"""
        if self.status in ['pending', 'sending']:
            self.status = 'cancelled'
            self.save()
            
            logger.info(f"[Message.cancel] 메시지 발송 취소 - ID: {self.id}")


class ScheduledMessage(models.Model):
    """
    예약 메시지 모델
    
    예약된 메시지 발송을 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        verbose_name='메시지'
    )
    scheduled_at = models.DateTimeField(verbose_name='예약 발송일시')
    is_sent = models.BooleanField(default=False, verbose_name='발송 여부')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='실제 발송일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='예약일시')
    
    class Meta:
        verbose_name = '예약 메시지'
        verbose_name_plural = '예약 메시지'
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['scheduled_at']),
            models.Index(fields=['is_sent']),
        ]
    
    def __str__(self):
        return f"예약 메시지 - {self.scheduled_at.strftime('%Y-%m-%d %H:%M')}"
    
    def clean(self):
        """예약 메시지 생성 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 예약 시간이 과거인지 검증
        if self.scheduled_at <= timezone.now():
            raise ValidationError("예약 시간은 현재 시간보다 이후여야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[ScheduledMessage.save] 새 예약 메시지 생성 - 예약시간: {self.scheduled_at}")
        else:
            logger.info(f"[ScheduledMessage.save] 예약 메시지 수정 - 예약시간: {self.scheduled_at}")
        
        super().save(*args, **kwargs)
    
    def send_scheduled_message(self):
        """
        예약된 메시지 발송
        
        예약 시간이 되면 실제 메시지를 발송합니다.
        """
        if not self.is_sent and self.scheduled_at <= timezone.now():
            self.message.send()
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save()
            
            logger.info(f"[ScheduledMessage.send_scheduled_message] 예약 메시지 발송 - ID: {self.id}")


class BulkMessage(models.Model):
    """
    일괄 메시지 모델
    
    여러 수신자에게 동시에 발송하는 메시지를 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.CASCADE,
        verbose_name='템플릿'
    )
    message_type = models.CharField(max_length=10, choices=Message.MESSAGE_TYPES, verbose_name='메시지 유형')
    recipients = models.JSONField(verbose_name='수신자 목록')
    content = models.TextField(verbose_name='메시지 내용')
    sent_by = models.ForeignKey(
        CompanyUser,
        on_delete=models.CASCADE,
        verbose_name='발송자'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='발송 업체'
    )
    total_count = models.IntegerField(default=0, verbose_name='총 발송 수')
    success_count = models.IntegerField(default=0, verbose_name='성공 수')
    failed_count = models.IntegerField(default=0, verbose_name='실패 수')
    is_completed = models.BooleanField(default=False, verbose_name='완료 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='완료일시')
    
    class Meta:
        verbose_name = '일괄 메시지'
        verbose_name_plural = '일괄 메시지'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message_type']),
            models.Index(fields=['sent_by']),
            models.Index(fields=['company']),
            models.Index(fields=['is_completed']),
        ]
    
    def __str__(self):
        return f"일괄 메시지 - {self.total_count}건 ({self.get_message_type_display()})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[BulkMessage.save] 새 일괄 메시지 생성 - 총 {self.total_count}건")
        else:
            logger.info(f"[BulkMessage.save] 일괄 메시지 수정 - 성공: {self.success_count}, 실패: {self.failed_count}")
        
        super().save(*args, **kwargs)
    
    def send_bulk_messages(self):
        """
        일괄 메시지 발송
        
        수신자 목록에 따라 개별 메시지를 생성하고 발송합니다.
        """
        for recipient in self.recipients:
            try:
                # 개별 메시지 생성
                message = Message.objects.create(
                    template=self.template,
                    message_type=self.message_type,
                    recipient_phone=recipient['phone'],
                    content=self.content,
                    sent_by=self.sent_by,
                    company=self.company
                )
                
                # 메시지 발송
                message.send()
                
                if message.status == 'sent':
                    self.success_count += 1
                else:
                    self.failed_count += 1
                
            except Exception as e:
                self.failed_count += 1
                logger.error(f"[BulkMessage.send_bulk_messages] 개별 메시지 발송 실패 - 수신자: {recipient.get('phone', 'Unknown')}, 에러: {str(e)}")
        
        # 일괄 발송 완료 처리
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
        
        logger.info(f"[BulkMessage.send_bulk_messages] 일괄 메시지 발송 완료 - 성공: {self.success_count}, 실패: {self.failed_count}")


class MessageLog(models.Model):
    """
    메시지 로그 모델
    
    메시지 발송 이력을 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='메시지'
    )
    action = models.CharField(max_length=50, verbose_name='액션')
    status = models.CharField(max_length=20, verbose_name='상태')
    details = models.JSONField(default=dict, verbose_name='상세 정보')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='로그일시')
    
    class Meta:
        verbose_name = '메시지 로그'
        verbose_name_plural = '메시지 로그'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['action']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.message.recipient_phone} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[MessageLog.save] 새 메시지 로그 생성 - 액션: {self.action}, 메시지: {self.message.id}")
        
        super().save(*args, **kwargs)

# companies/models.py
import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

logger = logging.getLogger('companies')


class Company(models.Model):
    """
    업체 정보를 관리하는 모델
    대리점과 판매점을 구분하여 관리
    """
    
    # 업체 타입 선택지
    TYPE_CHOICES = [
        ('agency', '대리점'),
        ('retail', '판매점'),
    ]
    
    # 기본 키는 UUID 사용
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="업체의 고유 식별자"
    )
    
    # 업체 기본 정보
    name = models.CharField(
        max_length=200,
        verbose_name="업체명",
        help_text="업체의 정식 명칭"
    )
    
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="업체 타입",
        help_text="대리점 또는 판매점 구분"
    )
    
    # 업체 운영 상태
    status = models.BooleanField(
        default=True,
        verbose_name="운영 상태",
        help_text="업체 운영 여부 (True: 운영중, False: 중단)"
    )
    
    # 하부 업체에 노출 여부
    visible = models.BooleanField(
        default=True,
        verbose_name="노출 여부",
        help_text="하부 업체에 노출할지 여부"
    )
    
    # 기본 택배사 설정
    default_courier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="기본 택배사",
        help_text="주문 처리 시 기본으로 사용할 택배사"
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
    
    class Meta:
        verbose_name = "업체"
        verbose_name_plural = "업체 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', 'status']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.name or not self.name.strip():
            raise ValidationError("업체명은 필수 입력 사항입니다.")
        
        # 중복 업체명 검사
        existing = Company.objects.filter(name=self.name).exclude(id=self.id)
        if existing.exists():
            raise ValidationError("동일한 업체명이 이미 존재합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 업체가 등록되었습니다: {self.name} ({self.type})")
            else:
                logger.info(f"업체 정보가 수정되었습니다: {self.name} (ID: {self.id})")
        
        except Exception as e:
            logger.error(f"업체 저장 중 오류 발생: {str(e)} - 업체: {self.name}")
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅 처리"""
        company_name = self.name
        company_id = self.id
        
        try:
            super().delete(*args, **kwargs)
            logger.info(f"업체가 삭제되었습니다: {company_name} (ID: {company_id})")
        
        except Exception as e:
            logger.error(f"업체 삭제 중 오류 발생: {str(e)} - 업체: {company_name}")
            raise
    
    def toggle_status(self):
        """업체 운영 상태를 토글하는 메서드"""
        try:
            old_status = self.status
            self.status = not self.status
            self.save()
            
            status_text = "운영중" if self.status else "중단"
            logger.info(f"업체 상태가 변경되었습니다: {self.name} - {status_text}")
            
            return True
        
        except Exception as e:
            logger.error(f"업체 상태 변경 중 오류 발생: {str(e)} - 업체: {self.name}")
            return False


class CompanyUser(models.Model):
    """
    업체별 사용자 계정 관리 모델
    각 업체의 관리자와 직원을 구분하여 관리
    """
    
    # 사용자 역할 선택지
    ROLE_CHOICES = [
        ('admin', '관리자'),
        ('staff', '직원'),
    ]
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # 업체 연결 (Foreign Key)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name="소속 업체",
        help_text="사용자가 소속된 업체"
    )
    
    # 사용자 기본 정보
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="사용자명",
        help_text="로그인에 사용할 사용자명"
    )
    
    password = models.CharField(
        max_length=255,
        verbose_name="비밀번호"
    )
    
    # 사용자 역할
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='staff',
        verbose_name="역할",
        help_text="사용자의 권한 레벨"
    )
    
    # 로그인 정보
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="마지막 로그인"
    )
    
    # 생성일시
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    class Meta:
        verbose_name = "업체 사용자"
        verbose_name_plural = "업체 사용자 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['company', 'role']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.company.name})"
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 업체 사용자가 생성되었습니다: {self.username} - {self.company.name}")
            else:
                logger.info(f"업체 사용자 정보가 수정되었습니다: {self.username}")
        
        except Exception as e:
            logger.error(f"업체 사용자 저장 중 오류 발생: {str(e)} - 사용자: {self.username}")
            raise


class CompanyMessage(models.Model):
    """
    업체에 발송되는 공지 메시지 관리 모델
    개별 발송과 일괄 발송을 구분하여 관리
    """
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # 메시지 내용
    message = models.TextField(
        verbose_name="메시지 내용",
        help_text="업체에 전송할 메시지 내용"
    )
    
    # 일괄 발송 여부
    is_bulk = models.BooleanField(
        default=False,
        verbose_name="일괄 발송 여부",
        help_text="모든 업체에 일괄 발송인지 개별 발송인지 구분"
    )
    
    # 발송자 (Django User와 연결)
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="발송자",
        help_text="메시지를 발송한 관리자"
    )
    
    # 수신 업체 (개별 발송 시)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages',
        verbose_name="수신 업체",
        help_text="메시지를 받을 업체 (일괄 발송 시에는 null)"
    )
    
    # 발송일시
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="발송일시"
    )
    
    class Meta:
        verbose_name = "업체 메시지"
        verbose_name_plural = "업체 메시지 목록"
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['company', 'sent_at']),
            models.Index(fields=['is_bulk', 'sent_at']),
        ]
    
    def __str__(self):
        if self.is_bulk:
            return f"일괄 메시지: {self.message[:50]}..."
        else:
            return f"{self.company.name}: {self.message[:50]}..."
    
    def clean(self):
        """모델 데이터 검증"""
        # 개별 발송인 경우 업체 지정 필수
        if not self.is_bulk and not self.company:
            raise ValidationError("개별 발송 시에는 수신 업체를 지정해야 합니다.")
        
        # 일괄 발송인 경우 업체 지정 불가
        if self.is_bulk and self.company:
            raise ValidationError("일괄 발송 시에는 수신 업체를 지정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if self.is_bulk:
                logger.info(f"일괄 메시지가 발송되었습니다: {self.message[:50]}...")
            else:
                logger.info(f"개별 메시지가 발송되었습니다: {self.company.name} - {self.message[:50]}...")
        
        except Exception as e:
            logger.error(f"업체 메시지 저장 중 오류 발생: {str(e)}")
            raise
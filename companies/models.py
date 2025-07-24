# companies/models.py
import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

logger = logging.getLogger('companies')


class Company(models.Model):
    """
    업체 정보를 관리하는 모델입니다.
    본사, 협력사, 판매점 등 다양한 유형의 업체를 계층적으로 관리합니다.
    """
    
    # 업체 타입 선택지: 본사(headquarters), 협력사(agency), 판매점(retail)
    TYPE_CHOICES = [
        ('headquarters', '본사'),
        ('agency', '협력사'),
        ('retail', '판매점'),
    ]
    
    # 업체의 고유 식별자 (UUID 사용)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="업체의 고유 식별자"
    )
    
    # 상위 업체 (계층 구조를 형성하는 핵심 필드)
    # 본사는 상위 업체가 없으며, 협력사는 본사를, 판매점은 협력사를 상위 업체로 가집니다.
    parent_company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL, # 상위 업체 삭제 시 하위 업체는 parent_company가 NULL이 됩니다.
        null=True,
        blank=True,
        related_name='child_companies', # 하위 업체에서 상위 업체를 역참조할 때 사용
        verbose_name="상위 업체",
        help_text="본사, 협력사, 판매점 간의 계층 관계를 정의합니다."
    )
    
    # 업체의 정식 명칭 (고유해야 함)
    name = models.CharField(
        max_length=200,
        unique=True, # 업체명은 고유해야 합니다.
        verbose_name="업체명",
        help_text="업체의 정식 명칭"
    )
    
    # 업체의 유형 (TYPE_CHOICES 중 하나)
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="업체 유형",
        help_text="본사, 협력사 또는 판매점 구분"
    )
    
    # 업체 운영 상태 (True: 운영중, False: 중단)
    status = models.BooleanField(
        default=True,
        verbose_name="운영 상태",
        help_text="업체 운영 여부 (True: 운영중, False: 중단)"
    )
    
    # 하부 업체에 노출 여부 (True: 노출, False: 비노출)
    visible = models.BooleanField(
        default=True,
        verbose_name="노출 여부",
        help_text="하부 업체에 노출할지 여부"
    )
    
    # 주문 처리 시 기본으로 사용할 택배사 (선택 사항)
    default_courier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="기본 택배사",
        help_text="주문 처리 시 기본으로 사용할 택배사"
    )
    
    # 생성일시 (자동 기록)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    # 수정일시 (자동 업데이트)
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "업체"
        verbose_name_plural = "업체 목록"
        ordering = ['-created_at'] # 최신 생성된 업체가 먼저 오도록 정렬
        indexes = [ # 쿼리 성능 향상을 위한 인덱스 설정
            models.Index(fields=['type', 'status']),
            models.Index(fields=['name']),
            models.Index(fields=['parent_company']),
        ]
    
    def __str__(self):
        """객체를 문자열로 표현할 때 사용합니다."""
        return f"{self.name} ({self.get_type_display()})"
    
    def clean(self):
        """
        모델 데이터의 유효성을 검증합니다.
        데이터베이스에 저장되기 전에 호출되어 비즈니스 규칙을 강제합니다.
        """
        # 1. 업체명 필수 입력 검증
        if not self.name or not self.name.strip():
            logger.warning(f"[Company.clean] 업체명 누락 시도. Name: '{self.name}'")
            raise ValidationError("업체명은 필수 입력 사항입니다.")
        
        # 2. 중복 업체명 검사 (고유성 제약 조건 강화)
        # 현재 인스턴스(self.id)를 제외하고 동일한 이름의 업체가 있는지 확인합니다.
        existing_companies = Company.objects.filter(name=self.name.strip())
        if self.pk: # 이미 존재하는 인스턴스인 경우 (수정)
            existing_companies = existing_companies.exclude(pk=self.pk)
        
        if existing_companies.exists():
            logger.warning(f"[Company.clean] 중복 업체명 생성/수정 시도. Name: '{self.name}'")
            raise ValidationError("동일한 업체명이 이미 존재합니다.")

        # 3. 본사-협력사-판매점 계층 관계 검증
        # 이 로직은 Company 모델의 핵심 비즈니스 규칙을 정의합니다.
        if self.type == 'headquarters':
            # 본사는 상위 업체를 가질 수 없습니다.
            if self.parent_company:
                logger.warning(f"[Company.clean] 본사({self.name})가 상위 업체({self.parent_company.name})를 가지려 시도.")
                raise ValidationError("본사는 상위 업체를 가질 수 없습니다.")
            # 본사는 시스템에 하나만 존재해야 합니다.
            # 현재 인스턴스를 제외하고 다른 본사가 이미 존재하는지 확인합니다.
            if Company.objects.filter(type='headquarters').exclude(pk=self.pk).exists():
                logger.warning(f"[Company.clean] 두 번째 본사({self.name}) 생성 시도.")
                raise ValidationError("본사는 시스템에 하나만 존재할 수 있습니다.")
        
        elif self.type == 'agency':
            # 협력사는 반드시 상위 본사를 지정해야 합니다.
            if not self.parent_company:
                logger.warning(f"[Company.clean] 협력사({self.name})가 상위 업체를 지정하지 않음.")
                raise ValidationError("협력사는 반드시 상위 본사를 지정해야 합니다.")
            # 협력사의 상위 업체는 반드시 본사여야 합니다.
            if self.parent_company.type != 'headquarters':
                logger.warning(f"[Company.clean] 협력사({self.name})의 상위 업체({self.parent_company.name})가 본사가 아님.")
                raise ValidationError("협력사의 상위 업체는 반드시 본사여야 합니다.")
        
        elif self.type == 'retail':
            # 판매점은 반드시 상위 협력사를 지정해야 합니다.
            if not self.parent_company:
                logger.warning(f"[Company.clean] 판매점({self.name})이 상위 업체를 지정하지 않음.")
                raise ValidationError("판매점은 반드시 상위 협력사를 지정해야 합니다.")
            # 판매점의 상위 업체는 반드시 협력사여야 합니다.
            if self.parent_company.type != 'agency':
                logger.warning(f"[Company.clean] 판매점({self.name})의 상위 업체({self.parent_company.name})가 협력사가 아님.")
                raise ValidationError("판매점의 상위 업체는 반드시 협력사여야 합니다.")
        
        # 기타 유효성 검증 로직 추가 가능

    def save(self, *args, **kwargs):
        """
        모델 인스턴스를 데이터베이스에 저장합니다.
        저장 전 `clean()` 메서드를 호출하여 유효성을 검증하고, 저장 과정을 로깅합니다.
        """
        is_new_instance = self.pk is None # 새로운 인스턴스인지 여부 판단
        
        try:
            # 데이터베이스 저장 전 모델의 유효성 검증을 수행합니다.
            # 이 과정에서 ValidationError가 발생하면 저장이 중단됩니다.
            self.full_clean() # clean() 메서드와 필드 유효성 검증을 모두 포함

            # 실제 데이터베이스 저장 작업을 수행합니다.
            super().save(*args, **kwargs)
            
            # 저장 작업 성공 후 로깅
            if is_new_instance:
                logger.info(f"[Company.save] 새로운 업체가 성공적으로 등록되었습니다. Name: '{self.name}', Type: '{self.type}', ID: {self.id}")
            else:
                logger.info(f"[Company.save] 업체 정보가 성공적으로 수정되었습니다. Name: '{self.name}', ID: {self.id}")
        
        except ValidationError as e:
            # clean() 또는 필드 유효성 검증에서 발생한 오류 로깅
            logger.error(f"[Company.save] 업체 저장 실패 - 유효성 검증 오류. Name: '{self.name}', Errors: {e.message_dict}", exc_info=True)
            raise # 호출자에게 ValidationError를 다시 발생시켜 처리하도록 합니다.
        except Exception as e:
            # 예상치 못한 다른 오류 발생 시 로깅
            logger.critical(f"[Company.save] 업체 저장 중 치명적인 오류 발생. Name: '{self.name}', Error: {str(e)}", exc_info=True)
            raise # 치명적인 오류는 다시 발생시켜 시스템 관리자에게 알립니다.
    
    def delete(self, *args, **kwargs):
        """
        모델 인스턴스를 데이터베이스에서 삭제합니다.
        삭제 과정을 로깅하고, 예외 발생 시 처리합니다.
        """
        company_name_to_log = self.name # 삭제 전 업체명 기록
        company_id_to_log = self.id     # 삭제 전 업체 ID 기록
        
        try:
            # 실제 데이터베이스 삭제 작업을 수행합니다.
            super().delete(*args, **kwargs)
            logger.info(f"[Company.delete] 업체가 성공적으로 삭제되었습니다. Name: '{company_name_to_log}', ID: {company_id_to_log}")
        
        except Exception as e:
            # 삭제 중 오류 발생 시 로깅
            logger.error(f"[Company.delete] 업체 삭제 중 오류 발생. Name: '{company_name_to_log}', ID: {company_id_to_log}, Error: {str(e)}", exc_info=True)
            raise # 호출자에게 예외를 다시 발생시켜 처리하도록 합니다.
    
    def toggle_status(self):
        """
        업체의 운영 상태(status)를 토글(True <-> False)하고 저장합니다.
        상태 변경 과정을 로깅하고 성공 여부를 반환합니다.
        """
        initial_status = self.status # 변경 전 상태 기록
        
        try:
            self.status = not self.status # 상태 변경
            self.save() # 변경된 상태 저장 (save 메서드 내에서 로깅 처리됨)
            
            current_status_text = "운영중" if self.status else "중단"
            logger.info(f"[Company.toggle_status] 업체 상태가 성공적으로 변경되었습니다. Name: '{self.name}', 이전 상태: {initial_status} -> 현재 상태: {current_status_text}")
            
            return True # 상태 변경 성공
        
        except Exception as e:
            # 상태 변경 중 오류 발생 시 로깅
            logger.error(f"[Company.toggle_status] 업체 상태 변경 중 오류 발생. Name: '{self.name}', Error: {str(e)}", exc_info=True)
            return False # 상태 변경 실패


class CompanyUser(models.Model):
    """
    업체별 사용자 계정을 관리하는 모델입니다.
    각 업체에 소속된 관리자와 직원을 구분하여 관리합니다.
    """
    
    # 사용자 역할 선택지: 관리자(admin), 직원(staff)
    ROLE_CHOICES = [
        ('admin', '관리자'),
        ('staff', '직원'),
    ]
    
    # 사용자 고유 식별자 (UUID 사용)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # 사용자가 소속된 업체 (Company 모델 참조)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE, # 소속 업체 삭제 시 사용자도 함께 삭제
        related_name='users', # Company 객체에서 해당 업체 사용자들을 역참조할 때 사용
        verbose_name="소속 업체",
        help_text="사용자가 소속된 업체"
    )
    
    # 로그인에 사용할 사용자명 (고유해야 함)
    username = models.CharField(
        max_length=150,
        unique=True, # 사용자명은 고유해야 합니다.
        verbose_name="사용자명",
        help_text="로그인에 사용할 사용자명"
    )
    
    # 사용자 비밀번호 (실제 운영 환경에서는 반드시 해시화하여 저장해야 합니다.)
    password = models.CharField(
        max_length=255,
        verbose_name="비밀번호"
    )
    
    # 사용자의 권한 레벨 (ROLE_CHOICES 중 하나)
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='staff',
        verbose_name="역할",
        help_text="사용자의 권한 레벨"
    )
    
    # 마지막 로그인 일시 (선택 사항)
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="마지막 로그인"
    )
    
    # 생성일시 (자동 기록)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    class Meta:
        verbose_name = "업체 사용자"
        verbose_name_plural = "업체 사용자 목록"
        ordering = ['-created_at'] # 최신 생성된 사용자가 먼저 오도록 정렬
        indexes = [ # 쿼리 성능 향상을 위한 인덱스 설정
            models.Index(fields=['username']),
            models.Index(fields=['company', 'role']),
        ]
    
    def __str__(self):
        """객체를 문자열로 표현할 때 사용합니다."""
        return f"{self.username} ({self.company.name})"
    
    def save(self, *args, **kwargs):
        """
        모델 인스턴스를 데이터베이스에 저장합니다.
        저장 과정을 로깅하고, 예외 발생 시 처리합니다.
        """
        is_new_instance = self.pk is None # 새로운 인스턴스인지 여부 판단
        
        try:
            # 실제 데이터베이스 저장 작업을 수행합니다.
            super().save(*args, **kwargs)
            
            # 저장 작업 성공 후 로깅
            if is_new_instance:
                logger.info(f"[CompanyUser.save] 새로운 업체 사용자가 성공적으로 생성되었습니다. Username: '{self.username}', Company: '{self.company.name}', Role: '{self.role}', ID: {self.id}")
            else:
                logger.info(f"[CompanyUser.save] 업체 사용자 정보가 성공적으로 수정되었습니다. Username: '{self.username}', Company: '{self.company.name}', ID: {self.id}")
        
        except Exception as e:
            # 예상치 못한 오류 발생 시 로깅
            logger.error(f"[CompanyUser.save] 업체 사용자 저장 중 오류 발생. Username: '{self.username}', Error: {str(e)}", exc_info=True)
            raise # 호출자에게 예외를 다시 발생시켜 처리하도록 합니다.


class CompanyMessage(models.Model):
    """
    업체에 발송되는 공지 메시지를 관리하는 모델입니다.
    개별 발송과 일괄 발송을 구분하여 관리합니다.
    """
    
    # 메시지 고유 식별자 (UUID 사용)
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # 메시지 내용 (텍스트 필드)
    message = models.TextField(
        verbose_name="메시지 내용",
        help_text="업체에 전송할 메시지 내용"
    )
    
    # 일괄 발송 여부 (True: 모든 업체에 발송, False: 특정 업체에 발송)
    is_bulk = models.BooleanField(
        default=False,
        verbose_name="일괄 발송 여부",
        help_text="모든 업체에 일괄 발송인지 개별 발송인지 구분"
    )
    
    # 메시지를 발송한 관리자 (Django의 기본 User 모델 참조)
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # 발송자 삭제 시 NULL로 설정
        null=True,
        blank=True,
        verbose_name="발송자",
        help_text="메시지를 발송한 관리자"
    )
    
    # 메시지를 받을 업체 (Company 모델 참조, 일괄 발송 시에는 NULL)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE, # 수신 업체 삭제 시 메시지도 함께 삭제
        null=True,
        blank=True,
        related_name='messages', # Company 객체에서 해당 업체 메시지들을 역참조할 때 사용
        verbose_name="수신 업체",
        help_text="메시지를 받을 업체 (일괄 발송 시에는 null)"
    )
    
    # 메시지 발송일시 (자동 기록)
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="발송일시"
    )
    
    class Meta:
        verbose_name = "업체 메시지"
        verbose_name_plural = "업체 메시지 목록"
        ordering = ['-sent_at'] # 최신 발송 메시지가 먼저 오도록 정렬
        indexes = [ # 쿼리 성능 향상을 위한 인덱스 설정
            models.Index(fields=['company', 'sent_at']),
            models.Index(fields=['is_bulk', 'sent_at']),
        ]
    
    def __str__(self):
        """객체를 문자열로 표현할 때 사용합니다."""
        if self.is_bulk:
            return f"일괄 메시지: {self.message[:50]}..."
        else:
            return f"{self.company.name}: {self.message[:50]}..."
    
    def clean(self):
        """
        모델 데이터의 유효성을 검증합니다.
        개별 발송과 일괄 발송 규칙을 강제합니다.
        """
        # 개별 발송인 경우 수신 업체 지정 필수
        if not self.is_bulk and not self.company:
            logger.warning(f"[CompanyMessage.clean] 개별 메시지 발송 시 수신 업체 누락 시도. Message: '{self.message[:50]}...'")
            raise ValidationError("개별 발송 시에는 수신 업체를 지정해야 합니다.")
        
        # 일괄 발송인 경우 수신 업체 지정 불가
        if self.is_bulk and self.company:
            logger.warning(f"[CompanyMessage.clean] 일괄 메시지 발송 시 수신 업체 지정 시도. Message: '{self.message[:50]}...', Company: '{self.company.name}'")
            raise ValidationError("일괄 발송 시에는 수신 업체를 지정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """
        모델 인스턴스를 데이터베이스에 저장합니다.
        저장 전 `clean()` 메서드를 호출하여 유효성을 검증하고, 저장 과정을 로깅합니다.
        """
        try:
            # 데이터베이스 저장 전 모델의 유효성 검증을 수행합니다.
            self.full_clean() # clean() 메서드와 필드 유효성 검증을 모두 포함

            # 실제 데이터베이스 저장 작업을 수행합니다.
            super().save(*args, **kwargs)
            
            # 저장 작업 성공 후 로깅
            if self.is_bulk:
                logger.info(f"[CompanyMessage.save] 일괄 메시지가 성공적으로 발송되었습니다. Message: '{self.message[:50]}...', ID: {self.id}")
            else:
                logger.info(f"[CompanyMessage.save] 개별 메시지가 성공적으로 발송되었습니다. Company: '{self.company.name}', Message: '{self.message[:50]}...', ID: {self.id}")
        
        except ValidationError as e:
            # clean() 또는 필드 유효성 검증에서 발생한 오류 로깅
            logger.error(f"[CompanyMessage.save] 메시지 저장 실패 - 유효성 검증 오류. Message: '{self.message[:50]}...', Errors: {e.message_dict}", exc_info=True)
            raise # 호출자에게 ValidationError를 다시 발생시켜 처리하도록 합니다.
        except Exception as e:
            # 예상치 못한 다른 오류 발생 시 로깅
            logger.critical(f"[CompanyMessage.save] 메시지 저장 중 치명적인 오류 발생. Message: '{self.message[:50]}...', Error: {str(e)}", exc_info=True)
            raise # 치명적인 오류는 다시 발생시켜 시스템 관리자에게 알립니다.
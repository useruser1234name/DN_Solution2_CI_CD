"""
주문 관리 시스템 모델

이 모듈은 고객 주문 관리를 위한 모델들을 정의합니다.
주문 상태 관리, 송장 등록, 자동 메시지 발송 등을 포함합니다.
"""

import uuid
import logging
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from companies.models import Company
from policies.models import Policy
# Redis 의존성 제거됨 - 민감정보는 해시로 처리
import hashlib
from django.conf import settings

logger = logging.getLogger('orders')


class Order(models.Model):
    """
    주문 모델
    
    고객 주문을 관리하는 핵심 모델입니다.
    주문 상태 관리, 송장 등록, 자동 메시지 발송 등을 포함합니다.
    """
    
    STATUS_CHOICES = [
        ('pending', '접수대기'),
        ('approved', '승인됨'),
        ('processing', '개통 준비중'),
        ('shipped', '개통중'),
        ('completed', '개통완료'),
        ('final_approved', '승인(완료)'),  # 정산 생성 트리거
        ('cancelled', '개통취소'),
        # TelecomOrder 상태 통합
        ('received', '접수'),
        ('activation_request', '개통 요청'),
        ('activating', '개통중'),
        ('activation_complete', '개통 완료'),
        ('rejected', '반려'),
    ]
    
    # 가입 유형 선택지 (TelecomOrder에서 통합)
    SUBSCRIPTION_TYPE_CHOICES = [
        ('MNP', '번호이동'),
        ('device_change', '기기변경'),
        ('new', '신규가입'),
    ]
    
    # 고객 유형 선택지 (TelecomOrder에서 통합)
    CUSTOMER_TYPE_CHOICES = [
        ('adult', '성인일반'),
        ('corporate', '법인'),
        ('foreigner', '외국인'),
        ('minor', '미성년자'),
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
    # 민감정보 필드들 - 승인 전까지 Redis에 임시 저장
    customer_name = models.CharField(max_length=100, verbose_name='고객명')
    customer_phone = models.CharField(max_length=20, verbose_name='고객 연락처')
    customer_email = models.EmailField(blank=True, verbose_name='고객 이메일')
    customer_address = models.TextField(verbose_name='배송 주소')
    
    # 민감정보 처리 관련 필드 (Redis 의존성 제거)
    is_sensitive_data_encrypted = models.BooleanField(
        default=False,
        verbose_name='민감정보 암호화 완료',
        help_text='민감정보가 암호화되어 저장되었는지 여부'
    )
    
    # ========== TelecomOrder 통합 필드들 ==========
    # 주문 번호 (자동 생성)
    order_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="주문번호",
        help_text="자동 생성된 주문번호"
    )
    
    # 통신사 정보
    carrier = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="통신사",
        help_text="정책에서 자동 입력"
    )
    
    # 참조 URL (정책 외부 URL 스냅샷)
    reference_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='참조 URL',
        help_text='정책의 외부 URL 스냅샷'
    )
    
    # 가입 유형
    subscription_type = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TYPE_CHOICES,
        blank=True,
        verbose_name="가입유형"
    )
    
    # 고객 유형
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        blank=True,
        verbose_name="고객유형"
    )
    
    # 판매점명 스냅샷
    retailer_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='판매점명 스냅샷'
    )
    
    # 이전 통신사
    previous_carrier = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='이전 통신사'
    )
    
    # 접수일자 (기존 created_at과 구분)
    received_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="접수일자",
        help_text="주문 접수 일시"
    )
    
    # 개통일자
    activation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="개통일자",
        help_text="실제 개통 완료 일시"
    )
    
    # 개통 번호(마스킹 표시용)
    activation_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='개통번호(마스킹)'
    )

    # 주문 데이터 (JSON 형태로 저장)
    order_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="주문 데이터",
        help_text="주문서 양식에서 제출된 모든 데이터"
    )
    
    # 요금/약정 및 단말/식별자 정보
    plan_name = models.CharField(max_length=200, blank=True, verbose_name='요금상품명')
    contract_period_selected = models.CharField(max_length=10, blank=True, verbose_name='약정기간(선택)')
    device_model = models.CharField(max_length=200, blank=True, verbose_name='단말기 모델')
    device_serial = models.CharField(max_length=100, blank=True, verbose_name='단말기 일련번호')
    imei = models.CharField(max_length=50, blank=True, verbose_name='IMEI')
    imei2 = models.CharField(max_length=50, blank=True, verbose_name='IMEI2')
    eid = models.CharField(max_length=50, blank=True, verbose_name='EID')
    usim_serial = models.CharField(max_length=50, blank=True, verbose_name='유심일련번호')
    
    # 납부/결제 정보 (평문 저장 금지: 마스킹본만 저장)
    payment_method = models.CharField(max_length=20, blank=True, verbose_name='납부방법', help_text='account|card')
    bank_name = models.CharField(max_length=100, blank=True, verbose_name='은행/카드사명')
    account_holder = models.CharField(max_length=100, blank=True, verbose_name='예금주/카드주')
    account_number_masked = models.CharField(max_length=100, blank=True, verbose_name='계좌번호(마스킹)')
    card_brand = models.CharField(max_length=50, blank=True, verbose_name='카드 브랜드')
    card_number_masked = models.CharField(max_length=100, blank=True, verbose_name='카드번호(마스킹)')
    card_exp_mmyy = models.CharField(max_length=10, blank=True, verbose_name='카드 유효기간(MMYY)')
    
    # 1차 ID (판매점 코드)
    first_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="1차 ID",
        help_text="주문을 접수한 판매점 코드"
    )
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
        is_new = self._state.adding  # UUID 필드 때문에 pk 체크 대신 _state.adding 사용
        self.full_clean()
        
        # 주문번호 자동 생성 (TelecomOrder 통합) - 중복 방지
        if is_new and not self.order_number:
            from django.utils import timezone
            import time
            
            # 중복되지 않는 주문번호 생성
            max_attempts = 10
            for attempt in range(max_attempts):
                if self.carrier:
                    prefix = self.carrier[:2].upper()
                else:
                    prefix = 'ORD'
                
                # 더 정밀한 타임스탬프 + 랜덤 접미사
                timestamp = timezone.now().strftime('%y%m%d%H%M%S')  # 초 단위까지 포함
                random_suffix = uuid.uuid4().hex[:6].upper()  # 6자리로 증가
                order_number = f"{prefix}-{timestamp}-{random_suffix}"
                
                # 중복 확인
                if not Order.objects.filter(order_number=order_number).exists():
                    self.order_number = order_number
                    break
                
                # 중복된 경우 잠시 대기 후 재시도
                time.sleep(0.001)  # 1ms 대기
            
            # 최대 시도 횟수 초과 시 UUID 사용
            if not self.order_number:
                self.order_number = f"{prefix}-{str(uuid.uuid4())[:8].upper()}"
                logger.warning(f"주문번호 생성 최대 시도 횟수 초과, UUID 사용: {self.order_number}")
        
        # 접수일자 자동 설정 (오늘 날짜)
        if is_new and not self.received_date:
            from django.utils import timezone
            self.received_date = timezone.now()
        
        # 1차 ID 자동 설정 (판매점 코드)
        if is_new and not self.first_id and self.company:
            self.first_id = self.company.code
        
        # 통신사 정보 자동 설정 (정책에서)
        if is_new and not self.carrier and self.policy:
            self.carrier = self.policy.carrier
        
        # 가입유형 자동 설정 (정책에서)
        if is_new and not self.subscription_type and self.policy:
            self.subscription_type = getattr(self.policy, 'subscription_type', 'new')
        
        # 정책 참조 URL 스냅샷
        if is_new and not self.reference_url and self.policy and getattr(self.policy, 'external_url', None):
            self.reference_url = self.policy.external_url
        
        # 약정기간 선택값 기본 설정(정책 기반)
        if is_new and not self.contract_period_selected and self.policy:
            self.contract_period_selected = getattr(self.policy, 'contract_period', '')
        
        # 판매점명 스냅샷
        if is_new and not self.retailer_name and self.company:
            try:
                self.retailer_name = self.company.name
            except Exception:
                self.retailer_name = ''
        
        # 개통번호 마스킹 기본값
        if is_new and not self.activation_phone and self.customer_phone:
            self.activation_phone = self._mask_phone(self.customer_phone)
        
        # 민감정보 처리 (로컬 암호화)
        if is_new and not self.is_sensitive_data_encrypted:
            # 민감정보를 로컬에서 암호화
            self._encrypt_sensitive_data()
        
        # 로깅 시 민감정보 마스킹
        masked_name = self._mask_customer_name()
        if is_new:
            logger.info(f"[Order.save] 새 주문 생성 - 고객: {masked_name}, 주문번호: {self.order_number}, 금액: {self.total_amount}")
        else:
            logger.info(f"[Order.save] 주문 수정 - 고객: {masked_name}, 주문번호: {self.order_number}")
        
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
                # 협력사 주문: 협력사 리베이트 금액
                self.rebate_amount = self.policy.rebate_agency
            elif self.company.type == 'retail':
                # 판매점 주문: 전체 리베이트 (협력사 + 판매점)
                self.rebate_amount = self.policy.rebate_agency + self.policy.rebate_retail
            else:
                # 본사 주문: 리베이트 없음
                self.rebate_amount = 0
            
            self.save()
            
            logger.info(f"리베이트 계산 완료: {self.customer_name} - {self.rebate_amount}원")
            return self.rebate_amount
        
        except Exception as e:
            logger.error(f"리베이트 계산 실패: {str(e)} - 주문: {self.customer_name}")
            return 0
    
    def update_status(self, new_status, user=None, reason=None):
        """주문 상태 업데이트 - 강화된 검증 및 로깅"""
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValidationError("유효하지 않은 주문 상태입니다.")
        
        # 권한 및 상태 전환 가능성 검증
        if not self.can_transition_to(new_status, user):
            if user:
                try:
                    from companies.models import CompanyUser
                    company_user = CompanyUser.objects.get(django_user=user)
                    user_info = f"{user.username} ({company_user.company.name})"
                except CompanyUser.DoesNotExist:
                    user_info = user.username
            else:
                user_info = "Unknown"
            
            raise ValidationError(
                f"사용자 {user_info}는 주문 상태를 '{self.get_status_display()}'에서 '{dict(self.STATUS_CHOICES)[new_status]}'로 변경할 권한이 없습니다."
            )
        
        old_status = self.status
        old_status_display = self.get_status_display()
        
        # 상태 변경 전 추가 검증
        self._validate_status_change(old_status, new_status, user)
        
        # 상태 변경
        self.status = new_status
        self.save()
        
        new_status_display = self.get_status_display()
        
        # 상세 로깅
        user_info = "System"
        if user:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=user)
                user_info = f"{user.username} ({company_user.company.name}, {company_user.get_role_display()})"
            except CompanyUser.DoesNotExist:
                user_info = user.username
        
        logger.info(
            f"[주문 상태 변경] {self.customer_name} - "
            f"{old_status_display} → {new_status_display} by {user_info}"
            f"{f' (사유: {reason})' if reason else ''}"
        )
        
        # 자동 메모 생성
        if user:
            memo_content = f"주문 상태가 '{old_status_display}'에서 '{new_status_display}'로 변경되었습니다."
            if reason:
                memo_content += f" 사유: {reason}"
            
            OrderMemo.objects.create(
                order=self,
                memo=memo_content,
                created_by=user
            )
        
        # 상태별 후처리
        self._handle_status_change_side_effects(old_status, new_status, user)
        
        # 상태 변경 이력 생성
        self._create_status_history(old_status, new_status, user, reason)
    
    def _validate_status_change(self, old_status, new_status, user):
        """상태 변경 전 추가 검증"""
        
        # 승인(completed) → 최종승인(final_approved) 시 추가 검증
        if old_status == 'completed' and new_status == 'final_approved':
            # 이미 정산이 생성되었는지 확인
            from settlements.models import Settlement
            if Settlement.objects.filter(order=self).exists():
                raise ValidationError("이미 정산이 생성된 주문입니다.")
        
        # 취소 시 추가 검증
        if new_status == 'cancelled':
            # 이미 정산이 진행된 경우 취소 불가
            from settlements.models import Settlement
            settlements = Settlement.objects.filter(order=self)
            if settlements.filter(status__in=['approved', 'paid']).exists():
                raise ValidationError("이미 정산이 진행된 주문은 취소할 수 없습니다.")
    
    def _handle_status_change_side_effects(self, old_status, new_status, user):
        """상태 변경 후 부가 처리"""
        
        # 취소 시 정산 취소 처리
        if new_status == 'cancelled':
            from settlements.models import Settlement
            settlements = Settlement.objects.filter(order=self, status='pending')
            for settlement in settlements:
                settlement.status = 'cancelled'
                settlement.save()
                logger.info(f"주문 취소로 인한 정산 취소: {settlement.id}")
        
        # 최종 승인 시 정산 생성 트리거 및 알림 로깅
        if new_status == 'final_approved':
            try:
                self._create_settlements()
                logger.info(f"주문 최종 승인으로 정산 생성 트리거 완료: {self.customer_name}")
            except Exception as e:
                logger.error(f"최종 승인 정산 생성 실패: {str(e)}")
    
    def _create_status_history(self, old_status, new_status, user, reason=None):
        """상태 변경 이력 생성"""
        try:
            # HTTP 요청 정보 추출 (가능한 경우)
            user_ip = None
            user_agent = ''
            
            # Django request context에서 IP 및 User-Agent 추출
            from django.core.context_processors import request
            import threading
            
            # 현재 요청 정보 가져오기 (가능한 경우)
            local_data = getattr(threading.current_thread(), 'request_data', None)
            if local_data:
                user_ip = local_data.get('ip')
                user_agent = local_data.get('user_agent', '')
            
            OrderHistory.objects.create(
                order=self,
                from_status=old_status,
                to_status=new_status,
                changed_by=user,
                reason=reason or '',
                user_ip=user_ip,
                user_agent=user_agent
            )
            
            logger.debug(
                f"상태 변경 이력 생성: {self.customer_name} - "
                f"{old_status} → {new_status}"
            )
            
        except Exception as e:
            logger.error(f"상태 변경 이력 생성 실패: {str(e)}")
    
    def can_transition_to(self, new_status, user=None):
        """상태 전환 가능 여부 확인 - 수정된 플로우 + 권한 검증"""
        valid_transitions = {
            'pending': ['approved', 'cancelled'],
            'approved': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['completed', 'cancelled'],
            'completed': ['final_approved', 'cancelled'],  # 수정: 개통완료 → 승인(완료)
            'final_approved': [],  # 최종 상태 - 더 이상 전환 불가
            'cancelled': [],
        }
        
        # 기본 상태 전환 가능성 확인
        if new_status not in valid_transitions.get(self.status, []):
            return False
        
        # 사용자 기반 권한 검증
        if user:
            return self._check_user_permission_for_status_change(user, new_status)
        
        return True
    
    def _check_user_permission_for_status_change(self, user, new_status):
        """사용자별 상태 변경 권한 검증"""
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=user)
            company = company_user.company
            role = company_user.role
        except CompanyUser.DoesNotExist:
            logger.warning(f"사용자 {user.username}의 회사 정보를 찾을 수 없습니다.")
            return False
        
        # 단계별 권한 제어
        if new_status == 'approved':
            # 승인: 본사 관리자만 가능
            return company.type == 'headquarters' and role == 'admin'
        
        elif new_status in ['processing', 'shipped', 'completed']:
            # 개통 진행: 본사 직원 이상
            return company.type == 'headquarters'
        
        elif new_status == 'final_approved':
            # 최종 승인: 본사 관리자만 가능
            return company.type == 'headquarters' and role == 'admin'
        
        elif new_status == 'cancelled':
            # 취소: 본사는 언제나, 다른 업체는 제한적
            if company.type == 'headquarters':
                return True
            elif company.type == 'agency':
                # 협력사: 자신의 주문만 취소 가능, pending/approved 단계에서만
                return (self.company == company and 
                       self.status in ['pending', 'approved'])
            elif company.type == 'retail':
                # 판매점: 자신의 주문만 취소 가능, pending 단계에서만
                return (self.company == company and 
                       self.status == 'pending')
        
        return True
    
    def _encrypt_sensitive_data(self):
        """민감정보를 해시로 처리"""
        try:
            # 민감정보 해시 생성 (실제로는 별도 테이블에 저장)
            if self.customer_name:
                customer_hash = hashlib.sha256(f"{self.customer_name}{self.id}".encode()).hexdigest()
                logger.debug(f"고객 정보 해시 생성: {customer_hash[:8]}...")
            
            self.is_sensitive_data_encrypted = True
            logger.info(f"민감정보가 처리되었습니다: {self.id}")
            
        except Exception as e:
            logger.error(f"민감정보 처리 실패: {str(e)}")
            self.is_sensitive_data_encrypted = False
    
    def _mask_phone(self, phone: str) -> str:
        """전화번호를 010-xxxx-xxxx 형식으로 마스킹"""
        try:
            digits = ''.join(ch for ch in phone if ch.isdigit())
            if len(digits) == 11:
                return f"{digits[:3]}-xxxx-{digits[-4:]}"
            if len(digits) == 10:
                return f"{digits[:3]}-xxx-{digits[-4:]}"
        except Exception:
            pass
        return phone
    
    def _process_sensitive_on_final_approve(self):
        """최종 승인 시 민감정보 정리: 평문 제거, 마스킹/해시 보관"""
        try:
            payload = self.order_data or {}
            rrn_plain = payload.pop('rrn', payload.pop('resident_registration_number', None))
            account_plain = payload.pop('account_number', None)
            card_plain = payload.pop('card_number', None)
            card_cvc_plain = payload.pop('card_cvc', None)
            
            # 표시용 마스킹 업데이트
            if account_plain:
                self.account_number_masked = self._mask_account_or_card(account_plain)
            if card_plain:
                self.card_number_masked = self._mask_account_or_card(card_plain)
            
            sensitive = getattr(self, 'sensitive_data', None)
            if not sensitive:
                sensitive = OrderSensitiveData(order=self)
            
            if rrn_plain:
                sensitive.rrn_masked = self._mask_rrn(rrn_plain)
                sensitive.rrn_hash = hashlib.sha256(rrn_plain.encode()).hexdigest()
            if account_plain:
                sensitive.account_number_hash = hashlib.sha256(account_plain.encode()).hexdigest()
            if card_plain:
                sensitive.card_number_hash = hashlib.sha256(card_plain.encode()).hexdigest()
            if card_cvc_plain:
                sensitive.card_cvc_hash = hashlib.sha256(card_cvc_plain.encode()).hexdigest()
            
            sensitive.save()
            
            self.order_data = payload
            self.is_sensitive_data_encrypted = True
            self.save(update_fields=['order_data', 'is_sensitive_data_encrypted', 'account_number_masked', 'card_number_masked'])
        except Exception as e:
            logger.error(f"최종 승인 민감정보 처리 실패: {str(e)}")
    
    def _mask_rrn(self, value: str) -> str:
        """주민등록번호 마스킹: xxxxx-x****** 형식"""
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) >= 13:
            return f"{digits[:5]}-x******"
        return "***************"
    
    def _mask_account_or_card(self, value: str) -> str:
        """계좌/카드번호 마스킹: ****-****-****-1234 형태"""
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) >= 4:
            return f"****-****-****-{digits[-4:]}"
        return "********"
    
    def _mask_customer_name(self):
        """고객명 마스킹"""
        if not self.customer_name or len(self.customer_name) < 2:
            return "***"
        
        if len(self.customer_name) == 2:
            return self.customer_name[0] + "*"
        else:
            return self.customer_name[0] + "*" * (len(self.customer_name) - 2) + self.customer_name[-1]
    
    def approve(self, user=None):
        """주문 승인 (본사만 가능) - 정산 생성하지 않음"""
        if self.status != 'pending':
            raise ValidationError("대기 중인 주문만 승인할 수 있습니다.")
        
        # 민감정보 처리 확인
        if not self.is_sensitive_data_encrypted:
            self._encrypt_sensitive_data()
        
        # 상태 변경 (정산 생성하지 않음)
        self.update_status('approved', user)
        
        logger.info(f"주문 승인 완료: {self.customer_name} - 정산은 최종 승인 시 생성됨")
    
    def final_approve(self, user=None):
        """최종 승인 (정산 생성 트리거)"""
        if self.status != 'completed':
            raise ValidationError("개통완료된 주문만 최종 승인할 수 있습니다.")
        
        # 개통일 자동 기입 및 민감정보 정리
        from django.utils import timezone
        self.activation_date = timezone.now()
        self.save(update_fields=['activation_date'])
        self._process_sensitive_on_final_approve()
        
        # 상태 변경
        self.update_status('final_approved', user)
        
        # 정산 자동 생성
        try:
            self._create_settlements()
            logger.info(f"주문 최종 승인 및 정산 생성 완료: {self.customer_name}")
        except Exception as e:
            logger.error(f"정산 생성 실패: {str(e)} - 주문: {self.customer_name}")
            raise
    
    def _create_settlements(self):
        """주문 승인 시 정산 자동 생성"""
        from settlements.models import Settlement
        
        # 이미 정산이 생성되었는지 확인
        if Settlement.objects.filter(order=self).exists():
            logger.info(f"이미 정산이 생성된 주문입니다: {self.customer_name}")
            return
        
        settlements = []
        
        try:
            with transaction.atomic():
                # 주문 업체의 계층 구조에 따라 정산 생성
                order_company = self.company
                
                if order_company.type == 'retail':
                    # 판매점 주문인 경우
                    # 1. 협력사에서 설정한 판매점 리베이트 조회
                    from policies.models import AgencyRebate, PolicyExposure
                    try:
                        # PolicyExposure를 통해 AgencyRebate 조회
                        policy_exposure = PolicyExposure.objects.get(
                            policy=self.policy,
                            agency=order_company.parent_company,
                            is_active=True
                        )
                        agency_rebate = AgencyRebate.objects.get(
                            policy_exposure=policy_exposure,
                            retail_company=order_company,
                            is_active=True
                        )
                        retail_rebate = agency_rebate.rebate_amount
                    except (PolicyExposure.DoesNotExist, AgencyRebate.DoesNotExist):
                        # 협력사가 설정하지 않은 경우 기본값 사용
                        retail_rebate = self.rebate_amount * Decimal('0.7')  # 70%
                    
                    # 판매점 정산 생성
                    retail_settlement = Settlement.objects.create(
                        order=self,
                        company=order_company,
                        rebate_amount=retail_rebate,
                        status='approved'  # 주문 승인 시 자동 승인
                    )
                    settlements.append(retail_settlement)
                    
                    # 협력사 정산 생성 (본사 리베이트에서 판매점 리베이트를 뺀 금액)
                    if order_company.parent_company:
                        agency_rebate_amount = self.rebate_amount - retail_rebate
                        if agency_rebate_amount > 0:
                            agency_settlement = Settlement.objects.create(
                                order=self,
                                company=order_company.parent_company,
                                rebate_amount=agency_rebate_amount,
                                status='approved'  # 주문 승인 시 자동 승인
                            )
                            settlements.append(agency_settlement)
                
                elif order_company.type == 'agency':
                    # 협력사 직접 주문인 경우
                    agency_settlement = Settlement.objects.create(
                        order=self,
                        company=order_company,
                        rebate_amount=self.rebate_amount,
                        status='approved'  # 주문 승인 시 자동 승인
                    )
                    settlements.append(agency_settlement)
                
                elif order_company.type == 'headquarters':
                    # 본사 직접 주문인 경우 (정산 없음)
                    logger.info(f"본사 직접 주문으로 정산 생성하지 않음: {self.customer_name}")
                
                logger.info(f"주문 {self.id}에 대한 정산 {len(settlements)}건 생성 완료")
                
        except Exception as e:
            logger.error(f"정산 생성 실패: {str(e)}")
            raise


class OrderSensitiveData(models.Model):
    """
    주문 민감정보 모델
    
    해시화된 민감정보를 별도로 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='sensitive_data',
        verbose_name='주문'
    )
    
    # 해시화된 민감정보
    customer_name_hash = models.CharField(max_length=64, verbose_name='고객명 해시')
    customer_phone_hash = models.CharField(max_length=64, verbose_name='전화번호 해시')
    customer_email_hash = models.CharField(max_length=64, blank=True, verbose_name='이메일 해시')
    customer_address_hash = models.CharField(max_length=64, verbose_name='주소 해시')
    rrn_hash = models.CharField(max_length=64, blank=True, verbose_name='주민등록번호 해시')
    account_number_hash = models.CharField(max_length=64, blank=True, verbose_name='계좌번호 해시')
    card_number_hash = models.CharField(max_length=64, blank=True, verbose_name='카드번호 해시')
    card_cvc_hash = models.CharField(max_length=64, blank=True, verbose_name='카드 CVC 해시')
    
    # 마스킹된 표시용 데이터
    customer_name_masked = models.CharField(max_length=100, verbose_name='고객명 (마스킹)')
    customer_phone_masked = models.CharField(max_length=20, verbose_name='전화번호 (마스킹)')
    customer_address_masked = models.TextField(verbose_name='주소 (마스킹)')
    rrn_masked = models.CharField(max_length=20, blank=True, verbose_name='주민등록번호(마스킹)')
    
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name='처리일시')
    
    class Meta:
        verbose_name = '주문 민감정보'
        verbose_name_plural = '주문 민감정보'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['processed_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_name_masked} - 민감정보 (처리됨)"


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


class OrderHistory(models.Model):
    """
    주문 상태 변경 이력 모델
    
    주문의 모든 상태 변경을 추적하고 기록합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='주문'
    )
    from_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        verbose_name='이전 상태'
    )
    to_status = models.CharField(
        max_length=20,
        choices=Order.STATUS_CHOICES,
        verbose_name='변경 상태'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='변경자'
    )
    reason = models.TextField(
        blank=True,
        verbose_name='변경 사유'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='변경일시'
    )
    
    # 시스템 정보
    user_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='사용자 IP'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='사용자 에이전트'
    )
    
    class Meta:
        verbose_name = '주문 상태 이력'
        verbose_name_plural = '주문 상태 이력'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['order', 'changed_at']),
            models.Index(fields=['to_status']),
            models.Index(fields=['changed_by']),
        ]
    
    def __str__(self):
        return f"{self.order.customer_name} - {self.get_from_status_display()} → {self.get_to_status_display()}"

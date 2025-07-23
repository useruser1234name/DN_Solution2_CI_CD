# orders/models.py
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
    고객 주문서 관리 모델
    온라인 가입 양식 및 주문 처리 상태 관리
    """
    
    # 주문 상태 선택지
    STATUS_CHOICES = [
        ('reserved', '예약'),
        ('received', '접수'),
        ('processing', '처리중'),
        ('completed', '완료'),
        ('cancelled', '취소'),
    ]
    
    # 신청 타입 선택지
    APPLY_TYPE_CHOICES = [
        ('new', '신규가입'),
        ('change', '기기변경'),
        ('transfer', '번호이동'),
        ('additional', '추가개통'),
    ]
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SK텔레콤'),
        ('kt', 'KT'),
        ('lgu', 'LG유플러스'),
        ('skt_mvno', 'SK텔레콤 알뜰폰'),
        ('kt_mvno', 'KT 알뜰폰'),
        ('lgu_mvno', 'LG유플러스 알뜰폰'),
    ]
    
    # 기본 키는 UUID 사용
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="주문서의 고유 식별자"
    )
    
    # 고객 기본 정보
    customer_name = models.CharField(
        max_length=100,
        verbose_name="고객명",
        help_text="신청 고객의 성명"
    )
    
    # 전화번호 검증을 위한 정규식 패턴
    phone_regex = RegexValidator(
        regex=r'^01([0|1|6|7|8|9])-?([0-9]{3,4})-?([0-9]{4})$',
        message="올바른 휴대폰 번호를 입력하세요. (예: 010-1234-5678)"
    )
    
    customer_phone = models.CharField(
        validators=[phone_regex],
        max_length=15,
        verbose_name="연락처",
        help_text="고객 휴대폰 번호"
    )
    
    customer_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="이메일",
        help_text="고객 이메일 주소 (선택사항)"
    )
    
    # 주문 상품 정보
    model_name = models.CharField(
        max_length=200,
        verbose_name="모델명",
        help_text="주문할 스마트기기 모델명"
    )
    
    carrier = models.CharField(
        max_length=20,
        choices=CARRIER_CHOICES,
        verbose_name="통신사",
        help_text="이용할 통신사"
    )
    
    # 신청 타입
    apply_type = models.CharField(
        max_length=20,
        choices=APPLY_TYPE_CHOICES,
        default='new',
        verbose_name="신청 타입",
        help_text="신청의 종류"
    )
    
    # 주문 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='reserved',
        verbose_name="처리 상태",
        help_text="주문서의 현재 처리 상태"
    )
    
    # 연결된 정책 (Foreign Key)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="적용 정책",
        help_text="이 주문에 적용된 정책"
    )
    
    # 연결된 업체 (Foreign Key)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="처리 업체",
        help_text="이 주문을 처리하는 업체"
    )
    
    # 주문 처리자
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders',
        verbose_name="접수자",
        help_text="주문을 접수한 사용자"
    )
    
    # 추가 정보
    memo = models.TextField(
        blank=True,
        null=True,
        verbose_name="메모",
        help_text="주문 관련 추가 메모"
    )
    
    # 배송 정보
    delivery_address = models.TextField(
        blank=True,
        null=True,
        verbose_name="배송 주소",
        help_text="기기 배송받을 주소"
    )
    
    # 시간 정보
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="접수일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "주문서"
        verbose_name_plural = "주문서 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['customer_name', 'customer_phone']),
            models.Index(fields=['model_name']),
            models.Index(fields=['carrier', 'apply_type']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.model_name} ({self.get_status_display()})"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.customer_name or not self.customer_name.strip():
            raise ValidationError("고객명은 필수 입력 사항입니다.")
        
        if not self.customer_phone or not self.customer_phone.strip():
            raise ValidationError("연락처는 필수 입력 사항입니다.")
        
        if not self.model_name or not self.model_name.strip():
            raise ValidationError("모델명은 필수 입력 사항입니다.")
        
        # 업체 상태 확인
        if self.company and not self.company.status:
            raise ValidationError("운영 중단된 업체로는 주문을 생성할 수 없습니다.")
        
        # 정책과 업체 매칭 확인
        if self.policy and self.company:
            policy_assignment = self.policy.assignments.filter(company=self.company).exists()
            if not policy_assignment:
                logger.warning(f"정책과 업체가 매칭되지 않는 주문 생성 시도: {self.policy.title} - {self.company.name}")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_instance = Order.objects.get(pk=self.pk)
                old_status = old_instance.status
            except Order.DoesNotExist:
                pass
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 주문서가 접수되었습니다: {self.customer_name} - {self.model_name} (업체: {self.company.name})")
            else:
                if old_status != self.status:
                    logger.info(f"주문서 상태 변경: {self.customer_name} - {old_status} → {self.status}")
                else:
                    logger.info(f"주문서 정보 수정: {self.customer_name} (ID: {self.id})")
        
        except Exception as e:
            logger.error(f"주문서 저장 중 오류 발생: {str(e)} - 고객: {self.customer_name}")
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅 처리"""
        customer_name = self.customer_name
        order_id = self.id
        
        try:
            super().delete(*args, **kwargs)
            logger.info(f"주문서가 삭제되었습니다: {customer_name} (ID: {order_id})")
        
        except Exception as e:
            logger.error(f"주문서 삭제 중 오류 발생: {str(e)} - 고객: {customer_name}")
            raise
    
    def update_status(self, new_status, user=None):
        """주문 상태를 업데이트하는 메서드"""
        try:
            old_status = self.status
            
            # 상태 변경이 유효한지 검증
            if not self._is_valid_status_transition(old_status, new_status):
                logger.warning(f"유효하지 않은 상태 변경 시도: {old_status} → {new_status} (주문: {self.customer_name})")
                return False
            
            self.status = new_status
            self.save()
            
            # 상태 변경 로그
            user_info = f" by {user.username}" if user else ""
            logger.info(f"주문 상태 변경 성공: {self.customer_name} - {old_status} → {new_status}{user_info}")
            
            return True
        
        except Exception as e:
            logger.error(f"주문 상태 변경 중 오류 발생: {str(e)} - 주문: {self.customer_name}")
            return False
    
    def _is_valid_status_transition(self, old_status, new_status):
        """상태 전환이 유효한지 검사"""
        # 기본적인 상태 전환 규칙
        valid_transitions = {
            'reserved': ['received', 'cancelled'],
            'received': ['processing', 'cancelled'],
            'processing': ['completed', 'cancelled'],
            'completed': [],  # 완료된 주문은 상태 변경 불가
            'cancelled': ['reserved'],  # 취소된 주문은 다시 예약으로만 가능
        }
        
        return new_status in valid_transitions.get(old_status, [])
    
    def get_memos(self):
        """연관된 메모 목록 반환"""
        try:
            return self.order_memos.all().order_by('-created_at')
        except Exception as e:
            logger.warning(f"주문 메모 조회 중 오류: {str(e)} - 주문: {self.customer_name}")
            return []
    
    def get_invoice(self):
        """연관된 송장 정보 반환"""
        try:
            return getattr(self, 'invoice', None)
        except Exception as e:
            logger.warning(f"주문 송장 조회 중 오류: {str(e)} - 주문: {self.customer_name}")
            return None
    
    def is_completed(self):
        """주문이 완료되었는지 확인"""
        return self.status == 'completed'
    
    def is_cancelled(self):
        """주문이 취소되었는지 확인"""
        return self.status == 'cancelled'
    
    def can_be_cancelled(self):
        """주문을 취소할 수 있는지 확인"""
        return self.status in ['reserved', 'received', 'processing']


class OrderMemo(models.Model):
    """
    주문서별 메모 관리 모델
    주문 처리 과정에서 발생하는 메모와 기록 관리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="메모의 고유 식별자"
    )
    
    # 주문서 연결 (Foreign Key)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_memos',
        verbose_name="연관 주문서",
        help_text="메모가 속한 주문서"
    )
    
    # 메모 내용
    memo = models.TextField(
        verbose_name="메모 내용",
        help_text="주문 처리 관련 메모나 기록"
    )
    
    # 메모 작성자
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="작성자",
        help_text="메모를 작성한 사용자"
    )
    
    # 메모 작성일시
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="작성일시"
    )
    
    class Meta:
        verbose_name = "주문 메모"
        verbose_name_plural = "주문 메모 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        memo_preview = self.memo[:50] + '...' if len(self.memo) > 50 else self.memo
        return f"{self.order.customer_name} - {memo_preview}"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.memo or not self.memo.strip():
            raise ValidationError("메모 내용은 필수 입력 사항입니다.")
        
        if len(self.memo.strip()) > 2000:
            raise ValidationError("메모는 2000자를 초과할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                author = self.created_by.username if self.created_by else "시스템"
                logger.info(f"주문 메모 추가: {self.order.customer_name} - 작성자: {author}")
            else:
                logger.info(f"주문 메모 수정: {self.order.customer_name} (메모 ID: {self.id})")
        
        except Exception as e:
            logger.error(f"주문 메모 저장 중 오류 발생: {str(e)} - 주문: {self.order.customer_name}")
            raise


class Invoice(models.Model):
    """
    주문 완료 후 송장 정보 관리 모델
    배송 처리 및 송장 추적을 위한 정보 저장
    """
    
    # 택배사 선택지
    COURIER_CHOICES = [
        ('cj', 'CJ대한통운'),
        ('lotte', '롯데택배'),
        ('hanjin', '한진택배'),
        ('post', '우체국택배'),
        ('kdexp', '경동택배'),
        ('logen', '로젠택배'),
        ('daesin', '대신택배'),
        ('etc', '기타'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="송장의 고유 식별자"
    )
    
    # 주문서 연결 (One-to-One)
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name="연관 주문서",
        help_text="송장이 속한 주문서"
    )
    
    # 택배사 정보
    courier = models.CharField(
        max_length=20,
        choices=COURIER_CHOICES,
        verbose_name="택배사",
        help_text="배송을 담당하는 택배사"
    )
    
    # 송장 번호
    invoice_number = models.CharField(
        max_length=100,
        verbose_name="송장 번호",
        help_text="택배사 송장 추적 번호"
    )
    
    # 발송일시
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="발송일시"
    )
    
    # 배송 완료일시
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="배송 완료일시"
    )
    
    # 수취인 정보 (고객 정보와 다를 수 있음)
    recipient_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="수취인명",
        help_text="실제 택배를 받을 사람 (빈 값이면 고객명 사용)"
    )
    
    recipient_phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="수취인 연락처",
        help_text="실제 택배를 받을 사람의 연락처"
    )
    
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
        
        # 이미 완료된 주문인지 확인
        if self.order.status != 'completed':
            logger.warning(f"미완료 주문에 송장 등록 시도: {self.order.customer_name} (상태: {self.order.status})")
    
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
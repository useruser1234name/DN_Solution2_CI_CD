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
from policies.models import Policy, CommissionMatrix

logger = logging.getLogger(__name__)


class Settlement(models.Model):
    """
    정산 모델
    주문 완료 시 자동으로 생성되며 계층별 리베이트를 관리
    """
    
    STATUS_CHOICES = [
        ('pending', '정산 대기'),
        ('approved', '정산 승인'),
        ('paid', '입금 완료'),  # 기존
        ('unpaid', '미입금'),    # 새로 추가
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
    
    # 입금 관련 추가 필드
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='입금 방법',
        help_text='계좌이체, 현금, 카드 등'
    )
    
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='입금 참조번호',
        help_text='거래번호, 승인번호 등'
    )
    
    expected_payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='입금 예정일',
        help_text='입금이 예상되는 날짜'
    )
    
    # 리베이트 지급 예정일 (협력사/판매점별로 다를 수 있음)
    rebate_due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='리베이트 지급 예정일',
        help_text='협력사 또는 판매점별로 설정된 리베이트 지급 예정일'
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
        """저장 시 로깅 및 상태 이력 기록"""
        is_new = self.pk is None
        old_status = None
        
        # 기존 상태 가져오기 (수정 시)
        if not is_new:
            try:
                old_instance = Settlement.objects.get(pk=self.pk)
                old_status = old_instance.status
            except Settlement.DoesNotExist:
                pass
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"정산 생성: {self.company.name} - {self.rebate_amount:,}원")
                # 새 정산의 초기 상태 이력 기록
                self._create_status_history(None, self.status, None, '정산 생성')
                
                # 팩트 테이블에 데이터 생성
                self._create_commission_fact()
                
                # 데이터 웨어하우스 팩트 테이블 생성
                try:
                    CommissionFact.create_from_settlement(self)
                except Exception as e:
                    logger.warning(f"팩트 테이블 생성 실패: {str(e)}")
            else:
                # 상태 변경 시 이력 기록
                if old_status and old_status != self.status:
                    self._create_status_history(old_status, self.status, None, '상태 변경')
                logger.info(f"정산 수정: {self.company.name} - {self.status}")
        
        except Exception as e:
            logger.error(f"정산 저장 실패: {str(e)}")
            raise
    
    def _create_status_history(self, old_status, new_status, user, reason=''):
        """상태 변경 이력 생성"""
        try:
            SettlementStatusHistory.objects.create(
                settlement=self,
                from_status=old_status or 'pending',
                to_status=new_status,
                changed_by=user,
                reason=reason
            )
            
            logger.debug(
                f"정산 상태 이력 생성: {self.company.name} - "
                f"{old_status} → {new_status}"
            )
            
        except Exception as e:
            logger.error(f"정산 상태 이력 생성 실패: {str(e)}")
    
    def _create_commission_fact(self):
        """팩트 테이블에 정산 데이터 생성"""
        try:
            # 그레이드 보너스 계산
            grade_bonus = self._calculate_grade_bonus()
            
            # 주문에서 추가 정보 추출
            plan_range = self._extract_plan_range_from_order()
            contract_period = self._extract_contract_period_from_order()
            
            # 팩트 데이터 생성
            CommissionFact.objects.create(
                date_key=self.created_at.date(),
                company=self.company,
                policy=self.order.policy,
                order=self.order,
                carrier=self.order.policy.carrier if hasattr(self.order, 'policy') else 'unknown',
                plan_range=plan_range,
                contract_period=contract_period,
                base_commission=self.rebate_amount,
                grade_bonus=grade_bonus,
                total_commission=self.rebate_amount + grade_bonus,
                settlement_status=self.status,
                payment_status='pending',
                order_count_in_period=1,
                achieved_grade_level=self._get_current_grade_level(),
                batch_id=None  # 실시간 생성이므로 배치 ID 없음
            )
            
            logger.info(f"팩트 테이블 생성 완료: {self.company.name} - {self.rebate_amount:,}원")
            
        except Exception as e:
            logger.error(f"팩트 테이블 생성 실패: {str(e)} - 정산: {self.id}")
    
    def _calculate_grade_bonus(self):
        """그레이드 보너스 계산"""
        try:
            # 현재 활성화된 그레이드 추적 찾기
            from django.utils import timezone
            current_date = timezone.now().date()
            
            grade_tracking = CommissionGradeTracking.objects.filter(
                company=self.company,
                policy=self.order.policy,
                period_start__lte=current_date,
                period_end__gte=current_date,
                is_active=True
            ).first()
            
            if grade_tracking:
                return grade_tracking.bonus_per_order
            return Decimal('0')
            
        except Exception as e:
            logger.warning(f"그레이드 보너스 계산 실패: {str(e)}")
            return Decimal('0')
    
    def _extract_plan_range_from_order(self):
        """주문에서 요금제 범위 추출"""
        try:
            # 주문에서 요금제 정보 추출 (실제 필드명에 따라 조정 필요)
            if hasattr(self.order, 'plan_amount'):
                plan_amount = self.order.plan_amount
                # CommissionMatrix의 PLAN_RANGE_CHOICES 참조
                from policies.models import CommissionMatrix
                for range_value, _ in CommissionMatrix.PLAN_RANGE_CHOICES:
                    if plan_amount <= range_value:
                        return range_value
                # 가장 높은 범위 반환
                return CommissionMatrix.PLAN_RANGE_CHOICES[-1][0]
            return 50000  # 기본값
        except Exception:
            return 50000
    
    def _extract_contract_period_from_order(self):
        """주문에서 계약기간 추출"""
        try:
            if hasattr(self.order, 'contract_period'):
                return self.order.contract_period
            return 24  # 기본값
        except Exception:
            return 24
    
    def _get_current_grade_level(self):
        """현재 그레이드 레벨 조회"""
        try:
            from django.utils import timezone
            current_date = timezone.now().date()
            
            grade_tracking = CommissionGradeTracking.objects.filter(
                company=self.company,
                policy=self.order.policy,
                period_start__lte=current_date,
                period_end__gte=current_date,
                is_active=True
            ).first()
            
            if grade_tracking:
                return grade_tracking.achieved_grade_level
            return 0
            
        except Exception:
            return 0
    
    def approve(self, user):
        """정산 승인"""
        if self.status != 'pending':
            raise ValidationError("대기 중인 정산만 승인할 수 있습니다.")
        
        old_status = self.status
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        
        # 상태 이력 생성
        self._create_status_history(old_status, self.status, user, '정산 승인')
        
        # save()를 호출하지 않고 직접 데이터베이스 업데이트
        Settlement.objects.filter(pk=self.pk).update(
            status=self.status,
            approved_by=self.approved_by,
            approved_at=self.approved_at
        )
        
        # 팩트 테이블 업데이트
        try:
            CommissionFact.update_payment_status(self)
        except Exception as e:
            logger.warning(f"팩트 테이블 상태 업데이트 실패: {str(e)}")
        
        logger.info(f"정산 승인: {self.company.name} - {self.rebate_amount:,}원")
    
    def mark_as_paid(self, user=None, payment_method='', payment_reference=''):
        """입금 완료 처리"""
        if self.status not in ['approved', 'unpaid']:
            raise ValidationError("승인된 정산 또는 미입금 정산만 입금 처리할 수 있습니다.")
        
        old_status = self.status
        self.status = 'paid'
        self.paid_at = timezone.now()
        
        # 입금 정보 업데이트
        if payment_method:
            self.payment_method = payment_method
        if payment_reference:
            self.payment_reference = payment_reference
        
        # 입금 확인자 기록
        if user:
            self.notes = f"입금 확인자: {user.username}\n{self.notes}"
        
        # 상태 이력 생성
        reason = f'입금 확인'
        if payment_method:
            reason += f' ({payment_method})'
        if payment_reference:
            reason += f' - 참조: {payment_reference}'
        
        self._create_status_history(old_status, self.status, user, reason)
        
        # 직접 데이터베이스 업데이트
        Settlement.objects.filter(pk=self.pk).update(
            status=self.status,
            paid_at=self.paid_at,
            payment_method=self.payment_method,
            payment_reference=self.payment_reference,
            notes=self.notes
        )
        
        # 팩트 테이블 업데이트
        try:
            CommissionFact.update_payment_status(self)
        except Exception as e:
            logger.warning(f"팩트 테이블 상태 업데이트 실패: {str(e)}")
        
        logger.info(f"정산 입금 완료: {self.company.name} - {self.rebate_amount:,}원 ({old_status} → paid)")
    
    def mark_as_unpaid(self, reason='', user=None):
        """미입금 처리"""
        if self.status != 'approved':
            raise ValidationError("승인된 정산만 미입금 처리할 수 있습니다.")
        
        old_status = self.status
        self.status = 'unpaid'
        if reason:
            self.notes = f"미입금 사유: {reason}\n{self.notes}"
        
        # 상태 이력 생성
        self._create_status_history(old_status, self.status, user, f'믴입금 처리{f" ({reason})" if reason else ""}')
        
        # 직접 데이터베이스 업데이트
        Settlement.objects.filter(pk=self.pk).update(
            status=self.status,
            notes=self.notes
        )
        
        # 팩트 테이블 업데이트
        try:
            CommissionFact.update_payment_status(self)
        except Exception as e:
            logger.warning(f"팩트 테이블 상태 업데이트 실패: {str(e)}")
        
        logger.info(f"정산 미입금 처리: {self.company.name} - {self.rebate_amount:,}원")
    
    def set_expected_payment_date(self, expected_date, user=None):
        """입금 예정일 설정"""
        if self.status not in ['approved', 'unpaid']:
            raise ValidationError("승인된 정산 또는 미입금 정산만 예정일을 설정할 수 있습니다.")
        
        old_date = self.expected_payment_date
        self.expected_payment_date = expected_date
        
        # 노트에 변경 사항 기록
        if user:
            if old_date:
                note = f"입금 예정일 변경: {old_date} → {expected_date} (by {user.username})"
            else:
                note = f"입금 예정일 설정: {expected_date} (by {user.username})"
            self.notes = f"{note}\n{self.notes}"
        
        self.save()
        
        logger.info(f"입금 예정일 설정: {self.company.name} - {expected_date}")
    
    def get_payment_info(self):
        """입금 정보 요약 반환"""
        return {
            'status': self.status,
            'status_display': self.get_status_display(),
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'expected_payment_date': self.expected_payment_date,
            'paid_at': self.paid_at,
            'rebate_due_date': self.rebate_due_date
        }
    
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
                
                if order_company.type == 'retail':
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
                
                elif order_company.type == 'agency':
                    # 협력사인 경우
                    agency_settlement = cls.objects.create(
                        order=order,
                        company=order_company,
                        rebate_amount=total_rebate
                    )
                    settlements.append(agency_settlement)
                
                elif order_company.type == 'headquarters':
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


class SettlementStatusHistory(models.Model):
    """
    정산 상태 변경 이력 모델
    
    정산의 모든 상태 변경을 추적하고 기록합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement = models.ForeignKey(
        Settlement,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='정산'
    )
    from_status = models.CharField(
        max_length=20,
        choices=Settlement.STATUS_CHOICES,
        verbose_name='이전 상태'
    )
    to_status = models.CharField(
        max_length=20,
        choices=Settlement.STATUS_CHOICES,
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
        verbose_name = '정산 상태 이력'
        verbose_name_plural = '정산 상태 이력'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['settlement', 'changed_at']),
            models.Index(fields=['to_status']),
            models.Index(fields=['changed_by']),
        ]
    
    def __str__(self):
        return f"{self.settlement.company.name} - {self.get_from_status_display()} → {self.get_to_status_display()}"


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


class CommissionGradeTracking(models.Model):
    """
    수수료 그레이드 달성 추적 모델
    
    업체별로 그레이드 달성 현황을 추적하고 보너스 수수료를 관리합니다.
    """
    
    # 기간 타입
    PERIOD_TYPE_CHOICES = [
        ('monthly', '월별'),
        ('quarterly', '분기별'),
        ('yearly', '연별'),
        ('lifetime', '누적'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='grade_tracking',
        verbose_name='업체'
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='grade_tracking',
        verbose_name='정책'
    )
    
    # 그레이드 적용 기간
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        verbose_name='기간 타입'
    )
    
    period_start = models.DateField(verbose_name='기간 시작일')
    period_end = models.DateField(verbose_name='기간 종료일')
    
    # 그레이드 달성 현황
    current_orders = models.IntegerField(default=0, verbose_name='현재 주문 수')
    target_orders = models.IntegerField(verbose_name='목표 주문 수')
    achieved_grade_level = models.IntegerField(default=0, verbose_name='달성 그레이드 레벨')
    
    # 보너스 수수료
    bonus_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='주문당 보너스 수수료'
    )
    
    # 보너스 정산
    total_bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='총 보너스 금액'
    )
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '수수료 그레이드 추적'
        verbose_name_plural = '수수료 그레이드 추적'
        ordering = ['-created_at']
        unique_together = ['company', 'policy', 'period_type', 'period_start']
        indexes = [
            models.Index(fields=['company', 'period_type']),
            models.Index(fields=['policy', 'period_start', 'period_end']),
            models.Index(fields=['achieved_grade_level']),
        ]
    
    def __str__(self):
        return f"{self.company.name} - {self.policy.title} - {self.get_period_type_display()} ({self.period_start} ~ {self.period_end})"
    
    def clean(self):
        """유효성 검증"""
        if self.period_start > self.period_end:
            raise ValidationError("기간 시작일이 종료일보다 늦을 수 없습니다.")
        
        if self.target_orders <= 0:
            raise ValidationError("목표 주문 수는 0보다 커야 합니다.")
        
        if self.current_orders < 0:
            raise ValidationError("현재 주문 수는 0 이상이어야 합니다.")
    
    def calculate_achievement_rate(self):
        """달성률 계산"""
        if self.target_orders == 0:
            return 0
        return (self.current_orders / self.target_orders) * 100
    
    def update_current_orders(self):
        """현재 주문 수 업데이트"""
        from orders.models import Order
        
        # 해당 기간 내 업체의 주문 수 계산
        orders_count = Order.objects.filter(
            company=self.company,
            policy=self.policy,
            created_at__date__gte=self.period_start,
            created_at__date__lte=self.period_end,
            status__in=['final_approved', 'completed']  # 승인완료 또는 완료된 주문만
        ).count()
        
        old_count = self.current_orders
        self.current_orders = orders_count
        
        # 그레이드 레벨 재계산
        self.recalculate_grade_level()
        
        self.save()
        
        logger.info(
            f"그레이드 추적 업데이트: {self.company.name} - "
            f"주문 수 {old_count} → {orders_count}, 그레이드 레벨: {self.achieved_grade_level}"
        )
    
    def recalculate_grade_level(self):
        """그레이드 레벨 재계산"""
        # 기본 그레이드 레벨 계산 로직
        achievement_rate = self.calculate_achievement_rate()
        
        if achievement_rate >= 100:
            self.achieved_grade_level = 5  # 최고 등급
        elif achievement_rate >= 80:
            self.achieved_grade_level = 4
        elif achievement_rate >= 60:
            self.achieved_grade_level = 3
        elif achievement_rate >= 40:
            self.achieved_grade_level = 2
        elif achievement_rate >= 20:
            self.achieved_grade_level = 1
        else:
            self.achieved_grade_level = 0
        
        # 그레이드 레벨에 따른 보너스 수수료 설정
        bonus_rates = {
            5: 50000,  # 5등급: 50,000원
            4: 30000,  # 4등급: 30,000원
            3: 20000,  # 3등급: 20,000원
            2: 10000,  # 2등급: 10,000원
            1: 5000,   # 1등급: 5,000원
            0: 0,      # 미달성: 0원
        }
        
        self.bonus_per_order = bonus_rates.get(self.achieved_grade_level, 0)
        
        # 총 보너스 금액 계산
        self.total_bonus = self.bonus_per_order * self.current_orders
    
    def get_grade_status(self):
        """그레이드 상태 정보 반환"""
        achievement_rate = self.calculate_achievement_rate()
        
        grade_names = {
            5: 'Diamond',
            4: 'Platinum',
            3: 'Gold',
            2: 'Silver',
            1: 'Bronze',
            0: 'None'
        }
        
        return {
            'level': self.achieved_grade_level,
            'name': grade_names.get(self.achieved_grade_level, 'Unknown'),
            'achievement_rate': round(achievement_rate, 2),
            'current_orders': self.current_orders,
            'target_orders': self.target_orders,
            'remaining_orders': max(0, self.target_orders - self.current_orders),
            'bonus_per_order': self.bonus_per_order,
            'total_bonus': self.total_bonus,
        }
    
    @classmethod
    def create_monthly_tracking(cls, company, policy, year, month, target_orders):
        """월별 그레이드 추적 생성"""
        from django.utils import timezone
        import calendar
        
        # 해당 월의 시작일과 종료일 계산
        start_date = timezone.datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = timezone.datetime(year, month, last_day).date()
        
        tracking, created = cls.objects.get_or_create(
            company=company,
            policy=policy,
            period_type='monthly',
            period_start=start_date,
            defaults={
                'period_end': end_date,
                'target_orders': target_orders,
            }
        )
        
        if not created:
            tracking.target_orders = target_orders
            tracking.save()
        
        # 현재 주문 수 업데이트
        tracking.update_current_orders()
        
        return tracking
    
    @classmethod
    def create_quarterly_tracking(cls, company, policy, year, quarter, target_orders):
        """분기별 그레이드 추적 생성"""
        from django.utils import timezone
        
        # 분기별 시작일과 종료일 계산
        quarter_months = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12)
        }
        
        start_month, end_month = quarter_months[quarter]
        start_date = timezone.datetime(year, start_month, 1).date()
        
        import calendar
        last_day = calendar.monthrange(year, end_month)[1]
        end_date = timezone.datetime(year, end_month, last_day).date()
        
        tracking, created = cls.objects.get_or_create(
            company=company,
            policy=policy,
            period_type='quarterly',
            period_start=start_date,
            defaults={
                'period_end': end_date,
                'target_orders': target_orders,
            }
        )
        
        if not created:
            tracking.target_orders = target_orders
            tracking.save()
        
        # 현재 주문 수 업데이트
        tracking.update_current_orders()
        
        return tracking


class GradeAchievementHistory(models.Model):
    """
    그레이드 달성 이력 모델
    그레이드 레벨 변경 이력을 추적
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    grade_tracking = models.ForeignKey(
        CommissionGradeTracking,
        on_delete=models.CASCADE,
        related_name='achievement_history',
        verbose_name='그레이드 추적'
    )
    
    from_level = models.IntegerField(verbose_name='이전 레벨')
    to_level = models.IntegerField(verbose_name='변경 레벨')
    
    orders_at_change = models.IntegerField(verbose_name='변경시 주문 수')
    bonus_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='보너스 금액'
    )
    
    achieved_at = models.DateTimeField(auto_now_add=True, verbose_name='달성일시')
    
    class Meta:
        verbose_name = '그레이드 달성 이력'
        verbose_name_plural = '그레이드 달성 이력'
        ordering = ['-achieved_at']
        indexes = [
            models.Index(fields=['grade_tracking', 'achieved_at']),
            models.Index(fields=['to_level']),
        ]
    
    def __str__(self):
        return f"{self.grade_tracking.company.name} - Level {self.from_level} → {self.to_level}"


class GradeBonusSettlement(models.Model):
    """
    그레이드 보너스 정산 모델
    그레이드 달성에 따른 보너스 수수료 정산을 관리
    """
    
    STATUS_CHOICES = [
        ('pending', '정산 대기'),
        ('approved', '정산 승인'),
        ('paid', '지급 완료'),
        ('cancelled', '취소됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    grade_tracking = models.ForeignKey(
        CommissionGradeTracking,
        on_delete=models.CASCADE,
        related_name='bonus_settlements',
        verbose_name='그레이드 추적'
    )
    
    bonus_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='보너스 금액'
    )
    
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
        related_name='approved_bonus_settlements',
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '그레이드 보너스 정산'
        verbose_name_plural = '그레이드 보너스 정산'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['grade_tracking', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.grade_tracking.company.name} - 보너스 {self.bonus_amount:,}원 ({self.get_status_display()})"
    
    def approve(self, user):
        """보너스 정산 승인"""
        if self.status != 'pending':
            raise ValidationError("대기 중인 보너스 정산만 승인할 수 있습니다.")
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
        
        logger.info(f"그레이드 보너스 정산 승인: {self.grade_tracking.company.name} - {self.bonus_amount:,}원")
    
    def mark_as_paid(self, user=None):
        """보너스 지급 완료 처리"""
        if self.status != 'approved':
            raise ValidationError("승인된 보너스 정산만 지급 처리할 수 있습니다.")
        
        self.status = 'paid'
        self.paid_at = timezone.now()
        if user:
            self.notes = f"지급 처리자: {user.username}\n{self.notes}"
        self.save()
        
        logger.info(f"그레이드 보너스 지급 완료: {self.grade_tracking.company.name} - {self.bonus_amount:,}원")
    
    @classmethod
    def create_bonus_settlement(cls, grade_tracking):
        """그레이드 추적 기반 보너스 정산 생성"""
        if grade_tracking.total_bonus <= 0:
            return None
        
        # 이미 해당 기간에 대한 보너스 정산이 있는지 확인
        existing = cls.objects.filter(
            grade_tracking=grade_tracking,
            status__in=['pending', 'approved', 'paid']
        ).first()
        
        if existing:
            # 기존 정산이 있으면 금액 업데이트
            if existing.status == 'pending':
                existing.bonus_amount = grade_tracking.total_bonus
                existing.save()
                return existing
            else:
                # 이미 승인되거나 지급된 정산이 있으면 새로 생성하지 않음
                return existing
        
        # 새로운 보너스 정산 생성
        bonus_settlement = cls.objects.create(
            grade_tracking=grade_tracking,
            bonus_amount=grade_tracking.total_bonus
        )
        
        logger.info(
            f"그레이드 보너스 정산 생성: {grade_tracking.company.name} - "
            f"{grade_tracking.total_bonus:,}원 (레벨 {grade_tracking.achieved_grade_level})"
        )
        
        return bonus_settlement


class CommissionFact(models.Model):
    """
    수수료 팩트 테이블 (데이터 웨어하우스)
    
    날짜별, 업체별, 정책별로 수수료 데이터를 집계하여 저장하는 팩트 테이블입니다.
    빠른 분석과 리포팅을 위한 데이터 웨어하우스 구조입니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 차원 키들
    date_key = models.DateField(verbose_name='날짜 차원')  # 날짜 차원
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='commission_facts',
        verbose_name='업체'
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='commission_facts',
        verbose_name='정책'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='commission_facts',
        verbose_name='주문'
    )
    
    # 요금제/계약 정보 (차원)
    carrier = models.CharField(
        max_length=10,
        verbose_name='통신사',
        help_text='SKT, KT, LG, all'
    )
    plan_range = models.IntegerField(
        verbose_name='요금제 범위',
        help_text='요금제 금액대 (11000, 22000, ...165000)'
    )
    contract_period = models.IntegerField(
        verbose_name='계약기간',
        help_text='계약기간 (12, 24, 36, 48개월)'
    )
    
    # 측정값 (Measures)
    base_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='기본 수수료'
    )
    grade_bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='그레이드 보너스'
    )
    total_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='총 수수료'
    )
    
    # 상태 정보
    settlement_status = models.CharField(
        max_length=20,
        verbose_name='정산 상태',
        help_text='pending, approved, paid, unpaid, cancelled'
    )
    payment_status = models.CharField(
        max_length=20,
        verbose_name='입금 상태',
        help_text='pending, paid, unpaid'
    )
    
    # 주문 정보
    order_count_in_period = models.IntegerField(
        default=1,
        verbose_name='기간 내 주문 수',
        help_text='해당 기간 내 업체의 누적 주문 수'
    )
    achieved_grade_level = models.IntegerField(
        default=0,
        verbose_name='달성 그레이드 레벨'
    )
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    # 배치 처리 정보
    batch_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='배치 ID',
        help_text='ETL 배치 처리 시 사용되는 배치 식별자'
    )
    
    class Meta:
        verbose_name = '수수료 팩트'
        verbose_name_plural = '수수료 팩트 테이블'
        ordering = ['-date_key', '-created_at']
        indexes = [
            models.Index(fields=['date_key', 'company']),
            models.Index(fields=['date_key', 'policy']),
            models.Index(fields=['company', 'settlement_status']),
            models.Index(fields=['policy', 'date_key']),
            models.Index(fields=['carrier', 'plan_range']),
            models.Index(fields=['achieved_grade_level']),
            models.Index(fields=['batch_id']),
        ]
        # 중복 방지: 같은 주문에 대해 같은 업체의 팩트는 하나만
        unique_together = ['order', 'company']
    
    def __str__(self):
        return f"{self.date_key} - {self.company.name} - {self.policy.title}: {self.total_commission:,}원"
    
    def clean(self):
        """유효성 검증"""
        if self.base_commission < 0:
            raise ValidationError("기본 수수료는 0 이상이어야 합니다.")
        
        if self.grade_bonus < 0:
            raise ValidationError("그레이드 보너스는 0 이상이어야 합니다.")
        
        # 총 수수료 자동 계산
        if self.base_commission is not None and self.grade_bonus is not None:
            calculated_total = self.base_commission + self.grade_bonus
            if self.total_commission != calculated_total:
                self.total_commission = calculated_total
    
    def save(self, *args, **kwargs):
        """저장 시 유효성 검증 및 로깅"""
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            logger.debug(
                f"수수료 팩트 저장: {self.company.name} - "
                f"날짜: {self.date_key}, 총액: {self.total_commission:,}원"
            )
        except Exception as e:
            logger.error(f"수수료 팩트 저장 실패: {str(e)}")
            raise
    
    @classmethod
    def create_from_settlement(cls, settlement):
        """
        정산 데이터를 기반으로 팩트 테이블 생성
        
        Args:
            settlement: Settlement 객체
        
        Returns:
            CommissionFact 객체
        """
        try:
            # 주문 정보에서 요금제/계약 정보 추출
            order = settlement.order
            policy = order.policy
            
            # 요금제 범위 계산 (주문의 요금제 정보 기반)
            plan_range = cls._calculate_plan_range(order)
            contract_period = cls._extract_contract_period(order)
            carrier = cls._extract_carrier(order)
            
            # 그레이드 보너스 계산
            grade_bonus = cls._calculate_grade_bonus(settlement)
            
            # 현재 기간 내 주문 수 계산
            order_count = cls._calculate_period_order_count(settlement.company, policy)
            
            # 달성 그레이드 레벨 조회
            grade_level = cls._get_achieved_grade_level(settlement.company, policy)
            
            # 팩트 데이터 생성
            fact = cls.objects.create(
                date_key=settlement.created_at.date(),
                company=settlement.company,
                policy=policy,
                order=order,
                carrier=carrier,
                plan_range=plan_range,
                contract_period=contract_period,
                base_commission=settlement.rebate_amount,
                grade_bonus=grade_bonus,
                total_commission=settlement.rebate_amount + grade_bonus,
                settlement_status=settlement.status,
                payment_status='pending' if settlement.status in ['pending', 'approved'] else settlement.status,
                order_count_in_period=order_count,
                achieved_grade_level=grade_level
            )
            
            logger.info(
                f"수수료 팩트 생성: {settlement.company.name} - "
                f"기본: {settlement.rebate_amount:,}원, 보너스: {grade_bonus:,}원"
            )
            
            return fact
            
        except Exception as e:
            logger.error(f"수수료 팩트 생성 실패: {str(e)}")
            raise
    
    @classmethod
    def _calculate_plan_range(cls, order):
        """주문에서 요금제 범위 계산"""
        # 주문에서 요금제 정보 추출 (실제 구현은 주문 모델 구조에 따라 조정)
        try:
            # 기본값으로 33K 범위 사용
            if hasattr(order, 'plan_amount'):
                plan_amount = order.plan_amount
                # 요금제 범위 매핑
                ranges = [11000, 22000, 33000, 44000, 55000, 66000, 77000, 88000, 99000, 110000, 121000, 132000, 143000, 154000, 165000]
                for range_val in ranges:
                    if plan_amount <= range_val:
                        return range_val
                return ranges[-1]  # 최고 범위
            else:
                return 33000  # 기본값
        except Exception:
            return 33000  # 기본값
    
    @classmethod
    def _extract_contract_period(cls, order):
        """주문에서 계약기간 추출"""
        try:
            if hasattr(order, 'contract_period'):
                return order.contract_period
            else:
                return 24  # 기본값 24개월
        except Exception:
            return 24
    
    @classmethod
    def _extract_carrier(cls, order):
        """주문에서 통신사 추출"""
        try:
            if hasattr(order, 'carrier'):
                return order.carrier
            elif hasattr(order.policy, 'carrier'):
                return order.policy.carrier
            else:
                return 'all'  # 기본값
        except Exception:
            return 'all'
    
    @classmethod
    def _calculate_grade_bonus(cls, settlement):
        """정산에 대한 그레이드 보너스 계산"""
        try:
            # 현재 기간의 그레이드 추적 정보 조회
            tracking = CommissionGradeTracking.objects.filter(
                company=settlement.company,
                policy=settlement.order.policy,
                period_start__lte=settlement.created_at.date(),
                period_end__gte=settlement.created_at.date(),
                is_active=True
            ).first()
            
            if tracking:
                return tracking.bonus_per_order
            else:
                return Decimal('0')
                
        except Exception as e:
            logger.warning(f"그레이드 보너스 계산 실패: {str(e)}")
            return Decimal('0')
    
    @classmethod
    def _calculate_period_order_count(cls, company, policy):
        """현재 기간 내 주문 수 계산"""
        try:
            # 현재 월의 주문 수 계산
            from django.utils import timezone
            import calendar
            
            now = timezone.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_of_month = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
            
            from orders.models import Order
            count = Order.objects.filter(
                company=company,
                policy=policy,
                created_at__gte=start_of_month,
                created_at__lte=end_of_month,
                status__in=['final_approved', 'completed']
            ).count()
            
            return count
            
        except Exception as e:
            logger.warning(f"기간 내 주문 수 계산 실패: {str(e)}")
            return 1
    
    @classmethod
    def _get_achieved_grade_level(cls, company, policy):
        """현재 달성 그레이드 레벨 조회"""
        try:
            # 현재 활성화된 그레이드 추적 정보 조회
            from django.utils import timezone
            
            tracking = CommissionGradeTracking.objects.filter(
                company=company,
                policy=policy,
                period_start__lte=timezone.now().date(),
                period_end__gte=timezone.now().date(),
                is_active=True
            ).first()
            
            if tracking:
                return tracking.achieved_grade_level
            else:
                return 0
                
        except Exception as e:
            logger.warning(f"그레이드 레벨 조회 실패: {str(e)}")
            return 0
    
    @classmethod
    def update_payment_status(cls, settlement):
        """
        정산 상태 변경 시 팩트 테이블의 payment_status 업데이트
        
        Args:
            settlement: Settlement 객체
        """
        try:
            facts = cls.objects.filter(
                order=settlement.order,
                company=settlement.company
            )
            
            for fact in facts:
                old_payment_status = fact.payment_status
                
                if settlement.status == 'paid':
                    fact.payment_status = 'paid'
                elif settlement.status == 'unpaid':
                    fact.payment_status = 'unpaid'
                else:
                    fact.payment_status = 'pending'
                
                fact.settlement_status = settlement.status
                fact.save()
                
                logger.debug(
                    f"팩트 테이블 결제 상태 업데이트: {settlement.company.name} - "
                    f"{old_payment_status} → {fact.payment_status}"
                )
                
        except Exception as e:
            logger.error(f"팩트 테이블 상태 업데이트 실패: {str(e)}")
    
    @classmethod
    def get_company_commission_summary(cls, company, start_date=None, end_date=None):
        """
        업체별 수수료 요약 통계
        
        Args:
            company: Company 객체
            start_date: 시작일 (선택적)
            end_date: 종료일 (선택적)
            
        Returns:
            dict: 수수료 통계 정보
        """
        from django.db.models import Sum, Count, Avg
        
        queryset = cls.objects.filter(company=company)
        
        if start_date:
            queryset = queryset.filter(date_key__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_key__lte=end_date)
        
        stats = queryset.aggregate(
            total_commission=Sum('total_commission'),
            total_base_commission=Sum('base_commission'),
            total_grade_bonus=Sum('grade_bonus'),
            total_orders=Count('id'),
            avg_commission=Avg('total_commission')
        )
        
        return {
            'company': company.name,
            'period': f"{start_date or '전체'} ~ {end_date or '현재'}",
            'total_commission': stats['total_commission'] or Decimal('0'),
            'total_base_commission': stats['total_base_commission'] or Decimal('0'),
            'total_grade_bonus': stats['total_grade_bonus'] or Decimal('0'),
            'total_orders': stats['total_orders'] or 0,
            'avg_commission': stats['avg_commission'] or Decimal('0')
        }
    
    @classmethod
    def get_policy_performance(cls, policy, start_date=None, end_date=None):
        """
        정책별 성과 분석
        
        Args:
            policy: Policy 객체
            start_date: 시작일 (선택적)
            end_date: 종료일 (선택적)
            
        Returns:
            dict: 정책 성과 정보
        """
        from django.db.models import Sum, Count, Avg
        
        queryset = cls.objects.filter(policy=policy)
        
        if start_date:
            queryset = queryset.filter(date_key__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_key__lte=end_date)
        
        # 전체 통계
        total_stats = queryset.aggregate(
            total_commission=Sum('total_commission'),
            total_orders=Count('id'),
            avg_commission=Avg('total_commission')
        )
        
        # 업체별 분포
        company_stats = queryset.values('company__name').annotate(
            company_commission=Sum('total_commission'),
            company_orders=Count('id')
        ).order_by('-company_commission')[:10]  # 상위 10개 업체
        
        # 그레이드별 분포
        grade_stats = queryset.values('achieved_grade_level').annotate(
            grade_commission=Sum('total_commission'),
            grade_orders=Count('id')
        ).order_by('achieved_grade_level')
        
        return {
            'policy': policy.title,
            'period': f"{start_date or '전체'} ~ {end_date or '현재'}",
            'total_stats': total_stats,
            'top_companies': list(company_stats),
            'grade_distribution': list(grade_stats)
        }
"""
정산 시스템 시리얼라이저
"""

from rest_framework import serializers
from .models import (
    Settlement, SettlementBatch, SettlementBatchItem, SettlementStatusHistory,
    CommissionGradeTracking, GradeAchievementHistory, GradeBonusSettlement
)
from companies.serializers import CompanySerializer
from orders.serializers import OrderSerializer


class SettlementStatusHistorySerializer(serializers.ModelSerializer):
    """정산 상태 이력 시리얼라이저"""
    
    from_status_display = serializers.CharField(source='get_from_status_display', read_only=True)
    to_status_display = serializers.CharField(source='get_to_status_display', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = SettlementStatusHistory
        fields = [
            'id', 'from_status', 'from_status_display',
            'to_status', 'to_status_display', 'changed_by', 'changed_by_name',
            'reason', 'changed_at', 'user_ip'
        ]
        read_only_fields = ['changed_at']


class SettlementSerializer(serializers.ModelSerializer):
    """정산 시리얼라이저"""
    
    company_name = serializers.CharField(source='company.name', read_only=True)
    order_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    status_history = serializers.SerializerMethodField()
    can_mark_paid = serializers.SerializerMethodField()
    can_mark_unpaid = serializers.SerializerMethodField()
    
    class Meta:
        model = Settlement
        fields = [
            'id', 'order', 'company', 'company_name', 'order_info',
            'rebate_amount', 'status', 'status_display',
            'approved_by', 'approved_by_name', 'approved_at', 'paid_at', 'rebate_due_date',
            'payment_method', 'payment_reference', 'expected_payment_date',  # 새로운 필드
            'notes', 'status_history', 'can_mark_paid', 'can_mark_unpaid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['approved_at', 'paid_at', 'created_at', 'updated_at']
    
    def get_order_info(self, obj):
        """주문 정보 요약 (통신사 주문 정보 포함)"""
        order_info = {
            'id': str(obj.order.id),
            'customer_name': obj.order.customer_name,
            'customer_phone': obj.order.customer_phone,
            'total_amount': str(obj.order.total_amount),
            'created_at': obj.order.created_at.isoformat(),
            'status': obj.order.status,
            'order_number': getattr(obj.order, 'order_number', None),
            # 통신사 관련 정보
            'carrier': None,
            'subscription_type': None,
            'plan_name': None,
            'contract_period': None,
            'activation_date': None
        }
        
        # 통신사 주문 정보가 있는 경우 추가 (정책과 회사를 통해 조회)
        try:
            from orders.telecom_order_models import TelecomOrder
            
            # 같은 정책과 회사로 생성된 통신사 주문 찾기 (임시 방법)
            telecom_orders = TelecomOrder.objects.filter(
                policy=obj.order.policy,
                company=obj.order.company,
                created_at__date=obj.order.created_at.date()
            ).order_by('-created_at')
            
            if telecom_orders.exists():
                telecom_order = telecom_orders.first()
                order_info.update({
                    'carrier': telecom_order.carrier,
                    'subscription_type': telecom_order.subscription_type,
                    'activation_date': telecom_order.activation_date.isoformat() if telecom_order.activation_date else None,
                    'order_number': telecom_order.order_number
                })
                
                # 주문 데이터에서 추가 정보 추출
                if telecom_order.order_data:
                    order_data = telecom_order.order_data
                    order_info.update({
                        'plan_name': order_data.get('plan_name'),
                        'contract_period': order_data.get('contract_period')
                    })
        except Exception as e:
            # 통신사 주문 정보 조회 실패 시 로그만 남기고 계속 진행
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"통신사 주문 정보 조회 실패: {e}")
            
            # 정책에서 기본 통신사 정보 가져오기
            try:
                if hasattr(obj.order.policy, 'carrier'):
                    order_info['carrier'] = obj.order.policy.carrier
            except Exception:
                pass
        
        return order_info
    
    def get_status_history(self, obj):
        """상태 변경 이력 반환 (최근 5개)"""
        try:
            recent_history = obj.status_history.all()[:5]
            return SettlementStatusHistorySerializer(recent_history, many=True).data
        except Exception:
            return []
    
    def get_can_mark_paid(self, obj):
        """입금 완료 처리 가능 여부"""
        return obj.status in ['approved', 'unpaid']
    
    def get_can_mark_unpaid(self, obj):
        """미입금 처리 가능 여부"""
        return obj.status == 'approved'


class PaymentUpdateSerializer(serializers.Serializer):
    """입금 정보 업데이트 시리얼라이저"""
    
    payment_method = serializers.CharField(
        max_length=50,
        required=False,
        help_text='입금 방법 (계좌이체, 현금, 카드 등)'
    )
    payment_reference = serializers.CharField(
        max_length=100,
        required=False,
        help_text='입금 참조번호 (거래번호, 승인번호 등)'
    )
    reason = serializers.CharField(
        required=False,
        help_text='입금 확인 사유 또는 참고사항'
    )


class ExpectedPaymentDateSerializer(serializers.Serializer):
    """입금 예정일 설정 시리얼라이저"""
    
    expected_payment_date = serializers.DateField(
        required=True,
        help_text='입금 예정일 (YYYY-MM-DD 형식)'
    )
    reason = serializers.CharField(
        required=False,
        help_text='예정일 설정 사유'
    )
    
    def validate_expected_payment_date(self, value):
        """예정일 유효성 검증"""
        from django.utils import timezone
        
        if value < timezone.now().date():
            raise serializers.ValidationError('입금 예정일은 오늘 이후로 설정해주세요.')
        
        return value


class SettlementCreateSerializer(serializers.ModelSerializer):
    """정산 생성 시리얼라이저"""
    
    class Meta:
        model = Settlement
        fields = ['order', 'company', 'rebate_amount', 'notes']
    
    def validate(self, data):
        """유효성 검증"""
        order = data.get('order')
        company = data.get('company')
        
        # 중복 정산 방지
        if Settlement.objects.filter(order=order, company=company).exists():
            raise serializers.ValidationError(
                "해당 주문과 업체에 대한 정산이 이미 존재합니다."
            )
        
        # 주문 상태 확인
        if order.status not in ['completed', 'shipped']:
            raise serializers.ValidationError(
                "완료되거나 배송 중인 주문만 정산할 수 있습니다."
            )
        
        return data


class CommissionGradeTrackingSerializer(serializers.ModelSerializer):
    """수수료 그레이드 추적 시리얼라이저"""
    
    company_name = serializers.CharField(source='company.name', read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    grade_status = serializers.SerializerMethodField()
    achievement_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = CommissionGradeTracking
        fields = [
            'id', 'company', 'company_name', 'policy', 'policy_title',
            'period_type', 'period_type_display', 'period_start', 'period_end',
            'current_orders', 'target_orders', 'achieved_grade_level',
            'bonus_per_order', 'total_bonus', 'is_active',
            'grade_status', 'achievement_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'current_orders', 'achieved_grade_level', 'bonus_per_order', 'total_bonus',
            'created_at', 'updated_at'
        ]
    
    def get_grade_status(self, obj):
        """그레이드 상태 정보 반환"""
        return obj.get_grade_status()
    
    def get_achievement_rate(self, obj):
        """달성률 반환"""
        return obj.calculate_achievement_rate()


class GradeAchievementHistorySerializer(serializers.ModelSerializer):
    """그레이드 달성 이력 시리얼라이저"""
    
    company_name = serializers.CharField(source='grade_tracking.company.name', read_only=True)
    policy_title = serializers.CharField(source='grade_tracking.policy.title', read_only=True)
    
    class Meta:
        model = GradeAchievementHistory
        fields = [
            'id', 'grade_tracking', 'company_name', 'policy_title',
            'from_level', 'to_level', 'orders_at_change', 'bonus_amount',
            'achieved_at'
        ]
        read_only_fields = ['achieved_at']


class GradeBonusSettlementSerializer(serializers.ModelSerializer):
    """그레이드 보너스 정산 시리얼라이저"""
    
    company_name = serializers.CharField(source='grade_tracking.company.name', read_only=True)
    policy_title = serializers.CharField(source='grade_tracking.policy.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    grade_level = serializers.IntegerField(source='grade_tracking.achieved_grade_level', read_only=True)
    period_info = serializers.SerializerMethodField()
    
    class Meta:
        model = GradeBonusSettlement
        fields = [
            'id', 'grade_tracking', 'company_name', 'policy_title',
            'bonus_amount', 'status', 'status_display', 'grade_level',
            'approved_by', 'approved_by_name', 'approved_at', 'paid_at',
            'notes', 'period_info', 'created_at', 'updated_at'
        ]
        read_only_fields = ['approved_at', 'paid_at', 'created_at', 'updated_at']
    
    def get_period_info(self, obj):
        """기간 정보 반환"""
        return {
            'period_type': obj.grade_tracking.period_type,
            'period_type_display': obj.grade_tracking.get_period_type_display(),
            'period_start': obj.grade_tracking.period_start,
            'period_end': obj.grade_tracking.period_end
        }


class GradeTargetSetupSerializer(serializers.Serializer):
    """그레이드 목표 설정 시리얼라이저"""
    
    company = serializers.UUIDField(help_text='업체 ID')
    policy = serializers.UUIDField(help_text='정책 ID')
    period_type = serializers.ChoiceField(
        choices=CommissionGradeTracking.PERIOD_TYPE_CHOICES,
        help_text='기간 타입'
    )
    target_orders = serializers.IntegerField(
        min_value=1,
        help_text='목표 주문 수'
    )
    year = serializers.IntegerField(
        min_value=2020,
        max_value=2050,
        help_text='년도'
    )
    month = serializers.IntegerField(
        min_value=1,
        max_value=12,
        required=False,
        help_text='월 (월별 추적시 필수)'
    )
    quarter = serializers.IntegerField(
        min_value=1,
        max_value=4,
        required=False,
        help_text='분기 (분기별 추적시 필수)'
    )
    
    def validate(self, data):
        """유효성 검증"""
        period_type = data.get('period_type')
        month = data.get('month')
        quarter = data.get('quarter')
        
        if period_type == 'monthly' and not month:
            raise serializers.ValidationError({
                'month': '월별 추적시 월을 지정해야 합니다.'
            })
        
        if period_type == 'quarterly' and not quarter:
            raise serializers.ValidationError({
                'quarter': '분기별 추적시 분기를 지정해야 합니다.'
            })
        
        return data


class GradeStatsSerializer(serializers.Serializer):
    """그레이드 통계 시리얼라이저"""
    
    total_companies = serializers.IntegerField()
    active_trackings = serializers.IntegerField()
    total_bonus_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_bonus_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    paid_bonus_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    grade_distribution = serializers.DictField(
        child=serializers.IntegerField(),
        help_text='그레이드별 업체 수 분포'
    )
    
    period_type_distribution = serializers.DictField(
        child=serializers.IntegerField(),
        help_text='기간 타입별 추적 수 분포'
    )


class SettlementStatsSerializer(serializers.Serializer):
    """정산 통계 시리얼라이저"""
    
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    unpaid_count = serializers.IntegerField()  # 새로 추가
    cancelled_count = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class SettlementBatchItemSerializer(serializers.ModelSerializer):
    """정산 배치 항목 시리얼라이저"""
    
    settlement_info = SettlementSerializer(source='settlement', read_only=True)
    
    class Meta:
        model = SettlementBatchItem
        fields = ['id', 'settlement', 'settlement_info', 'added_at']
        read_only_fields = ['added_at']


class SettlementBatchSerializer(serializers.ModelSerializer):
    """정산 배치 시리얼라이저"""
    
    items = SettlementBatchItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    class Meta:
        model = SettlementBatch
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'total_amount', 'items', 'item_count',
            'created_by', 'created_by_name', 'created_at',
            'approved_by', 'approved_by_name', 'approved_at'
        ]
        read_only_fields = [
            'total_amount', 'created_at', 'approved_at',
            'created_by', 'approved_by'
        ]
    
    def validate(self, data):
        """유효성 검증"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "시작일이 종료일보다 늦을 수 없습니다."
            )
        
        return data
    bonus_per_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="건당 보너스 수수료",
        help_text="해당 그레이드 달성 시 건당 추가 지급되는 수수료"
    )
    
    description = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="그레이드 설명",
        help_text="그레이드에 대한 설명 (예: 50건 이상 달성 시)"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화 여부",
        help_text="이 그레이드의 활성화 여부"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="표시 순서",
        help_text="그레이드 표시 순서"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    class Meta:
        verbose_name = "수수료 그레이드"
        verbose_name_plural = "수수료 그레이드 목록"
        ordering = ['policy', 'min_orders']
        unique_together = ['policy', 'min_orders']
        indexes = [
            models.Index(fields=['policy', 'is_active']),
            models.Index(fields=['min_orders']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.min_orders}건 이상: +{self.bonus_per_order:,}원/건"


class PolicyExposure(models.Model):
    """
    정책 노출 관리 모델
    본사가 협력사 및 하위 판매점에 정책을 노출하는 것을 관리
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='exposures', verbose_name='정책')
    agency = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='exposed_policies', verbose_name='노출 업체')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    exposed_at = models.DateTimeField(auto_now_add=True, verbose_name='노출 시작일')
    exposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='노출 설정자')
    
    class Meta:
        unique_together = ['policy', 'agency']
        verbose_name = '정책 노출'
        verbose_name_plural = '정책 노출 관리'
        ordering = ['-exposed_at']
    
    def __str__(self):
        return f"{self.policy.title} → {self.agency.name}"


class AgencyCommission(models.Model):
    """
    협력사 수수료 설정 모델 (기존 AgencyRebate)
    협력사가 판매점에 제공할 수수료를 설정
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_exposure = models.ForeignKey(PolicyExposure, on_delete=models.CASCADE, related_name='commissions', verbose_name='노출된 정책')
    retail_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='agency_commissions', verbose_name='판매점')
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='수수료 금액')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        unique_together = ['policy_exposure', 'retail_company']
        verbose_name = '협력사 수수료'
        verbose_name_plural = '협력사 수수료 설정'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.policy_exposure.policy.title} → {self.retail_company.name}: {self.commission_amount}원"


class AgencyCommissionMatrix(models.Model):
    """
    협력사 수수료 매트릭스 모델 (기존 AgencyRebateMatrix)
    협력사가 판매점에게 제공할 수수료 매트릭스를 관리
    """
    
    # 요금제 범위 선택지
    PLAN_RANGE_CHOICES = [
        (11000, '11K'),
        (22000, '22K'),
        (33000, '33K'),
        (44000, '44K'),
        (55000, '55K'),
        (66000, '66K'),
        (77000, '77K'),
        (88000, '88K'),
        (99000, '99K'),
        (110000, '110K'),
        (121000, '121K'),
        (132000, '132K'),
        (143000, '143K'),
        (154000, '154K'),
        (165000, '165K'),
    ]
    
    # 가입기간 선택지
    CONTRACT_PERIOD_CHOICES = [
        (12, '12개월'),
        (24, '24개월'),
        (36, '36개월'),
        (48, '48개월'),
    ]
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
        ('all', '전체'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="협력사 수수료 매트릭스의 고유 식별자"
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='agency_commission_matrix',
        verbose_name="정책",
        help_text="수수료 매트릭스가 속한 정책"
    )
    
    agency = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='commission_matrices',
        verbose_name="협력사",
        help_text="수수료를 설정하는 협력사"
    )
    
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="수수료가 적용될 통신사"
    )
    
    plan_range = models.IntegerField(
        choices=PLAN_RANGE_CHOICES,
        verbose_name="요금제 금액",
        help_text="수수료가 적용될 요금제 금액 (K 단위)"
    )
    
    contract_period = models.IntegerField(
        choices=CONTRACT_PERIOD_CHOICES,
        verbose_name="계약기간",
        help_text="수수료가 적용될 계약기간 (개월)"
    )
    
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="수수료 금액",
        help_text="해당 조건의 수수료 금액"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "협력사 수수료 매트릭스"
        verbose_name_plural = "협력사 수수료 매트릭스"
        ordering = ['policy', 'agency', 'plan_range', 'contract_period']
        unique_together = ['policy', 'agency', 'carrier', 'plan_range', 'contract_period']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['agency']),
            models.Index(fields=['policy', 'agency']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.agency.name} - {self.get_plan_range_display()} - {self.get_contract_period_display()}: {self.commission_amount:,}원"


class CommissionMatrix(models.Model):
    """
    수수료 매트릭스 모델 (기존 RebateMatrix)
    통신사별 요금제와 가입기간에 따른 수수료 금액을 관리
    """
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
        ('all', '전체'),
    ]
    
    # 요금제 범위 선택지
    PLAN_RANGE_CHOICES = [
        (11000, '11K'),
        (22000, '22K'),
        (33000, '33K'),
        (44000, '44K'),
        (55000, '55K'),
        (66000, '66K'),
        (77000, '77K'),
        (88000, '88K'),
        (99000, '99K'),
        (110000, '110K'),
        (121000, '121K'),
        (132000, '132K'),
        (143000, '143K'),
        (154000, '154K'),
        (165000, '165K'),
    ]
    
    # 가입기간 선택지
    CONTRACT_PERIOD_CHOICES = [
        (12, '12개월'),
        (24, '24개월'),
        (36, '36개월'),
        (48, '48개월'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="수수료 매트릭스의 고유 식별자"
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='commission_matrix',
        verbose_name="정책",
        help_text="수수료 매트릭스가 속한 정책"
    )
    
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="수수료가 적용될 통신사"
    )
    
    plan_range = models.IntegerField(
        choices=PLAN_RANGE_CHOICES,
        verbose_name="요금제 금액",
        help_text="수수료가 적용될 요금제 금액 (K 단위)"
    )
    
    contract_period = models.IntegerField(
        choices=CONTRACT_PERIOD_CHOICES,
        verbose_name="계약기간",
        help_text="수수료가 적용될 계약기간 (개월)"
    )
    
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="수수료 금액",
        help_text="해당 조건의 수수료 금액"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "수수료 매트릭스"
        verbose_name_plural = "수수료 매트릭스"
        ordering = ['policy', 'carrier', 'plan_range', 'contract_period']
        unique_together = ['policy', 'carrier', 'plan_range', 'contract_period']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['carrier', 'plan_range', 'contract_period']),
            models.Index(fields=['policy', 'carrier']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.get_carrier_display()} - {self.get_plan_range_display()} - {self.get_contract_period_display()}: {self.commission_amount:,}원"
    
    @classmethod
    def get_commission_amount(cls, policy, carrier, plan_amount, contract_period):
        """
        주어진 조건에 맞는 수수료 금액 조회
        
        Args:
            policy: Policy 객체
            carrier: 통신사 코드
            plan_amount: 요금제 금액
            contract_period: 가입기간 (개월)
            
        Returns:
            수수료 금액 또는 None
        """
        # 요금제 금액에 맞는 범위 찾기
        plan_range = None
        for range_value, _ in cls.PLAN_RANGE_CHOICES:
            if plan_amount <= range_value:
                plan_range = range_value
                break
        
        if not plan_range:
            # 가장 높은 범위 사용
            plan_range = cls.PLAN_RANGE_CHOICES[-1][0]
        
        try:
            # 먼저 특정 통신사에 대한 매트릭스를 찾기
            matrix = cls.objects.get(
                policy=policy,
                carrier=carrier,
                plan_range=plan_range,
                contract_period=contract_period
            )
            return matrix.commission_amount
        except cls.DoesNotExist:
            try:
                # 특정 통신사가 없으면 전체 통신사 매트릭스를 찾기
                matrix = cls.objects.get(
                    policy=policy,
                    carrier='all',
                    plan_range=plan_range,
                    contract_period=contract_period
                )
                return matrix.commission_amount
            except cls.DoesNotExist:
                return None


# 기존 다른 모델들 (CarrierPlan, DeviceModel, DeviceColor, OrderFormTemplate, OrderFormField)은 
# 수수료와 직접 관련이 없으므로 그대로 유지...

class CarrierPlan(models.Model):
    """통신사별 요금제 관리 모델"""
    
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    carrier = models.CharField(max_length=10, choices=CARRIER_CHOICES, verbose_name="통신사")
    plan_name = models.CharField(max_length=200, verbose_name="요금제명")
    plan_price = models.IntegerField(verbose_name="요금제 금액")
    description = models.TextField(blank=True, verbose_name="요금제 설명")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="생성자")
    
    class Meta:
        verbose_name = "통신사 요금제"
        verbose_name_plural = "통신사 요금제 관리"
        ordering = ['carrier', 'plan_price', 'plan_name']
        unique_together = ['carrier', 'plan_name']
    
    def __str__(self):
        return f"{self.get_carrier_display()} - {self.plan_name} ({self.plan_price:,}원)"


class DeviceModel(models.Model):
    """기기 모델 관리 모델"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=200, verbose_name="모델명")
    manufacturer = models.CharField(max_length=100, verbose_name="제조사")
    description = models.TextField(blank=True, verbose_name="모델 설명")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="생성자")
    
    class Meta:
        verbose_name = "기기 모델"
        verbose_name_plural = "기기 모델 관리"
        ordering = ['manufacturer', 'model_name']
        unique_together = ['manufacturer', 'model_name']
    
    def __str__(self):
        return f"{self.manufacturer} {self.model_name}"


class DeviceColor(models.Model):
    """기기 색상 관리 모델"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, related_name='colors', verbose_name="기기 모델")
    color_name = models.CharField(max_length=100, verbose_name="색상명")
    color_code = models.CharField(max_length=7, blank=True, verbose_name="색상 코드")
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    
    class Meta:
        verbose_name = "기기 색상"
        verbose_name_plural = "기기 색상 관리"
        ordering = ['device_model', 'color_name']
        unique_together = ['device_model', 'color_name']
    
    def __str__(self):
        return f"{self.device_model} - {self.color_name}"


class OrderFormTemplate(models.Model):
    """주문서 양식 템플릿 모델"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.OneToOneField(Policy, on_delete=models.CASCADE, related_name='order_form', verbose_name='정책')
    title = models.CharField(max_length=200, verbose_name='양식 제목')
    description = models.TextField(blank=True, verbose_name='양식 설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='생성자')
    
    class Meta:
        verbose_name = '주문서 양식'
        verbose_name_plural = '주문서 양식 관리'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.policy.title} - 주문서 양식"


class OrderFormField(models.Model):
    """주문서 양식 필드 모델"""
    
    FIELD_TYPE_CHOICES = [
        ('text', '텍스트'),
        ('number', '숫자'),
        ('select', '선택'),
        ('radio', '라디오'),
        ('checkbox', '체크박스'),
        ('textarea', '텍스트 영역'),
        ('date', '날짜'),
        ('phone', '전화번호'),
        ('email', '이메일'),
        ('carrier_plan', '통신사 요금제'),
        ('device_model', '기기 모델'),
        ('device_color', '기기 색상'),
        ('sim_type', '유심 타입'),
        ('contract_period', '계약 기간'),
        ('payment_method', '결제 방법'),
        ('commission_table', '수수료 테이블'),  # rebate_table → commission_table
        ('course', '코스'),
        ('common_support', '공통지원금'),
        ('additional_support', '추가지원금'),
        ('free_amount', '프리금액'),
        ('installment_principal', '할부원금'),
        ('additional_fee', '부가'),
        ('insurance', '보험'),
        ('welfare', '복지'),
        ('legal_info', '법대정보'),
        ('foreigner_info', '외국인정보'),
        ('installment_months', '할부개월수'),
        ('join_type', '가입유형'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(OrderFormTemplate, on_delete=models.CASCADE, related_name='fields', verbose_name='양식 템플릿')
    field_name = models.CharField(max_length=100, verbose_name='필드 이름')
    field_label = models.CharField(max_length=200, verbose_name='필드 라벨')
    field_type = models.CharField(max_length=30, choices=FIELD_TYPE_CHOICES, verbose_name='필드 타입')
    is_required = models.BooleanField(default=False, verbose_name='필수 여부')
    field_options = models.JSONField(blank=True, null=True, verbose_name='필드 옵션')
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='플레이스홀더')
    help_text = models.CharField(max_length=500, blank=True, verbose_name='도움말')
    order = models.IntegerField(default=0, verbose_name='순서')
    
    class Meta:
        verbose_name = '주문서 필드'
        verbose_name_plural = '주문서 필드 관리'
        ordering = ['order', 'field_name']
    
    def __str__(self):
        return f"{self.template.title} - {self.field_label}"

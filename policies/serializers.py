"""
정책 관리 시스템 시리얼라이저
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from companies.models import Company
from .models import (
    Policy, PolicyNotice, PolicyAssignment, PolicyExposure,
    AgencyRebate, CommissionMatrix, OrderFormTemplate, OrderFormField,
    CarrierPlan, DeviceModel, DeviceColor
)


class PolicySerializer(serializers.ModelSerializer):
    """정책 시리얼라이저"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    assignment_count = serializers.SerializerMethodField()
    carrier_display = serializers.CharField(source='get_carrier_display', read_only=True)
    join_type_display = serializers.CharField(source='get_join_type_display', read_only=True)
    contract_period_display = serializers.CharField(source='get_contract_period_display', read_only=True)
    form_type_display = serializers.CharField(source='get_form_type_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    
    class Meta:
        model = Policy
        fields = [
            'id', 'title', 'description', 'form_type', 'form_type_display',
            'type', 'type_display', 'status', 'status_display',
            'carrier', 'carrier_display', 'join_type', 'join_type_display',
            'contract_period', 'contract_period_display',
            'rebate_agency', 'rebate_retail', 'is_active',
            'html_content', 'external_url', 'created_by', 'created_by_username',
            'created_at', 'updated_at', 'assignment_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'html_content']
    
    def get_assignment_count(self, obj):
        """배정된 업체 수 반환"""
        return obj.get_assignment_count()
    

    
    def validate_title(self, value):
        """제목 중복 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("정책 제목은 필수 입력 사항입니다.")
        
        # 수정 시에는 자기 자신을 제외하고 중복 검사
        instance = getattr(self, 'instance', None)
        existing = Policy.objects.filter(title=value.strip())
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("동일한 제목의 정책이 이미 존재합니다.")
        
        return value.strip()
    

    
    def validate(self, data):
        """전체 데이터 검증"""
        # 리베이트 금액 검증
        rebate_agency = data.get('rebate_agency', 0)
        rebate_retail = data.get('rebate_retail', 0)
        
        if rebate_agency < 0:
            raise serializers.ValidationError("대리점 리베이트는 0 이상이어야 합니다.")
        
        if rebate_retail < 0:
            raise serializers.ValidationError("판매점 리베이트는 0 이상이어야 합니다.")
        
        return data


class PolicyNoticeSerializer(serializers.ModelSerializer):
    """정책 안내사항 시리얼라이저"""
    
    notice_type_display = serializers.CharField(source='get_notice_type_display', read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    
    class Meta:
        model = PolicyNotice
        fields = [
            'id', 'policy', 'policy_title', 'notice_type', 'notice_type_display',
            'title', 'content', 'is_important', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("안내 제목은 필수 입력 사항입니다.")
        return value.strip()
    
    def validate_content(self, value):
        """내용 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("안내 내용은 필수 입력 사항입니다.")
        return value


class PolicyAssignmentSerializer(serializers.ModelSerializer):
    """정책 배정 시리얼라이저"""
    
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.type', read_only=True)
    effective_rebate = serializers.SerializerMethodField()
    rebate_source = serializers.SerializerMethodField()
    
    class Meta:
        model = PolicyAssignment
        fields = [
            'id', 'policy', 'policy_title', 'company', 'company_name', 'company_type',
            'custom_rebate', 'expose_to_child', 'assigned_at', 'assigned_to_name',
            'effective_rebate', 'rebate_source'
        ]
        read_only_fields = ['id', 'assigned_at', 'assigned_to_name']
    
    def get_effective_rebate(self, obj):
        """효과적인 리베이트 금액 반환"""
        return float(obj.get_effective_rebate())
    
    def get_rebate_source(self, obj):
        """리베이트 출처 반환"""
        return obj.get_rebate_source()
    
    def validate(self, data):
        """전체 데이터 검증"""
        policy = data.get('policy')
        company = data.get('company')
        custom_rebate = data.get('custom_rebate')
        
        # 중복 배정 검사 (수정 시에는 자기 자신 제외)
        instance = getattr(self, 'instance', None)
        existing = PolicyAssignment.objects.filter(policy=policy, company=company)
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("이미 해당 업체에 배정된 정책입니다.")
        
        # 커스텀 리베이트 검증
        if custom_rebate is not None and custom_rebate < 0:
            raise serializers.ValidationError("커스텀 리베이트는 0 이상이어야 합니다.")
        
        # 비활성 업체 검사
        if company and not company.status:
            raise serializers.ValidationError("운영 중단된 업체에는 정책을 배정할 수 없습니다.")
        
        return data


class PolicyAssignmentListSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.type', read_only=True)

    class Meta:
        model = PolicyAssignment
        fields = [
            'id', 'policy', 'policy_title', 'company', 'company_name', 'company_type',
            'custom_rebate', 'expose_to_child', 'assigned_at', 'assigned_to_name'
        ]
        read_only_fields = fields


class CompanySerializer(serializers.ModelSerializer):
    """업체 시리얼라이저 (정책 배정용)"""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'type', 'type_display', 'business_number',
            'parent_company', 'parent_company_name', 'status',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CarrierPlanSerializer(serializers.ModelSerializer):
    """통신사 요금제 시리얼라이저"""
    
    carrier_display = serializers.CharField(source='get_carrier_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = CarrierPlan
        fields = [
            'id', 'carrier', 'carrier_display', 'plan_name', 'plan_price',
            'description', 'is_active', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_plan_name(self, value):
        """요금제명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("요금제명은 필수 입력 사항입니다.")
        return value.strip()
    
    def validate_plan_price(self, value):
        """요금제 금액 검증"""
        if value <= 0:
            raise serializers.ValidationError("요금제 금액은 0보다 커야 합니다.")
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        carrier = data.get('carrier')
        plan_name = data.get('plan_name')
        
        # 중복 검사 (수정 시에는 자기 자신 제외)
        instance = getattr(self, 'instance', None)
        existing = CarrierPlan.objects.filter(carrier=carrier, plan_name=plan_name)
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("해당 통신사에 동일한 이름의 요금제가 이미 존재합니다.")
        
        return data


class DeviceModelSerializer(serializers.ModelSerializer):
    """기기 모델 시리얼라이저"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    colors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceModel
        fields = [
            'id', 'model_name', 'manufacturer', 'description', 'is_active',
            'created_by', 'created_by_username', 'created_at', 'updated_at',
            'colors_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_colors_count(self, obj):
        """색상 수 반환"""
        return obj.colors.filter(is_active=True).count()
    
    def validate_model_name(self, value):
        """모델명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("모델명은 필수 입력 사항입니다.")
        return value.strip()
    
    def validate_manufacturer(self, value):
        """제조사 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("제조사는 필수 입력 사항입니다.")
        return value.strip()
    
    def validate(self, data):
        """전체 데이터 검증"""
        manufacturer = data.get('manufacturer')
        model_name = data.get('model_name')
        
        # 중복 검사 (수정 시에는 자기 자신 제외)
        instance = getattr(self, 'instance', None)
        existing = DeviceModel.objects.filter(manufacturer=manufacturer, model_name=model_name)
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("해당 제조사에 동일한 모델명이 이미 존재합니다.")
        
        return data


class DeviceColorSerializer(serializers.ModelSerializer):
    """기기 색상 시리얼라이저"""
    
    device_model_name = serializers.CharField(source='device_model.model_name', read_only=True)
    manufacturer = serializers.CharField(source='device_model.manufacturer', read_only=True)
    
    class Meta:
        model = DeviceColor
        fields = [
            'id', 'device_model', 'device_model_name', 'manufacturer',
            'color_name', 'color_code', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_color_name(self, value):
        """색상명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("색상명은 필수 입력 사항입니다.")
        return value.strip()
    
    def validate(self, data):
        """전체 데이터 검증"""
        device_model = data.get('device_model')
        color_name = data.get('color_name')
        
        # 중복 검사 (수정 시에는 자기 자신 제외)
        instance = getattr(self, 'instance', None)
        existing = DeviceColor.objects.filter(device_model=device_model, color_name=color_name)
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("해당 모델에 동일한 색상명이 이미 존재합니다.")
        
        return data


class CommissionMatrixSerializer(serializers.ModelSerializer):
    """수수료 매트릭스 시리얼라이저 (기존 RebateMatrixSerializer에서 이름 변경)"""
    
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    carrier_display = serializers.CharField(source='get_carrier_display', read_only=True)
    plan_range_display = serializers.CharField(source='get_plan_range_display', read_only=True)
    contract_period_display = serializers.CharField(source='get_contract_period_display', read_only=True)
    
    class Meta:
        model = CommissionMatrix
        fields = [
            'id', 'policy', 'policy_title', 'carrier', 'carrier_display',
            'plan_range', 'plan_range_display', 'contract_period', 'contract_period_display',
            'rebate_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_rebate_amount(self, value):
        """리베이트 금액 검증"""
        if value < 0:
            raise serializers.ValidationError("리베이트 금액은 0 이상이어야 합니다.")
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        policy = data.get('policy')
        carrier = data.get('carrier')
        plan_range = data.get('plan_range')
        contract_period = data.get('contract_period')
        
        # 중복 검사 (수정 시에는 자기 자신 제외)
        instance = getattr(self, 'instance', None)
        existing = CommissionMatrix.objects.filter(
            policy=policy,
            carrier=carrier,
            plan_range=plan_range,
            contract_period=contract_period
        )
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("동일한 조건의 리베이트 매트릭스가 이미 존재합니다.")
        
        return data


class OrderFormFieldSerializer(serializers.ModelSerializer):
    """주문서 필드 시리얼라이저"""
    
    field_type_display = serializers.CharField(source='get_field_type_display', read_only=True)
    
    class Meta:
        model = OrderFormField
        fields = [
            'id', 'template', 'field_name', 'field_label', 'field_type', 'field_type_display',
            'is_required', 'field_options', 'placeholder', 'help_text', 'order'
        ]
        read_only_fields = ['id']


class OrderFormTemplateSerializer(serializers.ModelSerializer):
    """주문서 템플릿 시리얼라이저"""
    
    fields = OrderFormFieldSerializer(many=True, read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = OrderFormTemplate
        fields = [
            'id', 'policy', 'policy_title', 'title', 'description', 'is_active',
            'created_by', 'created_by_username', 'created_at', 'updated_at', 'fields'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
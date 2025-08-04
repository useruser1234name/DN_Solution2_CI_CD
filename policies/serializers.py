# policies/serializers.py
import logging
from rest_framework import serializers
from django.contrib.auth.models import User
from companies.models import Company
from .models import Policy, PolicyNotice, PolicyAssignment

logger = logging.getLogger('policies')


class PolicySerializer(serializers.ModelSerializer):
    """
    정책 Serializer
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    form_type_display = serializers.CharField(source='get_form_type_display', read_only=True)
    carrier_display = serializers.CharField(source='get_carrier_display', read_only=True)
    contract_period_display = serializers.CharField(source='get_contract_period_display', read_only=True)
    assignment_count = serializers.SerializerMethodField()
    notices_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = [
            'id', 'title', 'description', 'form_type', 'form_type_display',
            'carrier', 'carrier_display', 'contract_period', 'contract_period_display',
            'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose',
            'html_content', 'created_by_username', 'created_at', 'updated_at',
            'assignment_count', 'notices_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'html_content']
    
    def get_assignment_count(self, obj):
        """배정된 업체 수"""
        return obj.get_assignment_count()
    
    def get_notices_count(self, obj):
        """안내사항 수"""
        return obj.notices.count()
    
    def validate_title(self, value):
        """제목 중복 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("정책 제목은 필수 입력 사항입니다.")
        
        # 중복 체크 (수정 시에는 제외)
        instance = getattr(self, 'instance', None)
        existing = Policy.objects.filter(title=value.strip())
        if instance:
            existing = existing.exclude(id=instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("동일한 제목의 정책이 이미 존재합니다.")
        
        return value.strip()
    
    def validate_rebate_agency(self, value):
        """대리점 리베이트 검증"""
        if value < 0:
            raise serializers.ValidationError("대리점 리베이트는 0 이상이어야 합니다.")
        return value
    
    def validate_rebate_retail(self, value):
        """판매점 리베이트 검증"""
        if value < 0:
            raise serializers.ValidationError("판매점 리베이트는 0 이상이어야 합니다.")
        return value


class PolicyNoticeSerializer(serializers.ModelSerializer):
    """
    정책 안내사항 Serializer
    """
    notice_type_display = serializers.CharField(source='get_notice_type_display', read_only=True)
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    
    class Meta:
        model = PolicyNotice
        fields = [
            'id', 'policy', 'policy_title', 'notice_type', 'notice_type_display',
            'title', 'content', 'is_important', 'order', 'created_at', 'updated_at'
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
        return value.strip()
    
    def validate_order(self, value):
        """순서 검증"""
        if value < 0:
            raise serializers.ValidationError("표시 순서는 0 이상이어야 합니다.")
        return value


class PolicyAssignmentSerializer(serializers.ModelSerializer):
    """
    정책 배정 Serializer
    """
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.get_type_display', read_only=True)
    effective_rebate = serializers.SerializerMethodField()
    rebate_source = serializers.CharField(source='get_rebate_source', read_only=True)
    
    class Meta:
        model = PolicyAssignment
        fields = [
            'id', 'policy', 'policy_title', 'company', 'company_name', 'company_type',
            'custom_rebate', 'effective_rebate', 'rebate_source', 'expose_to_child', 'assigned_at'
        ]
        read_only_fields = ['id', 'assigned_at']
    
    def get_effective_rebate(self, obj):
        """실제 적용되는 리베이트"""
        return obj.get_effective_rebate()
    
    def validate_custom_rebate(self, value):
        """커스텀 리베이트 검증"""
        if value is not None and value < 0:
            raise serializers.ValidationError("커스텀 리베이트는 0 이상이어야 합니다.")
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        policy = data.get('policy')
        company = data.get('company')
        
        if policy and company:
            # 동일 정책을 같은 업체에 중복 배정 방지
            existing = PolicyAssignment.objects.filter(policy=policy, company=company)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError("이미 해당 업체에 배정된 정책입니다.")
        
        return data


class CompanySerializer(serializers.ModelSerializer):
    """
    업체 Serializer (정책 배정용)
    """
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Company
        fields = ['id', 'code', 'name', 'type', 'type_display', 'status']
        read_only_fields = ['id', 'code', 'name', 'type', 'type_display', 'status']


class PolicyDetailSerializer(PolicySerializer):
    """
    정책 상세 Serializer (안내사항과 배정 정보 포함)
    """
    notices = PolicyNoticeSerializer(many=True, read_only=True)
    assignments = PolicyAssignmentSerializer(many=True, read_only=True)
    
    class Meta(PolicySerializer.Meta):
        fields = PolicySerializer.Meta.fields + ['notices', 'assignments']


class PolicyFilterSerializer(serializers.Serializer):
    """
    정책 필터링 Serializer
    """
    search = serializers.CharField(required=False, allow_blank=True)
    form_type = serializers.ChoiceField(choices=Policy.FORM_TYPE_CHOICES, required=False)
    carrier = serializers.ChoiceField(choices=Policy.CARRIER_CHOICES, required=False)
    contract_period = serializers.ChoiceField(choices=Policy.CONTRACT_PERIOD_CHOICES, required=False)
    expose = serializers.BooleanField(required=False)
    premium_market_expose = serializers.BooleanField(required=False)
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False, default=20)


class PolicyCreateSerializer(serializers.ModelSerializer):
    """
    정책 생성 Serializer
    """
    notices = PolicyNoticeSerializer(many=True, required=False)
    
    class Meta:
        model = Policy
        fields = [
            'title', 'description', 'form_type', 'carrier', 'contract_period',
            'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose', 'notices'
        ]
    
    def create(self, validated_data):
        """정책과 안내사항 함께 생성"""
        notices_data = validated_data.pop('notices', [])
        
        # 정책 생성
        policy = Policy.objects.create(**validated_data)
        
        # 안내사항들 생성
        for notice_data in notices_data:
            PolicyNotice.objects.create(policy=policy, **notice_data)
        
        return policy
    
    def to_representation(self, instance):
        """응답 데이터 변환"""
        return PolicySerializer(instance).data


class PolicyUpdateSerializer(serializers.ModelSerializer):
    """
    정책 수정 Serializer
    """
    notices = PolicyNoticeSerializer(many=True, required=False)
    
    class Meta:
        model = Policy
        fields = [
            'title', 'description', 'form_type', 'carrier', 'contract_period',
            'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose', 'notices'
        ]
    
    def update(self, instance, validated_data):
        """정책과 안내사항 함께 수정"""
        notices_data = validated_data.pop('notices', None)
        
        # 정책 수정
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 안내사항 수정 (기존 안내사항 삭제 후 새로 생성)
        if notices_data is not None:
            instance.notices.all().delete()
            for notice_data in notices_data:
                PolicyNotice.objects.create(policy=instance, **notice_data)
        
        return instance
    
    def to_representation(self, instance):
        """응답 데이터 변환"""
        return PolicySerializer(instance).data
# policies/serializers.py
import logging
from rest_framework import serializers
from django.contrib.auth.models import User
from companies.models import Company
from .models import Policy, PolicyAssignment

logger = logging.getLogger('policies')


class PolicySerializer(serializers.ModelSerializer):
    """
    정책 관리를 위한 시리얼라이저
    정책의 CRUD 작업과 HTML 자동 생성 기능 제공
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    html_content = serializers.CharField(read_only=True)
    
    # 관계 필드들
    form_type_display = serializers.CharField(source='get_form_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # 통계 정보
    assignment_count = serializers.SerializerMethodField()
    assigned_companies = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = [
            'id', 'title', 'description', 'form_type', 'form_type_display',
            'rebate_agency', 'rebate_retail', 'expose', 'html_content',
            'created_by', 'created_by_username', 'assignment_count',
            'assigned_companies', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'title': {
                'required': True,
                'allow_blank': False,
                'max_length': 200,
                'help_text': '정책의 제목을 입력하세요'
            },
            'description': {
                'required': True,
                'allow_blank': False,
                'help_text': '정책의 상세 설명을 입력하세요'
            },
            'rebate_agency': {
                'min_value': 0,
                'help_text': '대리점에 지급할 리베이트 금액'
            },
            'rebate_retail': {
                'min_value': 0,
                'help_text': '판매점에 지급할 리베이트 금액'
            }
        }
    
    def get_assignment_count(self, obj):
        """배정된 업체 수 반환"""
        try:
            return obj.get_assignment_count()
        except Exception as e:
            logger.warning(f"정책 배정 수 조회 중 오류: {str(e)} - 정책: {obj.title}")
            return 0
    
    def get_assigned_companies(self, obj):
        """배정된 업체 목록 반환 (간단한 정보만)"""
        try:
            companies = obj.get_assigned_companies()
            return [
                {
                    'id': str(company.id),
                    'name': company.name,
                    'type': company.type
                }
                for company in companies[:10]  # 최대 10개만 반환
            ]
        except Exception as e:
            logger.warning(f"정책 배정 업체 목록 조회 중 오류: {str(e)} - 정책: {obj.title}")
            return []
    
    def validate_title(self, value):
        """정책 제목 검증"""
        if not value or not value.strip():
            logger.warning("빈 정책 제목으로 생성/수정 시도")
            raise serializers.ValidationError("정책 제목은 필수 입력 사항입니다.")
        
        # 중복 제목 검사 (수정 시 자기 자신 제외)
        queryset = Policy.objects.filter(title=value.strip())
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"중복 정책 제목으로 생성/수정 시도: {value}")
            raise serializers.ValidationError("동일한 제목의 정책이 이미 존재합니다.")
        
        return value.strip()
    
    def validate_description(self, value):
        """정책 설명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("정책 설명은 필수 입력 사항입니다.")
        
        if len(value.strip()) > 5000:
            raise serializers.ValidationError("정책 설명은 5000자를 초과할 수 없습니다.")
        
        return value.strip()
    
    def validate_form_type(self, value):
        """신청서 타입 검증"""
        allowed_types = [choice[0] for choice in Policy.FORM_TYPE_CHOICES]
        if value not in allowed_types:
            logger.warning(f"잘못된 신청서 타입으로 생성/수정 시도: {value}")
            raise serializers.ValidationError(
                f"신청서 타입은 {', '.join(allowed_types)} 중 하나여야 합니다."
            )
        return value
    
    def create(self, validated_data):
        """정책 생성"""
        try:
            policy = Policy.objects.create(**validated_data)
            logger.info(f"정책 생성 성공: {policy.title} ({policy.form_type})")
            return policy
        except Exception as e:
            logger.error(f"정책 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("정책 생성 중 오류가 발생했습니다.")
    
    def update(self, instance, validated_data):
        """정책 정보 수정"""
        try:
            old_title = instance.title
            
            # HTML 재생성이 필요한 필드들이 변경되었는지 확인
            regenerate_html = any(
                field in validated_data 
                for field in ['title', 'description', 'form_type', 'rebate_agency', 'rebate_retail']
            )
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            # HTML 재생성
            if regenerate_html:
                instance.html_content = None  # 재생성을 위해 초기화
            
            instance.save()
            
            logger.info(f"정책 정보 수정 성공: {old_title} -> {instance.title}")
            return instance
        
        except Exception as e:
            logger.error(f"정책 정보 수정 실패: {str(e)} - 정책: {instance.title}")
            raise serializers.ValidationError("정책 정보 수정 중 오류가 발생했습니다.")


class PolicyAssignmentSerializer(serializers.ModelSerializer):
    """
    정책 배정 관리를 위한 시리얼라이저
    업체에 정책을 배정하고 커스텀 설정을 관리
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 관계 필드들
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.type', read_only=True)
    
    # 계산된 필드들
    effective_rebate = serializers.SerializerMethodField()
    rebate_source = serializers.SerializerMethodField()
    
    class Meta:
        model = PolicyAssignment
        fields = [
            'id', 'policy', 'policy_title', 'company', 'company_name', 'company_type',
            'custom_rebate', 'effective_rebate', 'rebate_source',
            'expose_to_child', 'assigned_at'
        ]
        extra_kwargs = {
            'policy': {
                'required': True,
                'help_text': '배정할 정책을 선택하세요'
            },
            'company': {
                'required': True,
                'help_text': '정책을 배정받을 업체를 선택하세요'
            },
            'custom_rebate': {
                'min_value': 0,
                'allow_null': True,
                'help_text': '특별 리베이트 (빈 값이면 정책 기본값 사용)'
            }
        }
    
    def get_effective_rebate(self, obj):
        """실제 적용되는 리베이트 금액"""
        try:
            return float(obj.get_effective_rebate())
        except Exception as e:
            logger.warning(f"효과적인 리베이트 조회 중 오류: {str(e)}")
            return 0.0
    
    def get_rebate_source(self, obj):
        """리베이트 출처"""
        try:
            return obj.get_rebate_source()
        except Exception as e:
            logger.warning(f"리베이트 출처 조회 중 오류: {str(e)}")
            return "알 수 없음"
    
    def validate(self, data):
        """전체 데이터 검증"""
        policy = data.get('policy')
        company = data.get('company')
        
        # 정책과 업체가 모두 존재하는지 확인
        if not policy:
            raise serializers.ValidationError({
                'policy': '정책을 선택해주세요.'
            })
        
        if not company:
            raise serializers.ValidationError({
                'company': '업체를 선택해주세요.'
            })
        
        # 비활성 업체 검사
        if not company.status:
            logger.warning(f"비활성 업체에 정책 배정 시도: {policy.title} → {company.name}")
            raise serializers.ValidationError({
                'company': '운영 중단된 업체에는 정책을 배정할 수 없습니다.'
            })
        
        # 중복 배정 검사 (수정 시 자기 자신 제외)
        queryset = PolicyAssignment.objects.filter(policy=policy, company=company)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"중복 정책 배정 시도: {policy.title} → {company.name}")
            raise serializers.ValidationError("이미 해당 업체에 동일한 정책이 배정되어 있습니다.")
        
        return data
    
    def create(self, validated_data):
        """정책 배정 생성"""
        try:
            assignment = PolicyAssignment.objects.create(**validated_data)
            logger.info(f"정책 배정 생성 성공: {assignment.policy.title} → {assignment.company.name}")
            return assignment
        except Exception as e:
            logger.error(f"정책 배정 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("정책 배정 중 오류가 발생했습니다.")


class PolicyHtmlGenerateSerializer(serializers.Serializer):
    """
    정책 HTML 생성을 위한 시리얼라이저
    정책 데이터를 기반으로 HTML 상세페이지 재생성
    """
    
    policy_id = serializers.UUIDField(
        required=True,
        help_text="HTML을 생성할 정책 ID"
    )
    
    force_regenerate = serializers.BooleanField(
        default=False,
        help_text="기존 HTML이 있어도 강제로 재생성할지 여부"
    )
    
    def validate_policy_id(self, value):
        """정책 ID 검증"""
        try:
            policy = Policy.objects.get(id=value)
            return value
        except Policy.DoesNotExist:
            logger.warning(f"존재하지 않는 정책 ID로 HTML 생성 시도: {value}")
            raise serializers.ValidationError("해당 정책을 찾을 수 없습니다.")


class PolicyBulkAssignmentSerializer(serializers.Serializer):
    """
    정책 일괄 배정을 위한 시리얼라이저
    하나의 정책을 여러 업체에 동시에 배정
    """
    
    policy_id = serializers.UUIDField(
        required=True,
        help_text="배정할 정책 ID"
    )
    
    company_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="정책을 배정받을 업체 ID 목록"
    )
    
    custom_rebate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
        help_text="모든 업체에 동일하게 적용할 커스텀 리베이트"
    )
    
    expose_to_child = serializers.BooleanField(
        default=True,
        help_text="하위 업체에 노출할지 여부"
    )
    
    def validate_policy_id(self, value):
        """정책 ID 검증"""
        try:
            policy = Policy.objects.get(id=value)
            return value
        except Policy.DoesNotExist:
            logger.warning(f"존재하지 않는 정책 ID로 일괄 배정 시도: {value}")
            raise serializers.ValidationError("해당 정책을 찾을 수 없습니다.")
    
    def validate_company_ids(self, value):
        """업체 ID 목록 검증"""
        if not value:
            raise serializers.ValidationError("배정받을 업체를 선택해주세요.")
        
        # 존재하는 업체 ID인지 확인
        existing_companies = Company.objects.filter(id__in=value, status=True)
        existing_ids = set(str(company.id) for company in existing_companies)
        provided_ids = set(str(id) for id in value)
        
        if len(existing_ids) != len(provided_ids):
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"유효하지 않은 업체 ID로 일괄 배정 시도: {invalid_ids}")
            raise serializers.ValidationError("일부 업체 ID가 존재하지 않거나 비활성 상태입니다.")
        
        return value


class PolicyExposeToggleSerializer(serializers.Serializer):
    """
    정책 노출 상태 전환을 위한 시리얼라이저
    정책의 노출 상태를 On/Off로 전환하는 기능
    """
    
    policy_id = serializers.UUIDField(
        required=True,
        help_text="노출 상태를 변경할 정책 ID"
    )
    
    def validate_policy_id(self, value):
        """정책 ID 검증"""
        try:
            policy = Policy.objects.get(id=value)
            return value
        except Policy.DoesNotExist:
            logger.warning(f"존재하지 않는 정책 ID로 노출 상태 변경 시도: {value}")
            raise serializers.ValidationError("해당 정책을 찾을 수 없습니다.")


class PolicyBulkDeleteSerializer(serializers.Serializer):
    """
    정책 일괄 삭제를 위한 시리얼라이저
    여러 정책을 선택하여 동시에 삭제하는 기능
    """
    
    policy_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="삭제할 정책 ID 목록"
    )
    
    force_delete = serializers.BooleanField(
        default=False,
        help_text="배정된 정책도 강제로 삭제할지 여부"
    )
    
    def validate_policy_ids(self, value):
        """정책 ID 목록 검증"""
        if not value:
            raise serializers.ValidationError("삭제할 정책을 선택해주세요.")
        
        # 존재하는 정책 ID인지 확인
        existing_policies = Policy.objects.filter(id__in=value)
        existing_ids = set(str(policy.id) for policy in existing_policies)
        provided_ids = set(str(id) for id in value)
        
        if existing_ids != provided_ids:
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"존재하지 않는 정책 ID로 삭제 시도: {invalid_ids}")
            raise serializers.ValidationError("일부 정책 ID가 존재하지 않습니다.")
        
        return value
"""
Serializers for companies app
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from companies.models import Company, CompanyUser, CompanyMessage


class CompanySerializer(serializers.ModelSerializer):
    """업체 시리얼라이저"""
    
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True)
    child_companies_count = serializers.IntegerField(read_only=True)
    users_count = serializers.IntegerField(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'id', 'code', 'name', 'type', 'type_display',
            'parent_company', 'parent_company_name',
            'status', 'visible', 'default_courier',
            'child_companies_count', 'users_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']
    
    def validate(self, data):
        """업체 데이터 검증"""
        # 업체 타입별 검증
        company_type = data.get('type')
        parent_company = data.get('parent_company')
        
        if company_type == 'headquarters' and parent_company:
            raise serializers.ValidationError("본사는 상위 업체를 가질 수 없습니다.")
        
        if company_type == 'agency':
            if not parent_company:
                raise serializers.ValidationError("협력사는 상위 업체(본사)가 필요합니다.")
            if parent_company.type != 'headquarters':
                raise serializers.ValidationError("협력사의 상위 업체는 본사여야 합니다.")
        
        if company_type == 'retail':
            if not parent_company:
                raise serializers.ValidationError("판매점은 상위 업체(협력사)가 필요합니다.")
            if parent_company.type != 'agency':
                raise serializers.ValidationError("판매점의 상위 업체는 협력사여야 합니다.")
        
        return data


class CompanyUserSerializer(serializers.ModelSerializer):
    """업체 사용자 시리얼라이저"""
    
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.type', read_only=True)
    django_username = serializers.CharField(source='django_user.username', read_only=True)
    email = serializers.EmailField(source='django_user.email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # 쓰기 전용 필드
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = CompanyUser
        fields = [
            'id', 'company', 'company_name', 'company_type',
            'django_user', 'django_username', 'email',
            'username', 'role', 'role_display',
            'is_approved', 'status', 'status_display',
            'last_login', 'created_at',
            'password'
        ]
        read_only_fields = ['id', 'django_user', 'last_login', 'created_at']
    
    def create(self, validated_data):
        """사용자 생성"""
        password = validated_data.pop('password', None)
        
        # Django User 생성
        django_user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=password or 'defaultpassword123!'
        )
        
        # CompanyUser 생성
        validated_data['django_user'] = django_user
        company_user = CompanyUser.objects.create(**validated_data)
        
        return company_user
    
    def update(self, instance, validated_data):
        """사용자 수정"""
        password = validated_data.pop('password', None)
        
        # 비밀번호 변경
        if password:
            instance.django_user.set_password(password)
            instance.django_user.save()
        
        # 이메일 업데이트
        if 'email' in validated_data:
            instance.django_user.email = validated_data.pop('email')
            instance.django_user.save()
        
        return super().update(instance, validated_data)


class CompanyMessageSerializer(serializers.ModelSerializer):
    """업체 메시지 시리얼라이저"""
    
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = CompanyMessage
        fields = [
            'id', 'message', 'message_type', 'message_type_display',
            'is_bulk', 'sent_by', 'sent_by_username',
            'company', 'company_name', 'sent_at'
        ]
        read_only_fields = ['id', 'sent_at']
    
    def validate(self, data):
        """메시지 데이터 검증"""
        is_bulk = data.get('is_bulk', False)
        company = data.get('company')
        
        if is_bulk and company:
            raise serializers.ValidationError("일괄 발송 시 개별 업체를 지정할 수 없습니다.")
        
        if not is_bulk and not company:
            raise serializers.ValidationError("개별 발송 시 수신 업체를 지정해야 합니다.")
        
        return data


class CompanyHierarchySerializer(serializers.ModelSerializer):
    """업체 계층 구조 시리얼라이저"""
    
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = ['id', 'code', 'name', 'type', 'status', 'children']
    
    def get_children(self, obj):
        """하위 업체 재귀적 조회"""
        children = obj.company_set.filter(status=True)
        return CompanyHierarchySerializer(children, many=True).data


class CompanyStatisticsSerializer(serializers.Serializer):
    """업체 통계 시리얼라이저"""
    
    total_companies = serializers.IntegerField()
    headquarters_count = serializers.IntegerField()
    agency_count = serializers.IntegerField()
    retail_count = serializers.IntegerField()
    active_users = serializers.IntegerField()
    pending_users = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

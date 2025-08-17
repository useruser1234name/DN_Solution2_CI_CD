# -*- coding: utf-8 -*-
"""
회사 관련 시리얼라이저
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Company, CompanyUser

User = get_user_model()


class CompanySerializer(serializers.ModelSerializer):
    """회사 정보 시리얼라이저"""
    
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True)
    child_companies_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'code', 'name', 'type', 'parent_company', 'parent_company_name',
            'status', 'visible', 'default_courier', 'child_companies_count', 'users_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']
    
    def get_child_companies_count(self, obj):
        """하위 업체 수 계산"""
        return obj.child_companies.count()
    
    def get_users_count(self, obj):
        """소속 사용자 수 계산"""
        return obj.companyuser_set.count()
    
    def validate(self, data):
        """회사 계층 구조 검증"""
        from dn_solution.utils.validators import DataValidator
        
        company_type = data.get('type')
        parent_company = data.get('parent_company')
        
        if company_type and parent_company:
            DataValidator.validate_hierarchy(parent_company, company_type)
        
        return data


class CompanyUserSerializer(serializers.ModelSerializer):
    """회사 사용자 시리얼라이저"""
    
    username = serializers.CharField(source='django_user.username', read_only=True)
    email = serializers.CharField(source='django_user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_type = serializers.CharField(source='company.type', read_only=True)
    
    class Meta:
        model = CompanyUser
        fields = [
            'id', 'company', 'company_name', 'company_type', 'django_user',
            'username', 'email', 'role', 'status', 'is_approved',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CompanyCreateSerializer(serializers.Serializer):
    """회사 및 관리자 생성 시리얼라이저"""
    
    # 회사 정보
    company_name = serializers.CharField(max_length=200)
    company_type = serializers.ChoiceField(choices=['headquarters', 'agency', 'retail'])
    parent_company_code = serializers.CharField(required=False, allow_blank=True)
    business_number = serializers.CharField(max_length=20, required=False)
    address = serializers.CharField(required=False)
    contact_number = serializers.CharField(max_length=20)
    
    # 관리자 정보
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    
    def validate_username(self, value):
        """사용자명 중복 검증"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 사용자명입니다.")
        return value
    
    def validate_parent_company_code(self, value):
        """상위 회사 코드 검증"""
        if value:
            try:
                Company.objects.get(code=value)
            except Company.DoesNotExist:
                raise serializers.ValidationError("유효하지 않은 상위 회사 코드입니다.")
        return value
    
    def validate(self, data):
        """전체 데이터 검증"""
        from dn_solution.utils.validators import DataValidator
        
        company_type = data.get('company_type')
        parent_company_code = data.get('parent_company_code')
        
        # 회사 타입별 상위 회사 필수 여부 검증
        if company_type == 'headquarters':
            if parent_company_code:
                raise serializers.ValidationError("본사는 상위 회사를 가질 수 없습니다.")
        else:
            if not parent_company_code:
                raise serializers.ValidationError(f"{company_type}은(는) 상위 회사 코드가 필요합니다.")
            
            parent_company = Company.objects.get(code=parent_company_code)
            DataValidator.validate_hierarchy(parent_company, company_type)
        
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """커스텀 JWT 토큰 시리얼라이저 (보안 강화)"""
    
    def validate(self, attrs):
        from .security import LoginAttemptManager, SecurityAuditLogger, TokenSecurityManager
        from django.utils import timezone
        
        username = attrs.get('username')
        password = attrs.get('password')
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        
        # 로그인 시도 제한 확인
        if LoginAttemptManager.is_locked_out(username):
            SecurityAuditLogger.log_login_attempt(
                username, ip_address, False, "계정 잠금 상태"
            )
            remaining_time = LoginAttemptManager.get_cache_key(username)
            raise serializers.ValidationError(
                f"너무 많은 로그인 시도로 인해 계정이 일시적으로 잠겼습니다. "
                f"30분 후 다시 시도해주세요."
            )
        
        try:
            data = super().validate(attrs)
        except Exception as e:
            # 로그인 실패 기록
            LoginAttemptManager.record_failed_attempt(username)
            SecurityAuditLogger.log_login_attempt(
                username, ip_address, False, str(e)
            )
            raise e
        
        # CompanyUser 확인
        try:
            company_user = CompanyUser.objects.select_related('company').get(
                django_user=self.user
            )
            
            # 승인 상태 확인
            if not company_user.is_approved:
                LoginAttemptManager.record_failed_attempt(username)
                SecurityAuditLogger.log_login_attempt(
                    username, ip_address, False, "승인되지 않은 사용자"
                )
                raise serializers.ValidationError("승인되지 않은 사용자입니다.")
            
            # 회사 상태 확인
            if not company_user.company.status:
                SecurityAuditLogger.log_login_attempt(
                    username, ip_address, False, "비활성화된 회사"
                )
                raise serializers.ValidationError("비활성화된 회사입니다.")
            
            # 성공한 로그인 처리
            LoginAttemptManager.clear_failed_attempts(username)
            SecurityAuditLogger.log_login_attempt(username, ip_address, True)
            
            # 마지막 로그인 시간 업데이트
            company_user.last_login = timezone.now()
            company_user.save(update_fields=['last_login'])
            
            # 토큰 지문 저장 (보안 강화)
            if request:
                from .security import SecurityConfig
                TokenSecurityManager.store_token_fingerprint(
                    data['access'], request, SecurityConfig.JWT_ACCESS_TOKEN_LIFETIME
                )
            
            # 토큰에 추가 정보 포함
            data['company'] = {
                'id': str(company_user.company.id),
                'code': company_user.company.code,
                'name': company_user.company.name,
                'type': company_user.company.type,
            }
            data['role'] = company_user.role
            data['user_id'] = str(company_user.id)
            
        except CompanyUser.DoesNotExist:
            SecurityAuditLogger.log_login_attempt(
                username, ip_address, False, "회사 사용자 정보 없음"
            )
            raise serializers.ValidationError("회사 사용자 정보가 없습니다.")
        
        return data
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # 토큰에 추가 클레임 포함
        try:
            company_user = CompanyUser.objects.select_related('company').get(
                django_user=user
            )
            token['company_id'] = str(company_user.company.id)
            token['company_type'] = company_user.company.type
            token['role'] = company_user.role
        except CompanyUser.DoesNotExist:
            pass
        
        return token


class UserSerializer(serializers.ModelSerializer):
    """Django User 시리얼라이저"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active']
        read_only_fields = ['id', 'username']
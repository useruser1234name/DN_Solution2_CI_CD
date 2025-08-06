from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import Company, CompanyUser


class CompanySerializer(serializers.ModelSerializer):
    parent_company_name = serializers.SerializerMethodField()
    child_companies = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = '__all__'
        extra_fields = ['parent_company_name', 'child_companies']

    def get_parent_company_name(self, obj):
        return obj.parent_company.name if obj.parent_company else None

    def get_child_companies(self, obj):
        return [child.name for child in obj.child_companies]


class CompanyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUser
        fields = '__all__'


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    커스텀 JWT 토큰 시리얼라이저
    승인된 CompanyUser만 로그인 가능하도록 추가 검증
    """
    
    def validate(self, attrs):
        # 기본 Django User 인증
        data = super().validate(attrs)
        
        # CompanyUser 승인 여부 확인
        try:
            company_user = CompanyUser.objects.get(django_user=self.user)
            
            # 승인되지 않은 사용자는 로그인 불가
            if not company_user.is_approved or company_user.status != 'approved':
                raise serializers.ValidationError(
                    '계정이 아직 승인되지 않았습니다. 관리자 승인 후 로그인할 수 있습니다.'
                )
            
            # 비활성화된 업체 소속 사용자는 로그인 불가
            if not company_user.company.status:
                raise serializers.ValidationError(
                    '소속 업체가 비활성화되어 있습니다. 관리자에게 문의하세요.'
                )
            
            # 추가 사용자 정보를 토큰에 포함
            data['user_info'] = {
                'company_id': str(company_user.company.id),
                'company_name': company_user.company.name,
                'company_type': company_user.company.type,
                'role': company_user.role,
                'username': company_user.username,
            }
            
        except CompanyUser.DoesNotExist:
            raise serializers.ValidationError(
                '업체 사용자 정보를 찾을 수 없습니다. 회원가입을 통해 등록해주세요.'
            )
        
        return data
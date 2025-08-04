from rest_framework import serializers
from .models import Company, CompanyUser

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
    
    def validate(self, data):
        """업체 데이터 검증"""
        # 코드 중복 검사
        code = data.get('code')
        if code:
            if Company.objects.filter(code=code).exists():
                raise serializers.ValidationError({
                    'code': '이미 존재하는 업체 코드입니다.'
                })
        
        # 이름 중복 검사
        name = data.get('name')
        if name:
            if Company.objects.filter(name=name).exists():
                raise serializers.ValidationError({
                    'name': '이미 존재하는 업체명입니다.'
                })
        
        return data

class CompanyUserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CompanyUser
        fields = '__all__' 
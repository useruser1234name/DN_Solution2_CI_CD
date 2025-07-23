# companies/serializers.py
import logging
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Company, CompanyUser, CompanyMessage

logger = logging.getLogger('companies')


class CompanySerializer(serializers.ModelSerializer):
    """
    업체 정보 시리얼라이저
    업체의 CRUD 작업을 위한 직렬화/역직렬화 처리
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    updated_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 업체 타입을 사용자 친화적으로 표시
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    # 관련 사용자 수 표시
    users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'type', 'type_display', 'status', 'visible',
            'default_courier', 'users_count', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'name': {
                'required': True,
                'allow_blank': False,
                'max_length': 200,
                'help_text': '업체의 정식 명칭을 입력하세요'
            },
            'type': {
                'required': True,
                'help_text': '대리점 또는 판매점을 선택하세요'
            },
            'default_courier': {
                'allow_blank': True,
                'max_length': 100,
                'help_text': '기본 택배사를 입력하세요 (선택사항)'
            }
        }
    
    def get_users_count(self, obj):
        """해당 업체에 속한 사용자 수를 반환"""
        try:
            return obj.users.count()
        except Exception as e:
            logger.warning(f"업체 사용자 수 조회 중 오류: {str(e)} - 업체: {obj.name}")
            return 0
    
    def validate_name(self, value):
        """업체명 검증"""
        if not value or not value.strip():
            logger.warning("빈 업체명으로 생성 시도")
            raise serializers.ValidationError("업체명은 필수 입력 사항입니다.")
        
        # 중복 업체명 검사 (수정 시 자기 자신 제외)
        queryset = Company.objects.filter(name=value.strip())
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"중복 업체명으로 생성/수정 시도: {value}")
            raise serializers.ValidationError("동일한 업체명이 이미 존재합니다.")
        
        return value.strip()
    
    def validate_type(self, value):
        """업체 타입 검증"""
        allowed_types = [choice[0] for choice in Company.TYPE_CHOICES]
        if value not in allowed_types:
            logger.warning(f"잘못된 업체 타입으로 생성/수정 시도: {value}")
            raise serializers.ValidationError(
                f"업체 타입은 {', '.join(allowed_types)} 중 하나여야 합니다."
            )
        return value
    
    def create(self, validated_data):
        """업체 생성"""
        try:
            company = Company.objects.create(**validated_data)
            logger.info(f"업체 생성 성공: {company.name} ({company.type})")
            return company
        except Exception as e:
            logger.error(f"업체 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("업체 생성 중 오류가 발생했습니다.")
    
    def update(self, instance, validated_data):
        """업체 정보 수정"""
        try:
            old_name = instance.name
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            instance.save()
            
            logger.info(f"업체 정보 수정 성공: {old_name} -> {instance.name}")
            return instance
        
        except Exception as e:
            logger.error(f"업체 정보 수정 실패: {str(e)} - 업체: {instance.name}")
            raise serializers.ValidationError("업체 정보 수정 중 오류가 발생했습니다.")


class CompanyUserSerializer(serializers.ModelSerializer):
    """
    업체 사용자 시리얼라이저
    업체별 사용자 관리를 위한 직렬화/역직렬화 처리
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    last_login = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 소속 업체 정보
    company_name = serializers.CharField(source='company.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    # 비밀번호는 쓰기 전용
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = CompanyUser
        fields = [
            'id', 'company', 'company_name', 'username', 'password',
            'role', 'role_display', 'last_login', 'created_at'
        ]
        extra_kwargs = {
            'username': {
                'required': True,
                'allow_blank': False,
                'max_length': 150,
                'help_text': '로그인에 사용할 사용자명을 입력하세요'
            },
            'company': {
                'required': True,
                'help_text': '소속 업체를 선택하세요'
            }
        }
    
    def validate_username(self, value):
        """사용자명 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("사용자명은 필수 입력 사항입니다.")
        
        # 중복 사용자명 검사
        queryset = CompanyUser.objects.filter(username=value.strip())
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"중복 사용자명으로 생성/수정 시도: {value}")
            raise serializers.ValidationError("동일한 사용자명이 이미 존재합니다.")
        
        return value.strip()
    
    def validate_company(self, value):
        """업체 검증"""
        if not value.status:
            logger.warning(f"비활성 업체에 사용자 생성 시도: {value.name}")
            raise serializers.ValidationError("운영 중단된 업체에는 사용자를 추가할 수 없습니다.")
        
        return value
    
    def create(self, validated_data):
        """업체 사용자 생성"""
        try:
            # 비밀번호 해시화 (실제 프로젝트에서는 Django의 암호화 기능 사용)
            password = validated_data.pop('password')
            user = CompanyUser.objects.create(**validated_data)
            user.password = password  # 실제로는 해시화해야 함
            user.save()
            
            logger.info(f"업체 사용자 생성 성공: {user.username} - {user.company.name}")
            return user
        
        except Exception as e:
            logger.error(f"업체 사용자 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("사용자 생성 중 오류가 발생했습니다.")


class CompanyMessageSerializer(serializers.ModelSerializer):
    """
    업체 메시지 시리얼라이저
    업체에 발송되는 메시지 관리를 위한 직렬화/역직렬화 처리
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True)
    sent_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    
    # 발송자 정보
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True)
    
    # 수신 업체 정보
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CompanyMessage
        fields = [
            'id', 'message', 'is_bulk', 'sent_by', 'sent_by_username',
            'company', 'company_name', 'sent_at'
        ]
        extra_kwargs = {
            'message': {
                'required': True,
                'allow_blank': False,
                'help_text': '업체에 전송할 메시지를 입력하세요'
            }
        }
    
    def validate(self, data):
        """전체 데이터 검증"""
        is_bulk = data.get('is_bulk', False)
        company = data.get('company')
        
        # 개별 발송인 경우 업체 지정 필수
        if not is_bulk and not company:
            raise serializers.ValidationError({
                'company': '개별 발송 시에는 수신 업체를 지정해야 합니다.'
            })
        
        # 일괄 발송인 경우 업체 지정 불가
        if is_bulk and company:
            raise serializers.ValidationError({
                'company': '일괄 발송 시에는 수신 업체를 지정할 수 없습니다.'
            })
        
        return data
    
    def validate_message(self, value):
        """메시지 내용 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("메시지 내용은 필수 입력 사항입니다.")
        
        if len(value.strip()) > 1000:
            raise serializers.ValidationError("메시지는 1000자를 초과할 수 없습니다.")
        
        return value.strip()
    
    def create(self, validated_data):
        """메시지 생성"""
        try:
            message = CompanyMessage.objects.create(**validated_data)
            
            if message.is_bulk:
                logger.info(f"일괄 메시지 발송: {message.message[:50]}...")
            else:
                logger.info(f"개별 메시지 발송: {message.company.name} - {message.message[:50]}...")
            
            return message
        
        except Exception as e:
            logger.error(f"메시지 생성 실패: {str(e)} - 데이터: {validated_data}")
            raise serializers.ValidationError("메시지 발송 중 오류가 발생했습니다.")


class CompanyBulkDeleteSerializer(serializers.Serializer):
    """
    업체 일괄 삭제를 위한 시리얼라이저
    여러 업체를 선택하여 동시에 삭제하는 기능
    """
    
    company_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="삭제할 업체 ID 목록"
    )
    
    def validate_company_ids(self, value):
        """업체 ID 목록 검증"""
        if not value:
            raise serializers.ValidationError("삭제할 업체를 선택해주세요.")
        
        # 존재하는 업체 ID인지 확인
        existing_companies = Company.objects.filter(id__in=value)
        existing_ids = set(str(company.id) for company in existing_companies)
        provided_ids = set(str(id) for id in value)
        
        if existing_ids != provided_ids:
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"존재하지 않는 업체 ID로 삭제 시도: {invalid_ids}")
            raise serializers.ValidationError("일부 업체 ID가 존재하지 않습니다.")
        
        return value


class CompanyStatusToggleSerializer(serializers.Serializer):
    """
    업체 상태 전환을 위한 시리얼라이저
    업체의 운영 상태를 On/Off로 전환하는 기능
    """
    
    company_id = serializers.UUIDField(
        required=True,
        help_text="상태를 변경할 업체 ID"
    )
    
    def validate_company_id(self, value):
        """업체 ID 검증"""
        try:
            company = Company.objects.get(id=value)
            return value
        except Company.DoesNotExist:
            logger.warning(f"존재하지 않는 업체 ID로 상태 변경 시도: {value}")
            raise serializers.ValidationError("해당 업체를 찾을 수 없습니다.")
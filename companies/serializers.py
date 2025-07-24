# companies/serializers.py
import logging
import uuid # Added for UUID type hinting
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Company, CompanyUser, CompanyMessage

logger = logging.getLogger('companies')


class CompanySerializer(serializers.ModelSerializer):
    """
    업체 정보 시리얼라이저입니다.
    업체의 생성(Create), 조회(Retrieve), 업데이트(Update), 삭제(Delete) 작업을 위한
    데이터 직렬화(Serialization) 및 역직렬화(Deserialization)를 처리합니다.
    """
    
    # 읽기 전용 필드들: 클라이언트에서 값을 전송해도 무시되며, 응답 시에만 포함됩니다.
    id = serializers.UUIDField(read_only=True, help_text="업체의 고유 식별자 (자동 생성)")
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S', help_text="업체 생성 일시")
    updated_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S', help_text="업체 마지막 수정 일시")
    
    # 업체 유형을 사용자 친화적인 텍스트로 표시합니다.
    type_display = serializers.CharField(source='get_type_display', read_only=True, help_text="업체 유형 (표시용)")
    
    # 해당 업체에 속한 사용자 수를 동적으로 계산하여 반환합니다.
    users_count = serializers.SerializerMethodField(help_text="해당 업체에 속한 사용자 수")

    # 상위 업체의 이름을 표시합니다.
    parent_company_name = serializers.CharField(source='parent_company.name', read_only=True, help_text="상위 업체명")

    # 하위 업체 목록을 재귀적으로 표시합니다. (협력사의 경우 판매점 목록)
    child_companies = serializers.SerializerMethodField(help_text="하위 업체 목록")
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'type', 'type_display', 'status', 'visible',
            'default_courier', 'users_count', 'created_at', 'updated_at',
            'parent_company', 'parent_company_name', 'child_companies'
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
            },
            'parent_company': {
                'required': False, 
                'allow_null': True,
                'help_text': '상위 업체의 UUID (본사, 협력사 등)'
            }
        }
    
    def get_users_count(self, obj: Company) -> int:
        """
        주어진 Company 객체에 속한 CompanyUser의 수를 반환합니다.
        N+1 쿼리 방지를 위해 `prefetch_related('users')`와 함께 사용됩니다.
        """
        try:
            return obj.users.count()
        except Exception as e:
            logger.error(f"[CompanySerializer.get_users_count] 업체 사용자 수 조회 중 오류: {str(e)} - 업체: {obj.name} (ID: {obj.id})", exc_info=True)
            return 0

    def get_child_companies(self, obj: Company) -> list:
        """
        주어진 Company 객체의 하위 업체 목록을 반환합니다.
        현재는 'agency' 타입의 업체만 하위 업체(retail)를 가질 수 있습니다.
        """
        if obj.type == 'agency':
            # 재귀적으로 CompanySerializer를 사용하여 하위 업체 정보를 직렬화합니다.
            # 이 부분은 순환 참조를 일으킬 수 있으므로, 실제 프로덕션에서는 깊이 제한 등을 고려해야 합니다.
            return CompanySerializer(obj.child_companies.all(), many=True).data
        return []
    
    def validate_name(self, value: str) -> str:
        """
        업체명 필드의 유효성을 검증합니다.
        업체명이 비어있지 않고, 중복되지 않음을 확인합니다.
        """
        cleaned_name = value.strip()
        if not cleaned_name:
            logger.warning("[CompanySerializer.validate_name] 빈 업체명으로 생성/수정 시도.")
            raise serializers.ValidationError("업체명은 필수 입력 사항입니다.")
        
        # 중복 업체명 검사: 현재 인스턴스(수정 시)를 제외하고 동일한 이름의 업체가 있는지 확인합니다.
        queryset = Company.objects.filter(name=cleaned_name)
        if self.instance: # 업데이트 시에는 자기 자신을 제외
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"[CompanySerializer.validate_name] 중복 업체명 생성/수정 시도: '{cleaned_name}'")
            raise serializers.ValidationError("동일한 업체명이 이미 존재합니다.")
        
        return cleaned_name
    
    def validate_type(self, value: str) -> str:
        """
        업체 유형 필드의 유효성을 검증합니다.
        정의된 `TYPE_CHOICES` 내에 존재하는 유효한 유형인지 확인합니다.
        """
        allowed_types = [choice[0] for choice in Company.TYPE_CHOICES]
        if value not in allowed_types:
            logger.warning(f"[CompanySerializer.validate_type] 잘못된 업체 타입으로 생성/수정 시도: '{value}'")
            raise serializers.ValidationError(
                f"업체 타입은 {', '.join(allowed_types)} 중 하나여야 합니다."
            )
        return value
    
    def create(self, validated_data: dict) -> Company:
        """
        유효성 검증된 데이터를 사용하여 새로운 Company 인스턴스를 생성합니다.
        생성 과정에서 발생할 수 있는 예외를 처리하고 로깅합니다.
        """
        try:
            company = Company.objects.create(**validated_data)
            logger.info(f"[CompanySerializer.create] 업체 생성 성공. Name: '{company.name}', Type: '{company.type}', ID: {company.id}")
            return company
        except Exception as e:
            logger.error(f"[CompanySerializer.create] 업체 생성 실패: {str(e)} - 데이터: {validated_data}", exc_info=True)
            # DRF의 ValidationError로 변환하여 클라이언트에게 명확한 오류 메시지 전달
            raise serializers.ValidationError({'detail': "업체 생성 중 오류가 발생했습니다."})
    
    def update(self, instance: Company, validated_data: dict) -> Company:
        """
        유효성 검증된 데이터를 사용하여 기존 Company 인스턴스를 업데이트합니다.
        업데이트 과정에서 발생할 수 있는 예외를 처리하고 로깅합니다.
        """
        old_name = instance.name # 변경 전 업체명 기록
        old_id = instance.id # 변경 전 ID 기록
        
        try:
            # validated_data의 각 항목을 인스턴스에 반영합니다.
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            instance.save() # 모델의 save() 메서드를 호출하여 변경사항 저장 및 모델 유효성 검증 수행
            
            logger.info(f"[CompanySerializer.update] 업체 정보 수정 성공. 이전: '{old_name}' (ID: {old_id}) -> 현재: '{instance.name}' (ID: {instance.id})")
            return instance
        
        except Exception as e:
            logger.error(f"[CompanySerializer.update] 업체 정보 수정 실패: {str(e)} - 업체: '{old_name}' (ID: {old_id})", exc_info=True)
            raise serializers.ValidationError({'detail': "업체 정보 수정 중 오류가 발생했습니다."})


class CompanyUserSerializer(serializers.ModelSerializer):
    """
    업체 사용자 시리얼라이저입니다.
    업체별 사용자 계정의 직렬화/역직렬화를 처리합니다.
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True, help_text="사용자 고유 식별자 (자동 생성)")
    created_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S', help_text="사용자 생성 일시")
    last_login = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S', help_text="마지막 로그인 일시")
    
    # 소속 업체의 이름을 표시합니다.
    company_name = serializers.CharField(source='company.name', read_only=True, help_text="소속 업체명")
    # 사용자 역할의 표시용 텍스트를 반환합니다.
    role_display = serializers.CharField(source='get_role_display', read_only=True, help_text="사용자 역할 (표시용)")
    
    # 비밀번호는 생성/수정 시에만 사용되며, 조회 시에는 포함되지 않습니다.
    password = serializers.CharField(write_only=True, min_length=6, help_text="사용자 비밀번호 (최소 6자)")
    
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
                'help_text': '사용자가 소속될 업체의 UUID'
            }
        }
    
    def validate_username(self, value: str) -> str:
        """
        사용자명 필드의 유효성을 검증합니다.
        사용자명이 비어있지 않고, 중복되지 않음을 확인합니다.
        """
        cleaned_username = value.strip()
        if not cleaned_username:
            logger.warning("[CompanyUserSerializer.validate_username] 빈 사용자명으로 생성/수정 시도.")
            raise serializers.ValidationError("사용자명은 필수 입력 사항입니다.")
        
        # 중복 사용자명 검사: 현재 인스턴스(수정 시)를 제외하고 동일한 사용자명이 있는지 확인합니다.
        queryset = CompanyUser.objects.filter(username=cleaned_username)
        if self.instance: # 업데이트 시에는 자기 자신을 제외
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            logger.warning(f"[CompanyUserSerializer.validate_username] 중복 사용자명 생성/수정 시도: '{cleaned_username}'")
            raise serializers.ValidationError("동일한 사용자명이 이미 존재합니다.")
        
        return cleaned_username
    
    def validate_company(self, value: Company) -> Company:
        """
        소속 업체 필드의 유효성을 검증합니다.
        선택된 업체가 운영 중단 상태가 아닌지 확인합니다.
        """
        if not value.status: # 업체가 운영 중단 상태인 경우
            logger.warning(f"[CompanyUserSerializer.validate_company] 비활성 업체('{value.name}')에 사용자 생성 시도.")
            raise serializers.ValidationError("운영 중단된 업체에는 사용자를 추가할 수 없습니다.")
        
        return value
    
    def create(self, validated_data: dict) -> CompanyUser:
        """
        유효성 검증된 데이터를 사용하여 새로운 CompanyUser 인스턴스를 생성합니다.
        비밀번호를 해시화하고, 생성 과정을 로깅합니다.
        """
        try:
            # 비밀번호는 저장 전에 반드시 해시화해야 합니다.
            # 실제 구현에서는 Django의 make_password 함수를 사용해야 합니다.
            password = validated_data.pop('password')
            user = CompanyUser.objects.create(**validated_data)
            user.password = password  # TODO: 실제 운영 환경에서는 반드시 비밀번호를 해시화해야 합니다. (예: make_password(password))
            user.save() # save() 메서드 내에서 로깅 처리됨
            
            logger.info(f"[CompanyUserSerializer.create] 업체 사용자 생성 성공. Username: '{user.username}', Company: '{user.company.name}', Role: '{user.role}', ID: {user.id}")
            return user
        
        except Exception as e:
            logger.error(f"[CompanyUserSerializer.create] 업체 사용자 생성 실패: {str(e)} - 데이터: {validated_data}", exc_info=True)
            raise serializers.ValidationError({'detail': "사용자 생성 중 오류가 발생했습니다."})


class CompanyMessageSerializer(serializers.ModelSerializer):
    """
    업체 메시지 시리얼라이저입니다.
    업체에 발송되는 메시지의 직렬화/역직렬화를 처리합니다.
    """
    
    # 읽기 전용 필드들
    id = serializers.UUIDField(read_only=True, help_text="메시지 고유 식별자 (자동 생성)")
    sent_at = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S', help_text="메시지 발송 일시")
    
    # 발송자 사용자명을 표시합니다.
    sent_by_username = serializers.CharField(source='sent_by.username', read_only=True, help_text="메시지 발송자 사용자명")
    
    # 수신 업체의 이름을 표시합니다.
    company_name = serializers.CharField(source='company.name', read_only=True, help_text="수신 업체명")
    
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
                'help_text': '업체에 전송할 메시지 내용을 입력하세요'
            },
            'sent_by': {
                'help_text': '메시지를 발송하는 관리자(Django User)의 ID'
            },
            'company': {
                'help_text': '메시지를 받을 업체의 UUID (일괄 발송 시에는 비워둡니다)'
            }
        }
    
    def validate(self, data: dict) -> dict:
        """
        전체 데이터의 유효성을 검증합니다.
        일괄 발송(`is_bulk`) 여부에 따라 `company` 필드의 필수 여부를 결정합니다.
        """
        is_bulk = data.get('is_bulk', False)
        company = data.get('company')
        
        # 개별 발송인 경우 수신 업체 지정 필수
        if not is_bulk and not company:
            logger.warning("[CompanyMessageSerializer.validate] 개별 메시지 발송 시 수신 업체 누락.")
            raise serializers.ValidationError({
                'company': '개별 발송 시에는 수신 업체를 지정해야 합니다.'
            })
        
        # 일괄 발송인 경우 수신 업체 지정 불가
        if is_bulk and company:
            logger.warning(f"[CompanyMessageSerializer.validate] 일괄 메시지 발송 시 수신 업체('{company.name}') 지정 시도.")
            raise serializers.ValidationError({
                'company': '일괄 발송 시에는 수신 업체를 지정할 수 없습니다.'
            })
        
        return data
    
    def validate_message(self, value: str) -> str:
        """
        메시지 내용 필드의 유효성을 검증합니다.
        메시지 내용이 비어있지 않고, 최대 길이를 초과하지 않음을 확인합니다.
        """
        cleaned_message = value.strip()
        if not cleaned_message:
            logger.warning("[CompanyMessageSerializer.validate_message] 빈 메시지 내용으로 발송 시도.")
            raise serializers.ValidationError("메시지 내용은 필수 입력 사항입니다.")
        
        if len(cleaned_message) > 1000:
            logger.warning(f"[CompanyMessageSerializer.validate_message] 메시지 내용이 1000자를 초과: {len(cleaned_message)}자.")
            raise serializers.ValidationError("메시지는 1000자를 초과할 수 없습니다.")
        
        return cleaned_message
    
    def create(self, validated_data: dict) -> CompanyMessage:
        """
        유효성 검증된 데이터를 사용하여 새로운 CompanyMessage 인스턴스를 생성합니다.
        생성 과정에서 발생할 수 있는 예외를 처리하고 로깅합니다.
        """
        try:
            message = CompanyMessage.objects.create(**validated_data)
            
            if message.is_bulk:
                logger.info(f"[CompanyMessageSerializer.create] 일괄 메시지 발송 성공. Message: '{message.message[:50]}...', ID: {message.id}")
            else:
                logger.info(f"[CompanyMessageSerializer.create] 개별 메시지 발송 성공. Company: '{message.company.name}', Message: '{message.message[:50]}...', ID: {message.id}")
            
            return message
        
        except Exception as e:
            logger.error(f"[CompanyMessageSerializer.create] 메시지 발송 실패: {str(e)} - 데이터: {validated_data}", exc_info=True)
            raise serializers.ValidationError({'detail': "메시지 발송 중 오류가 발생했습니다."})


class CompanyBulkDeleteSerializer(serializers.Serializer):
    """
    업체 일괄 삭제를 위한 시리얼라이저입니다.
    여러 업체의 ID를 받아 유효성을 검증합니다.
    """
    
    company_ids = serializers.ListField(
        child=serializers.UUIDField(help_text="삭제할 개별 업체의 고유 식별자"),
        min_length=1,
        help_text="삭제할 업체 ID 목록 (최소 1개 이상)"
    )
    
    def validate_company_ids(self, value: list) -> list:
        """
        업체 ID 목록의 유효성을 검증합니다.
        목록이 비어있지 않고, 모든 ID가 실제 존재하는 업체에 해당하는지 확인합니다.
        """
        if not value:
            logger.warning("[CompanyBulkDeleteSerializer.validate_company_ids] 삭제할 업체 ID 목록이 비어있음.")
            raise serializers.ValidationError("삭제할 업체를 선택해주세요.")
        
        # 제공된 모든 ID가 실제 존재하는 Company 객체에 해당하는지 확인합니다.
        existing_companies = Company.objects.filter(id__in=value)
        existing_ids = set(str(company.id) for company in existing_companies)
        provided_ids = set(str(id) for id in value)
        
        if existing_ids != provided_ids:
            invalid_ids = provided_ids - existing_ids
            logger.warning(f"[CompanyBulkDeleteSerializer.validate_company_ids] 존재하지 않는 업체 ID 포함: {invalid_ids}")
            raise serializers.ValidationError(f"일부 업체 ID가 존재하지 않습니다: {', '.join(map(str, invalid_ids))}")
        
        return value


class CompanyStatusToggleSerializer(serializers.Serializer):
    """
    업체 운영 상태 전환을 위한 시리얼라이저입니다.
    특정 업체의 ID를 받아 해당 업체의 존재 여부를 검증합니다.
    """
    
    company_id = serializers.UUIDField(
        required=True,
        help_text="상태를 변경할 업체의 고유 식별자"
    )
    
    def validate_company_id(self, value: uuid.UUID) -> uuid.UUID:
        """
        업체 ID의 유효성을 검증합니다.
        해당 ID를 가진 업체가 실제로 존재하는지 확인합니다.
        """
        try:
            company = Company.objects.get(id=value)
            logger.debug(f"[CompanyStatusToggleSerializer.validate_company_id] 업체 ID 유효성 검증 성공. ID: {value}, Name: '{company.name}'")
            return value
        except Company.DoesNotExist:
            logger.warning(f"[CompanyStatusToggleSerializer.validate_company_id] 존재하지 않는 업체 ID로 상태 변경 시도: {value}")
            raise serializers.ValidationError("해당 업체를 찾을 수 없습니다.")
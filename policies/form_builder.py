"""
동적 주문서 양식 빌더
본사가 정책별로 주문서 양식을 설계할 수 있는 시스템
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings

from policies.models import OrderFormTemplate, OrderFormField, Policy

logger = logging.getLogger(__name__)


class FormBuilder:
    """
    주문서 양식 빌더 클래스
    동적으로 주문서 양식을 생성하고 관리
    """
    
    # 설정 파일 경로
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config', 'order_form_fields.json')
    
    # 기본 필드 템플릿 (외부 설정 파일에서 로드)
    @classmethod
    def load_fields_from_config(cls):
        """설정 파일에서 필드 정의 로드"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('fields', [])
            else:
                logger.warning(f"설정 파일을 찾을 수 없습니다: {cls.CONFIG_FILE}")
                return cls._get_default_fields()
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {str(e)}")
            return cls._get_default_fields()
    
    @classmethod
    def _get_default_fields(cls):
        """기본 필드 정의 (설정 파일이 없는 경우 사용)"""
        return [
        # ========== 자동 입력 필드 ==========
        {
            'field_name': 'order_number',
            'field_label': '주문번호',
            'field_type': 'text',
            'is_required': False,
            'is_readonly': True,
            'auto_generate': True,
            'field_options': {'visible': False},
            'order': 1
        },
        {
            'field_name': 'received_date',
            'field_label': '접수일자',
            'field_type': 'datetime',
            'is_required': True,
            'is_readonly': True,
            'auto_fill': 'current_datetime',
            'order': 2
        },
        {
            'field_name': 'primary_id',
            'field_label': '1차 ID',
            'field_type': 'text',
            'is_required': True,
            'is_readonly': True,
            'auto_fill': 'current_user',
            'order': 3
        },
        {
            'field_name': 'retailer_name',
            'field_label': '판매점명',
            'field_type': 'text',
            'is_required': True,
            'is_readonly': True,
            'auto_fill': 'current_user',
            'order': 6
        },
        {
            'field_name': 'carrier',
            'field_label': '통신사',
            'field_type': 'text',
            'is_required': True,
            'is_readonly': True,
            'auto_fill': 'from_policy',
            'order': 4
        },
        {
            'field_name': 'subscription_type',
            'field_label': '가입유형',
            'field_type': 'text',
            'is_required': True,
            'is_readonly': True,
            'auto_fill': 'from_policy',
            'order': 5
        },
        
        # ========== 고객 정보 ==========
        {
            'field_name': 'customer_name',
            'field_label': '고객명',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '고객님의 성함을 입력해주세요',
            'order': 6
        },
        {
            'field_name': 'customer_type',
            'field_label': '고객유형',
            'field_type': 'select',
            'is_required': True,
            'field_options': [
                {'value': '성인일반', 'label': '성인일반'},
                {'value': '법인', 'label': '법인'},
                {'value': '외국인', 'label': '외국인'},
                {'value': '미성년자', 'label': '미성년자'}
            ],
            'order': 7
        },
        {
            'field_name': 'phone_number',
            'field_label': '개통번호',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '010-0000-0000',
            'order': 8
        },
        {
            'field_name': 'ssn',
            'field_label': '주민등록번호',
            'field_type': 'text',
            'is_required': True,
            'is_masked': True,
            'placeholder': '000000-0******',
            'order': 9
        },
        {
            'field_name': 'customer_address',
            'field_label': '고객주소',
            'field_type': 'text',
            'is_required': False,
            'placeholder': '주소를 입력해주세요',
            'order': 10
        },
        
        # ========== 기기 정보 (바코드 스캔 가능) ==========
        {
            'field_name': 'device_model',
            'field_label': '단말기 모델',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '모델명 입력',
            'order': 11
        },
        {
            'field_name': 'device_serial_number',
            'field_label': '단말기 일련번호',
            'field_type': 'barcode_scan',
            'is_required': True,
            'allow_manual': True,
            'placeholder': '바코드 스캔 또는 수기입력',
            'order': 12
        },
        {
            'field_name': 'imei',
            'field_label': 'IMEI',
            'field_type': 'barcode_scan',
            'is_required': True,
            'allow_manual': True,
            'placeholder': '바코드 스캔 또는 수기입력',
            'order': 13
        },
        {
            'field_name': 'imei2',
            'field_label': 'IMEI2',
            'field_type': 'barcode_scan',
            'is_required': False,
            'allow_manual': True,
            'placeholder': '바코드 스캔 또는 수기입력 (선택)',
            'order': 14
        },
        {
            'field_name': 'eid',
            'field_label': 'EID',
            'field_type': 'barcode_scan',
            'is_required': False,
            'allow_manual': True,
            'placeholder': '바코드 스캔 또는 수기입력 (선택)',
            'order': 15
        },
        
        # ========== 요금제 및 서비스 ==========
        {
            'field_name': 'plan_name',
            'field_label': '요금상품명',
            'field_type': 'dropdown_from_policy',
            'is_required': True,
            'data_source': 'policy_plans',
            'placeholder': '요금제를 선택해주세요',
            'order': 16
        },
        {
            'field_name': 'contract_period',
            'field_label': '약정기간',
            'field_type': 'select',
            'is_required': True,
            'field_options': [
                {'value': '무약정', 'label': '무약정'},
                {'value': '선택약정12개월', 'label': '선택약정 12개월'},
                {'value': '선택약정24개월', 'label': '선택약정 24개월'},
                {'value': '공시지원금12개월', 'label': '공시지원금 12개월'},
                {'value': '공시지원금24개월', 'label': '공시지원금 24개월'}
            ],
            'order': 17
        },
        
        # ========== 유심 정보 ==========
        {
            'field_name': 'sim_model',
            'field_label': '유심 모델',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '예: U2920',
            'order': 18
        },
        {
            'field_name': 'sim_serial_number',
            'field_label': '유심일련번호',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '유심 일련번호 입력',
            'order': 19
        },
        
        # ========== 번호이동 정보 ==========
        {
            'field_name': 'previous_carrier',
            'field_label': '이전통신사',
            'field_type': 'select',
            'is_required': False,
            'field_options': [
                {'value': 'SKT', 'label': 'SKT'},
                {'value': 'KT', 'label': 'KT'},
                {'value': 'LGU+', 'label': 'LG U+'},
                {'value': '알뜰폰', 'label': '알뜰폰'}
            ],
            'order': 20
        },
        {
            'field_name': 'mvno_carrier',
            'field_label': '별정통신사',
            'field_type': 'text',
            'is_required': False,
            'placeholder': 'MVNO 사업자명 (알뜰폰인 경우)',
            'order': 21
        },
        
        # ========== 결제 정보 ==========
        {
            'field_name': 'payment_method',
            'field_label': '납부방법',
            'field_type': 'select',
            'is_required': True,
            'field_options': [
                {'value': '은행자동이체', 'label': '은행 자동이체'},
                {'value': '카드자동이체', 'label': '카드 자동이체'},
                {'value': '지로', 'label': '지로'}
            ],
            'order': 22
        },
        {
            'field_name': 'account_holder',
            'field_label': '예금주명',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '예금주 또는 카드주 성명',
            'order': 23
        },
        {
            'field_name': 'bank_name',
            'field_label': '은행(카드)명',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '은행 또는 카드사명',
            'order': 24
        },
        {
            'field_name': 'account_number',
            'field_label': '계좌(카드)번호',
            'field_type': 'text',
            'is_required': True,
            'is_masked': True,
            'placeholder': '계좌번호 또는 카드번호',
            'order': 25
        },
        
        # ========== 추가 정보 ==========
        {
            'field_name': 'reference_url',
            'field_label': '참조 URL',
            'field_type': 'url',
            'is_required': False,
            'placeholder': 'https://... (관련 링크가 있으면 입력)',
            'auto_fill': 'from_policy',
            'order': 26
        },
        {
            'field_name': 'customer_memo',
            'field_label': '고객 메모',
            'field_type': 'large_textarea',
            'is_required': False,
            'placeholder': '고객 관련 상세 메모사항을 자유롭게 입력해주세요.\n여러 줄 입력이 가능합니다.',
            'rows': 8,
            'order': 27
        },
        
        # ========== 파일 첨부 ==========
        {
            'field_name': 'attachments',
            'field_label': '첨부파일',
            'field_type': 'file_upload',
            'is_required': False,
            'multiple': True,
            'accept': 'image/*,.pdf,.doc,.docx',
            'max_files': 4,
            'order': 28
        }
    ]
    
    # DEFAULT_FIELDS 속성을 동적으로 로드하는 프로퍼티로 정의
    @classmethod
    @property
    def DEFAULT_FIELDS(cls):
        """설정 파일에서 필드 정의를 동적으로 로드"""
        return cls.load_fields_from_config()
    
    @classmethod
    def create_template(cls, policy: Policy, fields: List[Dict] = None, 
                       title: str = None, description: str = None) -> OrderFormTemplate:
        """
        정책에 대한 주문서 템플릿 생성
        
        Args:
            policy: Policy 객체
            fields: 필드 정의 리스트 (없으면 기본값 사용)
            title: 템플릿 제목
            description: 템플릿 설명
            
        Returns:
            생성된 OrderFormTemplate 객체
        """
        try:
            with transaction.atomic():
                # 기존 템플릿이 있는지 확인
                if hasattr(policy, 'order_form'):
                    logger.warning(f"정책 '{policy.title}'에 이미 주문서 템플릿이 존재합니다.")
                    return policy.order_form
                
                # 템플릿 생성
                template = OrderFormTemplate.objects.create(
                    policy=policy,
                    title=title or f"{policy.title} 주문서",
                    description=description or f"{policy.title} 정책의 주문서 양식입니다."
                )
                
                # 필드 생성
                fields_to_create = fields or cls.load_fields_from_config()
                for field_data in fields_to_create:
                    cls._create_field(template, field_data)
                
                logger.info(f"정책 '{policy.title}'의 주문서 템플릿이 생성되었습니다.")
                return template
                
        except Exception as e:
            logger.error(f"주문서 템플릿 생성 실패: {str(e)}")
            raise
    
    @classmethod
    def _create_field(cls, template: OrderFormTemplate, field_data: Dict) -> OrderFormField:
        """개별 필드 생성"""
        return OrderFormField.objects.create(
            template=template,
            field_name=field_data.get('field_name'),
            field_label=field_data.get('field_label'),
            field_type=field_data.get('field_type'),
            is_required=field_data.get('is_required', False),
            field_options=field_data.get('field_options'),
            placeholder=field_data.get('placeholder', ''),
            help_text=field_data.get('help_text', ''),
            order=field_data.get('order', 0)
        )
    
    @classmethod
    def update_template(cls, template: OrderFormTemplate, fields: List[Dict] = None) -> OrderFormTemplate:
        """
        기존 템플릿 업데이트
        
        Args:
            template: 업데이트할 템플릿
            fields: 새로운 필드 정의 (없으면 설정 파일에서 로드)
            
        Returns:
            업데이트된 템플릿
        """
        try:
            with transaction.atomic():
                # 기존 필드 삭제
                template.fields.all().delete()
                
                # 새 필드 생성
                fields_to_create = fields or cls.load_fields_from_config()
                for field_data in fields_to_create:
                    cls._create_field(template, field_data)
                
                logger.info(f"주문서 템플릿 '{template.title}'이 업데이트되었습니다.")
                return template
                
        except Exception as e:
            logger.error(f"주문서 템플릿 업데이트 실패: {str(e)}")
            raise
    
    @classmethod
    def validate_submission(cls, template: OrderFormTemplate, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        제출된 데이터의 유효성 검증
        
        Args:
            template: 주문서 템플릿
            data: 제출된 데이터
            
        Returns:
            검증된 데이터
            
        Raises:
            ValidationError: 유효성 검증 실패
        """
        errors = {}
        validated_data = {}
        
        # 템플릿의 모든 필드에 대해 검증
        for field in template.fields.all():
            field_name = field.field_name
            field_value = data.get(field_name)
            
            # 필수 필드 검증
            if field.is_required and not field_value:
                errors[field_name] = f"{field.field_label}은(는) 필수 입력 항목입니다."
                continue
            
            # 필드 타입별 검증
            if field_value:
                try:
                    validated_value = cls._validate_field_value(field, field_value)
                    validated_data[field_name] = validated_value
                except ValidationError as e:
                    errors[field_name] = str(e)
        
        if errors:
            raise ValidationError(errors)
        
        return validated_data
    
    @classmethod
    def _validate_field_value(cls, field: OrderFormField, value: Any) -> Any:
        """개별 필드 값 검증"""
        if field.field_type == 'text':
            if not isinstance(value, str):
                raise ValidationError("텍스트 값이어야 합니다.")
            return value.strip()
            
        elif field.field_type == 'number':
            try:
                return int(value)
            except ValueError:
                raise ValidationError("숫자 값이어야 합니다.")
                
        elif field.field_type == 'select':
            if field.field_options:
                valid_values = [opt['value'] for opt in field.field_options]
                if value not in valid_values:
                    raise ValidationError(f"유효한 옵션이 아닙니다. 가능한 값: {', '.join(valid_values)}")
            return value
            
        elif field.field_type == 'checkbox':
            return bool(value)
            
        elif field.field_type == 'textarea':
            if not isinstance(value, str):
                raise ValidationError("텍스트 값이어야 합니다.")
            return value.strip()
            
        elif field.field_type == 'date':
            # 날짜 형식 검증 (YYYY-MM-DD)
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                raise ValidationError("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")
            return value
            
        return value
    
    @classmethod
    def render_form(cls, template: OrderFormTemplate) -> Dict[str, Any]:
        """
        템플릿을 기반으로 프론트엔드용 폼 구조 생성
        
        Args:
            template: 주문서 템플릿
            
        Returns:
            프론트엔드에서 렌더링할 수 있는 폼 구조
        """
        form_structure = {
            'template_id': str(template.id),
            'title': template.title,
            'description': template.description,
            'fields': []
        }
        
        for field in template.fields.all().order_by('order'):
            field_dict = {
                'name': field.field_name,
                'label': field.field_label,
                'type': field.field_type,
                'required': field.is_required,
                'placeholder': field.placeholder,
                'help_text': field.help_text,
                'order': field.order
            }
            
            # 선택 옵션이 있는 경우
            if field.field_options:
                field_dict['options'] = field.field_options
            
            form_structure['fields'].append(field_dict)
        
        return form_structure
    
    @classmethod
    def add_field(cls, template: OrderFormTemplate, field_data: Dict) -> OrderFormField:
        """
        템플릿에 필드 추가
        
        Args:
            template: 대상 템플릿
            field_data: 추가할 필드 정보
            
        Returns:
            생성된 필드
        """
        try:
            # 마지막 순서 찾기
            last_order = template.fields.aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            
            field_data['order'] = field_data.get('order', last_order + 1)
            
            field = cls._create_field(template, field_data)
            logger.info(f"필드 '{field.field_label}'이(가) 템플릿에 추가되었습니다.")
            return field
            
        except Exception as e:
            logger.error(f"필드 추가 실패: {str(e)}")
            raise
    
    @classmethod
    def remove_field(cls, template: OrderFormTemplate, field_name: str) -> bool:
        """
        템플릿에서 필드 제거
        
        Args:
            template: 대상 템플릿
            field_name: 제거할 필드 이름
            
        Returns:
            제거 성공 여부
        """
        try:
            field = template.fields.get(field_name=field_name)
            field.delete()
            logger.info(f"필드 '{field_name}'이(가) 템플릿에서 제거되었습니다.")
            return True
            
        except OrderFormField.DoesNotExist:
            logger.warning(f"필드 '{field_name}'을(를) 찾을 수 없습니다.")
            return False
        except Exception as e:
            logger.error(f"필드 제거 실패: {str(e)}")
            raise
    
    @classmethod
    def reorder_fields(cls, template: OrderFormTemplate, field_orders: Dict[str, int]) -> None:
        """
        필드 순서 재정렬
        
        Args:
            template: 대상 템플릿
            field_orders: {field_name: order} 형태의 딕셔너리
        """
        try:
            with transaction.atomic():
                for field_name, order in field_orders.items():
                    template.fields.filter(field_name=field_name).update(order=order)
                
                logger.info(f"템플릿 '{template.title}'의 필드 순서가 재정렬되었습니다.")
                
        except Exception as e:
            logger.error(f"필드 순서 재정렬 실패: {str(e)}")
            raise
    
    @classmethod
    def clone_template(cls, source_template: OrderFormTemplate, 
                      target_policy: Policy, title: str = None) -> OrderFormTemplate:
        """
        기존 템플릿을 복제하여 새 정책에 적용
        
        Args:
            source_template: 복제할 원본 템플릿
            target_policy: 대상 정책
            title: 새 템플릿 제목
            
        Returns:
            복제된 템플릿
        """
        try:
            with transaction.atomic():
                # 새 템플릿 생성
                new_template = OrderFormTemplate.objects.create(
                    policy=target_policy,
                    title=title or f"{target_policy.title} 주문서 (복제됨)",
                    description=source_template.description
                )
                
                # 필드 복제
                for field in source_template.fields.all():
                    field_data = {
                        'field_name': field.field_name,
                        'field_label': field.field_label,
                        'field_type': field.field_type,
                        'is_required': field.is_required,
                        'field_options': field.field_options,
                        'placeholder': field.placeholder,
                        'help_text': field.help_text,
                        'order': field.order
                    }
                    cls._create_field(new_template, field_data)
                
                logger.info(f"템플릿이 복제되었습니다: {source_template.title} → {new_template.title}")
                return new_template
                
        except Exception as e:
            logger.error(f"템플릿 복제 실패: {str(e)}")
            raise
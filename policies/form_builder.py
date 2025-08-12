"""
동적 주문서 양식 빌더
본사가 정책별로 주문서 양식을 설계할 수 있는 시스템
"""

import json
import logging
from typing import Dict, List, Any, Optional
from django.core.exceptions import ValidationError
from django.db import transaction

from policies.models import OrderFormTemplate, OrderFormField, Policy

logger = logging.getLogger(__name__)


class FormBuilder:
    """
    주문서 양식 빌더 클래스
    동적으로 주문서 양식을 생성하고 관리
    """
    
    # 기본 필드 템플릿
    DEFAULT_FIELDS = [
        {
            'field_name': 'customer_name',
            'field_label': '고객명',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '고객님의 성함을 입력해주세요',
            'order': 1
        },
        {
            'field_name': 'phone',
            'field_label': '전화번호',
            'field_type': 'text',
            'is_required': True,
            'placeholder': '010-1234-5678',
            'order': 2
        },
        {
            'field_name': 'carrier',
            'field_label': '통신사',
            'field_type': 'select',
            'is_required': True,
            'field_options': [
                {'value': 'skt', 'label': 'SKT'},
                {'value': 'kt', 'label': 'KT'},
                {'value': 'lg', 'label': 'LG U+'}
            ],
            'order': 3
        },
        {
            'field_name': 'plan',
            'field_label': '요금제',
            'field_type': 'select',
            'is_required': True,
            'placeholder': '요금제를 선택해주세요',
            'order': 4
        },
        {
            'field_name': 'contract_period',
            'field_label': '가입기간',
            'field_type': 'select',
            'is_required': True,
            'field_options': [
                {'value': '3', 'label': '3개월'},
                {'value': '6', 'label': '6개월'},
                {'value': '9', 'label': '9개월'},
                {'value': '12', 'label': '12개월'},
                {'value': '24', 'label': '24개월'},
                {'value': '36', 'label': '36개월'}
            ],
            'order': 5
        },
        {
            'field_name': 'url',
            'field_label': 'URL 링크',
            'field_type': 'text',
            'is_required': True,
            'placeholder': 'https://...',
            'order': 6
        },
        {
            'field_name': 'memo',
            'field_label': '메모',
            'field_type': 'textarea',
            'is_required': False,
            'placeholder': '추가 메모사항을 입력해주세요',
            'order': 7
        }
    ]
    
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
                fields_to_create = fields or cls.DEFAULT_FIELDS
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
    def update_template(cls, template: OrderFormTemplate, fields: List[Dict]) -> OrderFormTemplate:
        """
        기존 템플릿 업데이트
        
        Args:
            template: 업데이트할 템플릿
            fields: 새로운 필드 정의
            
        Returns:
            업데이트된 템플릿
        """
        try:
            with transaction.atomic():
                # 기존 필드 삭제
                template.fields.all().delete()
                
                # 새 필드 생성
                for field_data in fields:
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
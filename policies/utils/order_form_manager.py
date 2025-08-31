"""
주문서 양식 관리 유틸리티

주문서 양식의 생성, 업데이트, 검증 등을 담당하는 유틸리티 함수들
"""

import logging
from django.db import transaction
from ..models import OrderFormTemplate, OrderFormField
from ..form_builder import FormBuilder

logger = logging.getLogger('policies')


class OrderFormManager:
    """
    주문서 양식 관리 클래스
    정책에 대한 주문서 양식 생성 및 업데이트 기능 제공
    """
    
    @classmethod
    def create_order_form(cls, policy, user=None):
        """
        정책에 대한 주문서 양식 생성
        
        Args:
            policy: Policy 객체
            user: 생성자 (User 객체, 선택사항)
            
        Returns:
            생성된 OrderFormTemplate 객체
        """
        try:
            with transaction.atomic():
                # 기존 양식이 있는지 확인
                if hasattr(policy, 'order_form'):
                    logger.warning(f"정책 '{policy.title}'에 이미 주문서 양식이 존재합니다.")
                    return policy.order_form
                
                # 템플릿 생성
                template = OrderFormTemplate.objects.create(
                    policy=policy,
                    title=f"{policy.title} - 주문서",
                    description="자동 생성된 주문서 양식입니다.",
                    created_by=user
                )
                
                # 설정 파일에서 필드 정의 로드
                default_fields = FormBuilder.load_fields_from_config()
                
                # 필드들 생성
                for field_data in default_fields:
                    OrderFormField.objects.create(
                        template=template,
                        field_name=field_data.get('field_name'),
                        field_label=field_data.get('field_label'),
                        field_type=field_data.get('field_type'),
                        is_required=field_data.get('is_required', False),
                        field_options=field_data.get('field_options'),
                        placeholder=field_data.get('placeholder', ''),
                        help_text=field_data.get('help_text', ''),
                        order=field_data.get('order', 0),
                        is_readonly=field_data.get('is_readonly', False),
                        is_masked=field_data.get('is_masked', False),
                        auto_fill=field_data.get('auto_fill', ''),
                        auto_generate=field_data.get('auto_generate', False),
                        allow_manual=field_data.get('allow_manual', True),
                        data_source=field_data.get('data_source', ''),
                        rows=field_data.get('rows', 3),
                        multiple=field_data.get('multiple', False),
                        max_files=field_data.get('max_files', 1),
                        accept=field_data.get('accept', '')
                    )
                
                logger.info(f"정책 '{policy.title}'에 주문서 양식이 생성되었습니다. ({len(default_fields)}개 필드)")
                return template
                
        except Exception as e:
            logger.error(f"주문서 양식 생성 실패: {str(e)} - 정책: {policy.title}")
            raise
    
    @classmethod
    def update_order_form(cls, template, force=False):
        """
        주문서 양식을 최신 버전으로 업데이트
        
        Args:
            template: OrderFormTemplate 객체
            force: 강제 업데이트 여부 (기본값: False)
            
        Returns:
            업데이트된 OrderFormTemplate 객체
        """
        try:
            # 업데이트 필요 여부 확인 (force=True이면 무조건 업데이트)
            # 기본 제공 필드 수 일치만으로 '최신' 판단을 하지 않고, 관리자 편집 내용을 보호하기 위해
            # force=False 인 경우에는 업데이트를 건너뛴다.
            if not force:
                logger.info(f"주문서 양식 '{template.title}' 사용자 편집 보호: 강제 업데이트가 아니므로 스킵")
                return template
            
            with transaction.atomic():
                # 기존 필드 삭제 후 기본 필드로 재생성 (강제 업데이트인 경우에만)
                template.fields.all().delete()
                
                # 설정 파일에서 필드 정의 로드
                default_fields = FormBuilder.load_fields_from_config()
                
                for field_data in default_fields:
                    OrderFormField.objects.create(
                        template=template,
                        field_name=field_data.get('field_name'),
                        field_label=field_data.get('field_label'),
                        field_type=field_data.get('field_type'),
                        is_required=field_data.get('is_required', False),
                        field_options=field_data.get('field_options'),
                        placeholder=field_data.get('placeholder', ''),
                        help_text=field_data.get('help_text', ''),
                        order=field_data.get('order', 0),
                        is_readonly=field_data.get('is_readonly', False),
                        is_masked=field_data.get('is_masked', False),
                        auto_fill=field_data.get('auto_fill', ''),
                        auto_generate=field_data.get('auto_generate', False),
                        allow_manual=field_data.get('allow_manual', True),
                        data_source=field_data.get('data_source', ''),
                        rows=field_data.get('rows', 3),
                        multiple=field_data.get('multiple', False),
                        max_files=field_data.get('max_files', 1),
                        accept=field_data.get('accept', '')
                    )
                
                logger.info(f"주문서 양식 '{template.title}'이 최신 버전으로 업데이트되었습니다. ({len(default_fields)}개 필드)")
                return template
                
        except Exception as e:
            logger.error(f"주문서 양식 업데이트 실패: {str(e)} - 템플릿: {template.title}")
            raise
    
    @classmethod
    def ensure_latest_order_form(cls, policy, force=False):
        """
        정책에 최신 주문서 양식이 적용되어 있는지 확인하고,
        없거나 오래된 경우 최신 양식을 적용
        
        Args:
            policy: Policy 객체
            force: 강제 업데이트 여부 (기본값: False)
            
        Returns:
            OrderFormTemplate 객체
        """
        try:
            # 양식이 있는지 확인
            template_exists = hasattr(policy, 'order_form')
            
            if not template_exists:
                # 양식이 없으면 새로 생성
                return cls.create_order_form(policy)
            else:
                # 양식이 있으면 업데이트 여부 확인
                return cls.update_order_form(policy.order_form, force=force)
                
        except Exception as e:
            logger.error(f"주문서 양식 확인 실패: {str(e)} - 정책: {policy.title}")
            raise

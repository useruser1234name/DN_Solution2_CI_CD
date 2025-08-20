"""
모든 정책에 기본 주문서 양식을 적용하는 관리 명령어
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from policies.models import Policy, OrderFormTemplate, OrderFormField
from policies.form_builder import FormBuilder
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '모든 정책에 기본 주문서 양식을 적용합니다.'

    def handle(self, *args, **options):
        self.stdout.write('정책에 기본 주문서 양식 적용 시작...')
        
        # 모든 정책 조회
        policies = Policy.objects.all()
        self.stdout.write(f'총 {policies.count()}개의 정책을 처리합니다.')
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for policy in policies:
            try:
                with transaction.atomic():
                    # 이미 양식이 있는지 확인
                    template_exists = hasattr(policy, 'order_form')
                    
                    if template_exists:
                        # 기존 양식 업데이트
                        template = policy.order_form
                        # 기존 필드 삭제
                        template.fields.all().delete()
                        
                        self.stdout.write(f'정책 "{policy.title}"의 기존 주문서 양식을 업데이트합니다.')
                        updated_count += 1
                    else:
                        # 새 양식 생성
                        template = OrderFormTemplate.objects.create(
                            policy=policy,
                            title=f"{policy.title} - 주문서",
                            description="기본 주문서 양식입니다."
                        )
                        self.stdout.write(f'정책 "{policy.title}"에 새 주문서 양식을 생성합니다.')
                        created_count += 1
                    
                    # FormBuilder의 DEFAULT_FIELDS 사용 (업데이트된 필드 포함)
                    default_fields = FormBuilder.DEFAULT_FIELDS
                    
                    # 자동 생성 필드 추가 (주문번호, 접수일자, 1차 ID, 통신사)
                    auto_fields = [
                        {
                            'field_name': 'order_number',
                            'field_label': '주문번호',
                            'field_type': 'text',
                            'is_required': True,
                            'is_readonly': True,
                            'auto_generate': True,
                            'order': 0
                        },
                        {
                            'field_name': 'received_date',
                            'field_label': '접수일자',
                            'field_type': 'date',
                            'is_required': True,
                            'is_readonly': True,
                            'auto_fill': 'current_datetime',
                            'order': 1
                        },
                        {
                            'field_name': 'company_code',
                            'field_label': '1차 ID',
                            'field_type': 'text',
                            'is_required': True,
                            'is_readonly': True,
                            'auto_fill': 'current_user',
                            'order': 2
                        },
                        {
                            'field_name': 'carrier',
                            'field_label': '통신사',
                            'field_type': 'text',
                            'is_required': True,
                            'is_readonly': True,
                            'auto_fill': 'from_policy',
                            'order': 3
                        }
                    ]
                    
                    # 기존 필드와 자동 생성 필드 병합
                    merged_fields = auto_fields + [{
                        **field,
                        'order': field.get('order', 0) + len(auto_fields)  # 순서 조정
                    } for field in default_fields]
                    
                    # 필드들 생성
                    for field_data in merged_fields:
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
                            allow_manual=field_data.get('allow_manual', True)
                        )
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'정책 "{policy.title}" 처리 중 오류: {str(e)}'))
                error_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'작업 완료: {created_count}개 생성, {updated_count}개 업데이트, {error_count}개 오류'
        ))

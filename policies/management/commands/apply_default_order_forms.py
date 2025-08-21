"""
모든 정책에 기본 주문서 양식을 적용하는 관리 명령어
"""

from django.core.management.base import BaseCommand
from policies.models import Policy
from policies.utils.order_form_manager import OrderFormManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '모든 정책에 기본 주문서 양식을 적용합니다.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='모든 양식을 강제로 업데이트합니다.'
        )
        parser.add_argument(
            '--policy-id',
            type=str,
            help='특정 정책 ID만 처리합니다.'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        policy_id = options.get('policy_id')
        
        self.stdout.write('정책에 기본 주문서 양식 적용 시작...')
        
        # 정책 조회
        if policy_id:
            policies = Policy.objects.filter(id=policy_id)
            self.stdout.write(f'정책 ID {policy_id}에 대한 주문서 양식을 처리합니다.')
        else:
            policies = Policy.objects.all()
            self.stdout.write(f'총 {policies.count()}개의 정책을 처리합니다.')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for policy in policies:
            try:
                # 이미 양식이 있는지 확인
                template_exists = hasattr(policy, 'order_form')
                
                if not template_exists:
                    # 새 양식 생성
                    OrderFormManager.create_order_form(policy)
                    self.stdout.write(f'정책 "{policy.title}"에 새 주문서 양식을 생성했습니다.')
                    created_count += 1
                else:
                    # 기존 양식 업데이트 여부 확인
                    if force:
                        # 강제 업데이트
                        OrderFormManager.update_order_form(policy.order_form, force=True)
                        self.stdout.write(f'정책 "{policy.title}"의 주문서 양식을 강제로 업데이트했습니다.')
                        updated_count += 1
                    else:
                        # 필요 시 업데이트
                        current_fields_count = policy.order_form.fields.count()
                        
                        from policies.form_builder import FormBuilder
                        default_fields_count = len(FormBuilder.load_fields_from_config())
                        
                        if current_fields_count != default_fields_count:
                            OrderFormManager.update_order_form(policy.order_form)
                            self.stdout.write(f'정책 "{policy.title}"의 주문서 양식을 업데이트했습니다.')
                            updated_count += 1
                        else:
                            self.stdout.write(f'정책 "{policy.title}"의 주문서 양식은 이미 최신 상태입니다.')
                            skipped_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'정책 "{policy.title}" 처리 중 오류: {str(e)}'))
                error_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'작업 완료: {created_count}개 생성, {updated_count}개 업데이트, {skipped_count}개 건너뜀, {error_count}개 오류'
        ))

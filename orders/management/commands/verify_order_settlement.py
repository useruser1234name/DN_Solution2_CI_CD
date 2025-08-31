import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import Order
from settlements.models import Settlement


class Command(BaseCommand):
    help = "최신 주문 1건에 대해 순차 상태 전이 후 정산 생성 여부를 검증합니다."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='bon_admin', help='상태 변경 권한 사용자명(본사 관리자)')
        parser.add_argument('--order-id', type=str, default='', help='대상 주문 ID (미지정 시 최신 주문)')

    def handle(self, *args, **options):
        username = options['username']
        order_id = options['order_id']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"사용자를 찾을 수 없습니다: {username}"))
            sys.exit(1)

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"주문을 찾을 수 없습니다: {order_id}"))
                sys.exit(1)
        else:
            order = Order.objects.order_by('-created_at').first()

        if not order:
            self.stderr.write(self.style.ERROR("검증할 주문이 없습니다."))
            sys.exit(1)

        self.stdout.write(self.style.MIGRATE_HEADING(f"대상 주문: {order.id} 상태={order.status}"))

        # 순차 전이 계획 (백엔드 전이 규칙과 일치)
        steps = ['approved', 'processing', 'shipped', 'completed', 'final_approved']

        progressed = []
        for step in steps:
            order.refresh_from_db()
            # 현재 상태 기준으로 가능한 단계만 시도
            can = order.can_transition_to(step, user=user)
            if not can:
                continue
            try:
                order.update_status(step, user=user)
                progressed.append(step)
                self.stdout.write(self.style.SUCCESS(f"→ {step} 전이 완료"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"전이 실패({step}): {e}"))
                break

        order.refresh_from_db()
        self.stdout.write(self.style.MIGRATE_LABEL(f"최종 상태: {order.status}"))

        settlements = Settlement.objects.filter(order=order).select_related('company')
        self.stdout.write(self.style.HTTP_INFO(f"정산 생성 건수: {settlements.count()}"))
        for s in settlements:
            # 간단 요약
            self.stdout.write(f" - {getattr(s.company, 'type', '?')} | {getattr(s.company, 'name', '-')} | 정산액={s.rebate_amount} | 상태={s.status}")

        # 결과 코드
        if order.status == 'final_approved' and settlements.exists():
            self.stdout.write(self.style.SUCCESS("검증 성공: 최종승인 및 정산 생성 확인"))
            return
        self.stderr.write(self.style.WARNING("검증 경고: 최종승인 또는 정산 생성이 완료되지 않았습니다."))



"""
수수료 ETL 배치 처리 관리 명령어

Usage:
    python manage.py run_commission_etl --start-date 2025-01-01 --end-date 2025-01-31
    python manage.py run_commission_etl --rebuild  # 전체 재구축
    python manage.py run_commission_etl --sync-today  # 오늘 데이터만 동기화
"""

import logging
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from settlements.models import Settlement, CommissionFact
from companies.models import Company
from policies.models import Policy

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '수수료 데이터 웨어하우스 ETL 처리'
    
    def add_arguments(self, parser):
        # 날짜 범위 옵션
        parser.add_argument(
            '--start-date',
            type=str,
            help='시작일 (YYYY-MM-DD 형식)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='종료일 (YYYY-MM-DD 형식)'
        )
        
        # 특수 모드 옵션
        parser.add_argument(
            '--rebuild',
            action='store_true',
            help='전체 팩트 테이블 재구축'
        )
        parser.add_argument(
            '--sync-today',
            action='store_true',
            help='오늘 데이터만 동기화'
        )
        parser.add_argument(
            '--sync-recent',
            type=int,
            default=7,
            help='최근 N일 데이터 동기화 (기본값: 7일)'
        )
        
        # 실행 옵션
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 실행 없이 계획만 출력'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='배치 처리 사이즈 (기본값: 1000)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='기존 데이터 덮어쓰기'
        )
    
    def handle(self, *args, **options):
        """ETL 처리 메인 로직"""
        try:
            # 배치 ID 생성
            batch_id = f"etl_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.stdout.write(
                self.style.SUCCESS(f'수수료 ETL 배치 처리 시작: {batch_id}')
            )
            
            # 실행 모드 결정
            if options['rebuild']:
                self._rebuild_all_facts(batch_id, options)
            elif options['sync_today']:
                self._sync_today(batch_id, options)
            elif options['start_date'] and options['end_date']:
                self._sync_date_range(batch_id, options)
            else:
                # 기본값: 최근 N일 동기화
                self._sync_recent_days(batch_id, options)
            
            self.stdout.write(
                self.style.SUCCESS(f'ETL 배치 처리 완료: {batch_id}')
            )
            
        except Exception as e:
            logger.error(f"ETL 처리 중 오류: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'ETL 처리 실패: {str(e)}')
            )
            raise CommandError(f'ETL 처리 실패: {str(e)}')
    
    def _rebuild_all_facts(self, batch_id, options):
        """전체 팩트 테이블 재구축"""
        self.stdout.write('전체 팩트 테이블 재구축 시작...')
        
        if options['dry_run']:
            total_settlements = Settlement.objects.count()
            self.stdout.write(f'[DRY RUN] {total_settlements}개 정산 데이터 처리 예정')
            return
        
        # 기존 팩트 데이터 삭제 (force 옵션인 경우)
        if options['force']:
            deleted_count = CommissionFact.objects.all().delete()[0]
            self.stdout.write(f'기존 팩트 데이터 {deleted_count}건 삭제')
        
        # 모든 정산 데이터 처리
        settlements = Settlement.objects.select_related(
            'company', 'order', 'order__policy'
        ).all()
        
        self._process_settlements_batch(settlements, batch_id, options)
    
    def _sync_today(self, batch_id, options):
        """오늘 데이터만 동기화"""
        today = timezone.now().date()
        self.stdout.write(f'오늘({today}) 데이터 동기화 시작...')
        
        settlements = Settlement.objects.filter(
            created_at__date=today
        ).select_related('company', 'order', 'order__policy')
        
        if options['dry_run']:
            self.stdout.write(f'[DRY RUN] {settlements.count()}개 정산 데이터 처리 예정')
            return
        
        self._process_settlements_batch(settlements, batch_id, options)
    
    def _sync_date_range(self, batch_id, options):
        """날짜 범위 데이터 동기화"""
        try:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        except ValueError as e:
            raise CommandError(f'날짜 형식 오류: {e}')
        
        if start_date > end_date:
            raise CommandError('시작일이 종료일보다 늦을 수 없습니다.')
        
        self.stdout.write(f'{start_date} ~ {end_date} 데이터 동기화 시작...')
        
        settlements = Settlement.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('company', 'order', 'order__policy')
        
        if options['dry_run']:
            self.stdout.write(f'[DRY RUN] {settlements.count()}개 정산 데이터 처리 예정')
            return
        
        self._process_settlements_batch(settlements, batch_id, options)
    
    def _sync_recent_days(self, batch_id, options):
        """최근 N일 데이터 동기화"""
        days = options['sync_recent']
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(f'최근 {days}일({start_date} ~ {end_date}) 데이터 동기화 시작...')
        
        settlements = Settlement.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('company', 'order', 'order__policy')
        
        if options['dry_run']:
            self.stdout.write(f'[DRY RUN] {settlements.count()}개 정산 데이터 처리 예정')
            return
        
        self._process_settlements_batch(settlements, batch_id, options)
    
    def _process_settlements_batch(self, settlements, batch_id, options):
        """정산 데이터 배치 처리"""
        batch_size = options['batch_size']
        total_count = settlements.count()
        processed_count = 0
        error_count = 0
        
        self.stdout.write(f'총 {total_count}개 정산 데이터 처리 시작 (배치 크기: {batch_size})')
        
        # 배치별로 처리
        for i in range(0, total_count, batch_size):
            batch_settlements = settlements[i:i + batch_size]
            
            with transaction.atomic():
                for settlement in batch_settlements:
                    try:
                        self._process_single_settlement(settlement, batch_id, options)
                        processed_count += 1
                        
                        # 진행 상황 출력
                        if processed_count % 100 == 0:
                            progress = (processed_count / total_count) * 100
                            self.stdout.write(
                                f'진행률: {progress:.1f}% ({processed_count}/{total_count})'
                            )
                            
                    except Exception as e:
                        error_count += 1
                        logger.error(f'정산 처리 실패: {settlement.id} - {str(e)}')
                        
                        # 에러가 너무 많으면 중단
                        if error_count > total_count * 0.1:  # 10% 이상 에러 시 중단
                            raise CommandError(f'에러율이 너무 높습니다. 처리 중단. (에러: {error_count}건)')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'배치 처리 완료 - 성공: {processed_count}건, 실패: {error_count}건'
            )
        )
    
    def _process_single_settlement(self, settlement, batch_id, options):
        """개별 정산 데이터 처리"""
        # 기존 팩트 데이터 확인
        existing_fact = CommissionFact.objects.filter(
            order=settlement.order,
            company=settlement.company
        ).first()
        
        if existing_fact:
            if options['force']:
                # 기존 데이터 업데이트
                self._update_commission_fact(existing_fact, settlement, batch_id)
            else:
                # 상태만 업데이트
                if existing_fact.settlement_status != settlement.status:
                    existing_fact.settlement_status = settlement.status
                    if settlement.status == 'paid':
                        existing_fact.payment_status = 'paid'
                    elif settlement.status == 'unpaid':
                        existing_fact.payment_status = 'unpaid'
                    else:
                        existing_fact.payment_status = 'pending'
                    
                    existing_fact.batch_id = batch_id
                    existing_fact.save()
        else:
            # 새로운 팩트 데이터 생성
            CommissionFact.create_from_settlement(settlement)
            
            # 배치 ID 업데이트
            CommissionFact.objects.filter(
                order=settlement.order,
                company=settlement.company
            ).update(batch_id=batch_id)
    
    def _update_commission_fact(self, fact, settlement, batch_id):
        """팩트 데이터 업데이트"""
        # 그레이드 보너스 재계산
        grade_bonus = CommissionFact._calculate_grade_bonus(settlement)
        
        # 현재 주문 수 재계산
        order_count = CommissionFact._calculate_period_order_count(
            settlement.company, settlement.order.policy
        )
        
        # 그레이드 레벨 재조회
        grade_level = CommissionFact._get_achieved_grade_level(
            settlement.company, settlement.order.policy
        )
        
        # 팩트 데이터 업데이트
        fact.base_commission = settlement.rebate_amount
        fact.grade_bonus = grade_bonus
        fact.total_commission = settlement.rebate_amount + grade_bonus
        fact.settlement_status = settlement.status
        
        if settlement.status == 'paid':
            fact.payment_status = 'paid'
        elif settlement.status == 'unpaid':
            fact.payment_status = 'unpaid'
        else:
            fact.payment_status = 'pending'
        
        fact.order_count_in_period = order_count
        fact.achieved_grade_level = grade_level
        fact.batch_id = batch_id
        
        fact.save()

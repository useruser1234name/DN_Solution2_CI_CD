"""
수수료 분석 및 보고서 생성 도구
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from .models import CommissionFact, CommissionGradeTracking, Settlement
from companies.models import Company
from policies.models import Policy

logger = logging.getLogger(__name__)


class CommissionAnalyzer:
    """수수료 데이터 분석 클래스"""
    
    def __init__(self, start_date=None, end_date=None):
        """
        초기화
        
        Args:
            start_date: 분석 시작일
            end_date: 분석 종료일
        """
        self.start_date = start_date or (timezone.now().date() - timedelta(days=30))
        self.end_date = end_date or timezone.now().date()
    
    def get_commission_summary(self):
        """전체 수수료 요약 통계"""
        
        queryset = CommissionFact.objects.filter(
            date_key__gte=self.start_date,
            date_key__lte=self.end_date
        )
        
        stats = queryset.aggregate(
            total_commission=Sum('total_commission'),
            total_base_commission=Sum('base_commission'),
            total_grade_bonus=Sum('grade_bonus'),
            total_orders=Count('id'),
            avg_commission=Avg('total_commission'),
            paid_commission=Sum(
                'total_commission',
                filter=Q(payment_status='paid')
            ),
            pending_commission=Sum(
                'total_commission',
                filter=Q(payment_status='pending')
            ),
            unpaid_commission=Sum(
                'total_commission',
                filter=Q(payment_status='unpaid')
            )
        )
        
        return {
            'period': f'{self.start_date} ~ {self.end_date}',
            'total_commission': stats['total_commission'] or Decimal('0'),
            'total_base_commission': stats['total_base_commission'] or Decimal('0'),
            'total_grade_bonus': stats['total_grade_bonus'] or Decimal('0'),
            'total_orders': stats['total_orders'] or 0,
            'avg_commission': stats['avg_commission'] or Decimal('0'),
            'paid_commission': stats['paid_commission'] or Decimal('0'),
            'pending_commission': stats['pending_commission'] or Decimal('0'),
            'unpaid_commission': stats['unpaid_commission'] or Decimal('0'),
        }
    
    def get_company_ranking(self, limit=10):
        """업체별 수수료 순위"""
        
        rankings = CommissionFact.objects.filter(
            date_key__gte=self.start_date,
            date_key__lte=self.end_date
        ).values(
            'company__name', 
            'company__type'
        ).annotate(
            total_commission=Sum('total_commission'),
            total_orders=Count('id'),
            avg_commission=Avg('total_commission'),
            grade_bonus_total=Sum('grade_bonus')
        ).order_by('-total_commission')[:limit]
        
        return list(rankings)
    
    def get_policy_performance(self, limit=10):
        """정책별 성과 분석"""
        
        performances = CommissionFact.objects.filter(
            date_key__gte=self.start_date,
            date_key__lte=self.end_date
        ).values(
            'policy__title',
            'policy__carrier'
        ).annotate(
            total_commission=Sum('total_commission'),
            total_orders=Count('id'),
            avg_commission=Avg('total_commission'),
            unique_companies=Count('company', distinct=True)
        ).order_by('-total_commission')[:limit]
        
        return list(performances)
    
    def export_to_excel(self, file_path=None):
        """엑셀로 데이터 내보내기"""
        
        try:
            import pandas as pd
            from django.http import HttpResponse
            import io
            
            # 데이터 준비
            data = {
                'summary': self.get_commission_summary(),
                'company_ranking': self.get_company_ranking(20),
                'policy_performance': self.get_policy_performance(20)
            }
            
            # 엑셀 파일 생성
            if file_path:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # 각 시트별로 데이터 저장
                    for sheet_name, sheet_data in data.items():
                        if sheet_name == 'summary':
                            # 요약 데이터는 세로로 배치
                            df = pd.DataFrame([sheet_data]).T
                            df.columns = ['값']
                        else:
                            df = pd.DataFrame(sheet_data)
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                logger.info(f'엑셀 파일 생성 완료: {file_path}')
                return file_path
            else:
                # HttpResponse로 반환 (웹 다운로드용)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for sheet_name, sheet_data in data.items():
                        if sheet_name == 'summary':
                            df = pd.DataFrame([sheet_data]).T
                            df.columns = ['값']
                        else:
                            df = pd.DataFrame(sheet_data)
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                output.seek(0)
                
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="commission_report_{self.start_date}_{self.end_date}.xlsx"'
                
                return response
                
        except ImportError:
            logger.error('pandas 라이브러리가 설치되지 않았습니다.')
            return None
        except Exception as e:
            logger.error(f'엑셀 내보내기 실패: {str(e)}')
            return None


class GradeAnalyzer:
    """그레이드 시스템 분석 클래스"""
    
    def get_grade_achievement_stats(self, period_type='monthly'):
        """그레이드 달성 통계"""
        
        trackings = CommissionGradeTracking.objects.filter(
            period_type=period_type,
            is_active=True
        ).select_related('company', 'policy')
        
        stats = {
            'total_trackings': trackings.count(),
            'by_grade': {},
            'by_company_type': {},
            'achievement_rates': []
        }
        
        for tracking in trackings:
            level = tracking.achieved_grade_level
            company_type = tracking.company.type
            achievement_rate = tracking.calculate_achievement_rate()
            
            # 그레이드별 집계
            if level not in stats['by_grade']:
                stats['by_grade'][level] = 0
            stats['by_grade'][level] += 1
            
            # 업체 타입별 집계
            if company_type not in stats['by_company_type']:
                stats['by_company_type'][company_type] = 0
            stats['by_company_type'][company_type] += 1
            
            # 달성률 수집
            stats['achievement_rates'].append({
                'company': tracking.company.name,
                'policy': tracking.policy.title,
                'achievement_rate': achievement_rate,
                'current_orders': tracking.current_orders,
                'target_orders': tracking.target_orders,
                'grade_level': level
            })
        
        return stats
    
    def get_bonus_summary(self):
        """보너스 정산 요약"""
        
        from .models import GradeBonusSettlement
        
        bonus_stats = GradeBonusSettlement.objects.aggregate(
            total_bonus=Sum('bonus_amount'),
            pending_bonus=Sum('bonus_amount', filter=Q(status='pending')),
            approved_bonus=Sum('bonus_amount', filter=Q(status='approved')),
            paid_bonus=Sum('bonus_amount', filter=Q(status='paid')),
            total_settlements=Count('id')
        )
        
        return {
            'total_bonus': bonus_stats['total_bonus'] or Decimal('0'),
            'pending_bonus': bonus_stats['pending_bonus'] or Decimal('0'),
            'approved_bonus': bonus_stats['approved_bonus'] or Decimal('0'),
            'paid_bonus': bonus_stats['paid_bonus'] or Decimal('0'),
            'total_settlements': bonus_stats['total_settlements'] or 0
        }


class DataWarehouseManager:
    """데이터 웨어하우스 관리 클래스"""
    
    @classmethod
    def rebuild_facts_for_date_range(cls, start_date, end_date):
        """특정 기간의 팩트 데이터 재구축"""
        
        logger.info(f'팩트 데이터 재구축 시작: {start_date} ~ {end_date}')
        
        # 기존 데이터 삭제
        deleted_count = CommissionFact.objects.filter(
            date_key__gte=start_date,
            date_key__lte=end_date
        ).delete()[0]
        
        logger.info(f'기존 팩트 데이터 삭제: {deleted_count}건')
        
        # 해당 기간의 정산들로 팩트 데이터 재생성
        settlements = Settlement.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=['approved', 'paid', 'unpaid']
        ).select_related('company', 'order', 'order__policy')
        
        created_count = 0
        for settlement in settlements:
            try:
                CommissionFact.create_from_settlement(settlement)
                created_count += 1
            except Exception as e:
                logger.error(f'팩트 생성 실패: {settlement.id} - {str(e)}')
        
        logger.info(f'팩트 데이터 재구축 완료: {created_count}건 생성')
        return created_count
    
    @classmethod
    def sync_settlement_status(cls):
        """정산 상태와 팩트 테이블 동기화"""
        
        logger.info('정산 상태 동기화 시작')
        
        # 모든 팩트 레코드에 대해 정산 상태 확인
        facts = CommissionFact.objects.select_related('order', 'company')
        updated_count = 0
        
        for fact in facts:
            try:
                settlement = Settlement.objects.get(
                    order=fact.order,
                    company=fact.company
                )
                
                # 상태 불일치 시 업데이트
                if (fact.settlement_status != settlement.status or 
                    fact.payment_status != cls._get_payment_status(settlement.status)):
                    
                    fact.settlement_status = settlement.status
                    fact.payment_status = cls._get_payment_status(settlement.status)
                    fact.save()
                    updated_count += 1
                    
            except Settlement.DoesNotExist:
                logger.warning(f'정산 없음: Order {fact.order.id}, Company {fact.company.id}')
                continue
            except Exception as e:
                logger.error(f'상태 동기화 실패: {fact.id} - {str(e)}')
        
        logger.info(f'정산 상태 동기화 완료: {updated_count}건 업데이트')
        return updated_count
    
    @classmethod
    def _get_payment_status(cls, settlement_status):
        """정산 상태를 결제 상태로 변환"""
        if settlement_status == 'paid':
            return 'paid'
        elif settlement_status == 'unpaid':
            return 'unpaid'
        else:
            return 'pending'

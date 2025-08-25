"""
Phase 6: 사용자별 맞춤 엑셀 내보내기 시스템
회사 유형별 특화된 엑셀 템플릿 및 대용량 데이터 처리
"""

import logging
import io
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import xlsxwriter
from django.http import HttpResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from companies.models import Company, CompanyUser
from .models import Settlement, CommissionGradeTracking
from .filters import DynamicSettlementFilter

logger = logging.getLogger(__name__)


class SettlementExcelExporter:
    """
    정산 데이터 엑셀 내보내기 메인 클래스
    사용자 유형별 맞춤 템플릿 제공
    """
    
    def __init__(self, user, filters: Dict[str, Any] = None):
        """
        엑셀 내보내기 초기화
        
        Args:
            user: 현재 사용자
            filters: 동적 필터 조건
        """
        self.user = user
        self.filters = filters or {}
        self.company_user = self._get_company_user()
        self.user_company = self.company_user.company if self.company_user else None
        self.user_company_type = self.user_company.type if self.user_company else None
        
        # 동적 필터 적용
        self.dynamic_filter = DynamicSettlementFilter(user)
        self.queryset = self.dynamic_filter.apply_multiple_filters(self.filters)
        
    def _get_company_user(self):
        """사용자의 회사 정보 조회"""
        try:
            return CompanyUser.objects.get(django_user=self.user)
        except CompanyUser.DoesNotExist:
            return None
    
    def export_for_user_type(self) -> HttpResponse:
        """
        사용자 유형에 따른 맞춤 엑셀 내보내기
        
        Returns:
            HttpResponse: 엑셀 파일 응답
        """
        if self.user.is_superuser or self.user_company_type == 'headquarters':
            return self.export_for_headquarters()
        elif self.user_company_type == 'agency':
            return self.export_for_agency()
        elif self.user_company_type == 'retail':
            return self.export_for_retail()
        else:
            raise ValueError("유효하지 않은 사용자 유형입니다.")
    
    def export_for_headquarters(self) -> HttpResponse:
        """본사용 엑셀 내보내기 - 전체 정산 현황"""
        exporter = HeadquartersExcelExporter(self.user, self.filters)
        return exporter.generate_excel()
    
    def export_for_agency(self) -> HttpResponse:
        """협력사용 엑셀 내보내기 - 받을/지급할 리베이트"""
        exporter = AgencyExcelExporter(self.user, self.filters)
        return exporter.generate_excel()
    
    def export_for_retail(self) -> HttpResponse:
        """판매점용 엑셀 내보내기 - 받을 리베이트만"""
        exporter = RetailExcelExporter(self.user, self.filters)
        return exporter.generate_excel()


class BaseExcelExporter:
    """엑셀 내보내기 기본 클래스"""
    
    def __init__(self, user, filters: Dict[str, Any] = None):
        self.user = user
        self.filters = filters or {}
        self.dynamic_filter = DynamicSettlementFilter(user)
        self.queryset = self.dynamic_filter.apply_multiple_filters(self.filters)
        
        # 엑셀 스타일 정의
        self.styles = {}
        
    def _create_workbook(self) -> tuple:
        """워크북 및 기본 스타일 생성"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # 스타일 정의
        self.styles = {
            'header': workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            }),
            'subheader': workbook.add_format({
                'bold': True,
                'bg_color': '#D9E2F3',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0',
                'border': 1,
                'align': 'right'
            }),
            'date': workbook.add_format({
                'num_format': 'yyyy-mm-dd',
                'border': 1,
                'align': 'center'
            }),
            'center': workbook.add_format({
                'border': 1,
                'align': 'center'
            }),
            'left': workbook.add_format({
                'border': 1,
                'align': 'left'
            }),
            'total': workbook.add_format({
                'bold': True,
                'bg_color': '#FFF2CC',
                'num_format': '#,##0',
                'border': 1,
                'align': 'right'
            })
        }
        
        return workbook, output
    
    def _write_summary_info(self, worksheet, start_row: int = 0) -> int:
        """요약 정보 작성"""
        current_row = start_row
        
        # 제목
        worksheet.merge_range(current_row, 0, current_row, 7, 
                            f'{self.get_report_title()}', self.styles['header'])
        current_row += 1
        
        # 생성 정보
        worksheet.write(current_row, 0, '생성일시:', self.styles['subheader'])
        worksheet.write(current_row, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.styles['left'])
        current_row += 1
        
        worksheet.write(current_row, 0, '생성자:', self.styles['subheader'])
        worksheet.write(current_row, 1, self.user.username, self.styles['left'])
        current_row += 1
        
        # 필터 정보
        if self.filters:
            worksheet.write(current_row, 0, '적용 필터:', self.styles['subheader'])
            filter_text = self._format_filter_text()
            worksheet.write(current_row, 1, filter_text, self.styles['left'])
            current_row += 1
        
        current_row += 1  # 빈 줄
        return current_row
    
    def _format_filter_text(self) -> str:
        """필터 조건을 텍스트로 포맷팅"""
        filter_parts = []
        
        if 'period_type' in self.filters:
            filter_parts.append(f"기간: {self.filters['period_type']}")
        
        if 'start_date' in self.filters and 'end_date' in self.filters:
            filter_parts.append(f"날짜: {self.filters['start_date']} ~ {self.filters['end_date']}")
        
        if 'statuses' in self.filters:
            filter_parts.append(f"상태: {', '.join(self.filters['statuses'])}")
        
        if 'company_types' in self.filters:
            filter_parts.append(f"회사유형: {', '.join(self.filters['company_types'])}")
        
        return ' | '.join(filter_parts) if filter_parts else '전체'
    
    def _write_summary_statistics(self, worksheet, start_row: int) -> int:
        """요약 통계 작성"""
        current_row = start_row
        
        # 통계 계산
        stats = self.queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_grade_bonus=Sum('grade_bonus')
        )
        
        # 요약 테이블 헤더
        worksheet.merge_range(current_row, 0, current_row, 3, '요약 통계', self.styles['header'])
        current_row += 1
        
        # 통계 데이터
        summary_data = [
            ('총 정산 건수', stats['total_count'] or 0, '건'),
            ('총 정산 금액', stats['total_amount'] or 0, '원'),
            ('평균 정산 금액', stats['avg_amount'] or 0, '원'),
            ('총 그레이드 보너스', stats['total_grade_bonus'] or 0, '원')
        ]
        
        for label, value, unit in summary_data:
            worksheet.write(current_row, 0, label, self.styles['subheader'])
            if '금액' in label:
                worksheet.write(current_row, 1, float(value), self.styles['currency'])
            else:
                worksheet.write(current_row, 1, value, self.styles['center'])
            worksheet.write(current_row, 2, unit, self.styles['center'])
            current_row += 1
        
        current_row += 1  # 빈 줄
        return current_row
    
    def _set_column_widths(self, worksheet, columns: List[tuple]):
        """컬럼 너비 설정"""
        for col_index, width in columns:
            worksheet.set_column(col_index, col_index, width)
    
    def get_report_title(self) -> str:
        """리포트 제목 반환 (하위 클래스에서 구현)"""
        return "정산 리포트"
    
    def generate_excel(self) -> HttpResponse:
        """엑셀 파일 생성 (하위 클래스에서 구현)"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다.")


class HeadquartersExcelExporter(BaseExcelExporter):
    """본사용 엑셀 내보내기"""
    
    def get_report_title(self) -> str:
        return "본사 전체 정산 현황 리포트"
    
    def generate_excel(self) -> HttpResponse:
        """본사용 엑셀 파일 생성"""
        workbook, output = self._create_workbook()
        
        # 메인 시트 - 전체 정산 현황
        main_sheet = workbook.add_worksheet('전체 정산 현황')
        current_row = self._write_main_sheet(main_sheet)
        
        # 회사별 요약 시트
        company_sheet = workbook.add_worksheet('회사별 요약')
        self._write_company_summary_sheet(company_sheet)
        
        # 정책별 요약 시트
        policy_sheet = workbook.add_worksheet('정책별 요약')
        self._write_policy_summary_sheet(policy_sheet)
        
        # 상태별 요약 시트
        status_sheet = workbook.add_worksheet('상태별 요약')
        self._write_status_summary_sheet(status_sheet)
        
        workbook.close()
        output.seek(0)
        
        # HTTP 응답 생성
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'본사_정산현황_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _write_main_sheet(self, worksheet) -> int:
        """메인 시트 작성"""
        current_row = 0
        
        # 요약 정보
        current_row = self._write_summary_info(worksheet, current_row)
        
        # 요약 통계
        current_row = self._write_summary_statistics(worksheet, current_row)
        
        # 상세 데이터 헤더
        headers = [
            '정산ID', '생성일', '회사명', '회사유형', '고객명', 
            '정책명', '통신사', '정산금액', '그레이드보너스', '총금액', 
            '상태', '승인자', '승인일', '메모'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 상세 데이터
        settlements = self.queryset.select_related(
            'order', 'order__policy', 'company', 'approved_by'
        ).order_by('-created_at')
        
        for settlement in settlements:
            row_data = [
                str(settlement.id)[:8] + '...',  # ID 축약
                settlement.created_at.strftime('%Y-%m-%d'),
                settlement.company.name,
                settlement.company.get_type_display(),
                settlement.order.customer_name,
                settlement.order.policy.title,
                settlement.order.policy.carrier,
                float(settlement.rebate_amount),
                float(settlement.grade_bonus or 0),
                float(settlement.rebate_amount + (settlement.grade_bonus or 0)),
                settlement.get_status_display(),
                settlement.approved_by.username if settlement.approved_by else '',
                settlement.approved_at.strftime('%Y-%m-%d') if settlement.approved_at else '',
                settlement.notes or ''
            ]
            
            for col, value in enumerate(row_data):
                if col in [7, 8, 9]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [1, 12]:  # 날짜 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 12), (1, 12), (2, 15), (3, 10), (4, 15),
            (5, 25), (6, 8), (7, 12), (8, 12), (9, 12),
            (10, 10), (11, 12), (12, 12), (13, 20)
        ]
        self._set_column_widths(worksheet, column_widths)
        
        return current_row
    
    def _write_company_summary_sheet(self, worksheet):
        """회사별 요약 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 5, '회사별 정산 요약', self.styles['header'])
        current_row = 2
        
        # 헤더
        headers = ['회사명', '회사유형', '정산건수', '총정산금액', '평균정산금액', '그레이드보너스']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 회사별 집계
        company_stats = self.queryset.values(
            'company__name', 'company__type'
        ).annotate(
            count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_bonus=Sum('grade_bonus')
        ).order_by('-total_amount')
        
        for stat in company_stats:
            row_data = [
                stat['company__name'],
                dict(Company.TYPE_CHOICES).get(stat['company__type'], stat['company__type']),
                stat['count'],
                float(stat['total_amount'] or 0),
                float(stat['avg_amount'] or 0),
                float(stat['total_bonus'] or 0)
            ]
            
            for col, value in enumerate(row_data):
                if col in [3, 4, 5]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col == 2:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 20), (1, 12), (2, 10), (3, 15), (4, 15), (5, 15)]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_policy_summary_sheet(self, worksheet):
        """정책별 요약 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 5, '정책별 정산 요약', self.styles['header'])
        current_row = 2
        
        # 헤더
        headers = ['정책명', '통신사', '정산건수', '총정산금액', '평균정산금액', '그레이드보너스']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 정책별 집계
        policy_stats = self.queryset.values(
            'order__policy__title', 'order__policy__carrier'
        ).annotate(
            count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_bonus=Sum('grade_bonus')
        ).order_by('-total_amount')
        
        for stat in policy_stats:
            row_data = [
                stat['order__policy__title'],
                stat['order__policy__carrier'],
                stat['count'],
                float(stat['total_amount'] or 0),
                float(stat['avg_amount'] or 0),
                float(stat['total_bonus'] or 0)
            ]
            
            for col, value in enumerate(row_data):
                if col in [3, 4, 5]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col == 2:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 25), (1, 10), (2, 10), (3, 15), (4, 15), (5, 15)]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_status_summary_sheet(self, worksheet):
        """상태별 요약 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 3, '상태별 정산 요약', self.styles['header'])
        current_row = 2
        
        # 헤더
        headers = ['정산상태', '정산건수', '총정산금액', '평균정산금액']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 상태별 집계
        status_stats = self.queryset.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount')
        ).order_by('-total_amount')
        
        status_choices = dict(Settlement.STATUS_CHOICES)
        
        for stat in status_stats:
            row_data = [
                status_choices.get(stat['status'], stat['status']),
                stat['count'],
                float(stat['total_amount'] or 0),
                float(stat['avg_amount'] or 0)
            ]
            
            for col, value in enumerate(row_data):
                if col in [2, 3]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col == 1:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 15), (1, 10), (2, 15), (3, 15)]
        self._set_column_widths(worksheet, column_widths)


class AgencyExcelExporter(BaseExcelExporter):
    """협력사용 엑셀 내보내기 - 받을/지급할 리베이트"""
    
    def get_report_title(self) -> str:
        return "협력사 리베이트 현황 리포트"
    
    def generate_excel(self) -> HttpResponse:
        """협력사용 엑셀 파일 생성"""
        workbook, output = self._create_workbook()
        
        # 받을 리베이트 시트
        receivable_sheet = workbook.add_worksheet('받을 리베이트')
        self._write_receivable_sheet(receivable_sheet)
        
        # 지급할 리베이트 시트 (하위 판매점)
        payable_sheet = workbook.add_worksheet('지급할 리베이트')
        self._write_payable_sheet(payable_sheet)
        
        # 그레이드 달성 현황 시트
        grade_sheet = workbook.add_worksheet('그레이드 현황')
        self._write_grade_status_sheet(grade_sheet)
        
        # 판매점별 성과 시트
        performance_sheet = workbook.add_worksheet('판매점별 성과')
        self._write_subordinate_performance_sheet(performance_sheet)
        
        workbook.close()
        output.seek(0)
        
        # HTTP 응답 생성
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'협력사_리베이트현황_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _write_receivable_sheet(self, worksheet):
        """받을 리베이트 시트 작성"""
        current_row = 0
        
        # 요약 정보
        current_row = self._write_summary_info(worksheet, current_row)
        
        # 자신의 정산만 필터링
        company_user = CompanyUser.objects.get(django_user=self.user)
        own_settlements = self.queryset.filter(company=company_user.company)
        
        # 받을 리베이트 요약 통계
        own_stats = own_settlements.aggregate(
            total_count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_grade_bonus=Sum('grade_bonus')
        )
        
        # 요약 테이블
        worksheet.merge_range(current_row, 0, current_row, 3, '받을 리베이트 요약', self.styles['header'])
        current_row += 1
        
        summary_data = [
            ('총 정산 건수', own_stats['total_count'] or 0, '건'),
            ('총 받을 금액', own_stats['total_amount'] or 0, '원'),
            ('평균 정산 금액', own_stats['avg_amount'] or 0, '원'),
            ('총 그레이드 보너스', own_stats['total_grade_bonus'] or 0, '원')
        ]
        
        for label, value, unit in summary_data:
            worksheet.write(current_row, 0, label, self.styles['subheader'])
            if '금액' in label:
                worksheet.write(current_row, 1, float(value), self.styles['currency'])
            else:
                worksheet.write(current_row, 1, value, self.styles['center'])
            worksheet.write(current_row, 2, unit, self.styles['center'])
            current_row += 1
        
        current_row += 1
        
        # 상세 데이터 헤더
        headers = [
            '정산ID', '생성일', '고객명', '정책명', '통신사', 
            '정산금액', '그레이드보너스', '총금액', '상태', '승인일', '메모'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 상세 데이터
        for settlement in own_settlements.order_by('-created_at'):
            row_data = [
                str(settlement.id)[:8] + '...',
                settlement.created_at.strftime('%Y-%m-%d'),
                settlement.order.customer_name,
                settlement.order.policy.title,
                settlement.order.policy.carrier,
                float(settlement.rebate_amount),
                float(settlement.grade_bonus or 0),
                float(settlement.rebate_amount + (settlement.grade_bonus or 0)),
                settlement.get_status_display(),
                settlement.approved_at.strftime('%Y-%m-%d') if settlement.approved_at else '',
                settlement.notes or ''
            ]
            
            for col, value in enumerate(row_data):
                if col in [5, 6, 7]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [1, 9]:  # 날짜 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 12), (1, 12), (2, 15), (3, 25), (4, 8),
            (5, 12), (6, 12), (7, 12), (8, 10), (9, 12), (10, 20)
        ]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_payable_sheet(self, worksheet):
        """지급할 리베이트 시트 작성 (하위 판매점)"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 7, '하위 판매점 지급할 리베이트', self.styles['header'])
        current_row = 2
        
        # 하위 판매점 정산만 필터링
        company_user = CompanyUser.objects.get(django_user=self.user)
        subordinate_settlements = self.queryset.filter(
            company__parent_company=company_user.company
        )
        
        # 지급할 리베이트 요약 통계
        payable_stats = subordinate_settlements.aggregate(
            total_count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount')
        )
        
        # 요약 정보
        worksheet.write(current_row, 0, '총 지급 건수:', self.styles['subheader'])
        worksheet.write(current_row, 1, payable_stats['total_count'] or 0, self.styles['center'])
        current_row += 1
        
        worksheet.write(current_row, 0, '총 지급 금액:', self.styles['subheader'])
        worksheet.write(current_row, 1, float(payable_stats['total_amount'] or 0), self.styles['currency'])
        current_row += 1
        
        current_row += 1
        
        # 판매점별 요약
        worksheet.merge_range(current_row, 0, current_row, 5, '판매점별 지급 요약', self.styles['header'])
        current_row += 1
        
        headers = ['판매점명', '정산건수', '총지급금액', '평균금액', '미지급건수', '미지급금액']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 판매점별 집계
        retail_stats = subordinate_settlements.values('company__name').annotate(
            total_count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            unpaid_count=Count('id', filter=Q(status__in=['pending', 'approved'])),
            unpaid_amount=Sum('rebate_amount', filter=Q(status__in=['pending', 'approved']))
        ).order_by('-total_amount')
        
        for stat in retail_stats:
            row_data = [
                stat['company__name'],
                stat['total_count'],
                float(stat['total_amount'] or 0),
                float(stat['avg_amount'] or 0),
                stat['unpaid_count'] or 0,
                float(stat['unpaid_amount'] or 0)
            ]
            
            for col, value in enumerate(row_data):
                if col in [2, 3, 5]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [1, 4]:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 20), (1, 10), (2, 15), (3, 12), (4, 12), (5, 15)]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_grade_status_sheet(self, worksheet):
        """그레이드 달성 현황 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 7, '그레이드 달성 현황', self.styles['header'])
        current_row = 2
        
        # 그레이드 추적 정보 조회
        company_user = CompanyUser.objects.get(django_user=self.user)
        grade_trackings = CommissionGradeTracking.objects.filter(
            company=company_user.company,
            is_active=True
        ).select_related('policy')
        
        if not grade_trackings.exists():
            worksheet.write(current_row, 0, '활성화된 그레이드 추적이 없습니다.', self.styles['center'])
            return
        
        # 헤더
        headers = [
            '정책명', '기간유형', '시작일', '종료일', '목표건수', 
            '현재건수', '달성률', '보너스단가', '예상보너스'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 그레이드 데이터
        for tracking in grade_trackings:
            achievement_rate = (tracking.current_orders / tracking.target_orders * 100) if tracking.target_orders > 0 else 0
            expected_bonus = tracking.bonus_per_order * max(0, tracking.target_orders - tracking.current_orders)
            
            row_data = [
                tracking.policy.title,
                tracking.get_period_type_display(),
                tracking.period_start.strftime('%Y-%m-%d'),
                tracking.period_end.strftime('%Y-%m-%d'),
                tracking.target_orders,
                tracking.current_orders,
                f'{achievement_rate:.1f}%',
                float(tracking.bonus_per_order),
                float(expected_bonus)
            ]
            
            for col, value in enumerate(row_data):
                if col in [7, 8]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [2, 3]:  # 날짜 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                elif col in [4, 5]:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 25), (1, 10), (2, 12), (3, 12), (4, 10),
            (5, 10), (6, 10), (7, 12), (8, 12)
        ]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_subordinate_performance_sheet(self, worksheet):
        """판매점별 성과 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 6, '판매점별 성과 분석', self.styles['header'])
        current_row = 2
        
        # 하위 판매점 성과 분석
        company_user = CompanyUser.objects.get(django_user=self.user)
        subordinate_companies = Company.objects.filter(parent_company=company_user.company)
        
        if not subordinate_companies.exists():
            worksheet.write(current_row, 0, '하위 판매점이 없습니다.', self.styles['center'])
            return
        
        # 헤더
        headers = ['판매점명', '이번달 건수', '이번달 금액', '지난달 건수', '지난달 금액', '성장률', '순위']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 이번달/지난달 기간 설정
        now = timezone.now()
        this_month_start = now.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        
        performance_data = []
        
        for company in subordinate_companies:
            # 이번달 데이터
            this_month_stats = Settlement.objects.filter(
                company=company,
                created_at__gte=this_month_start
            ).aggregate(
                count=Count('id'),
                amount=Sum('rebate_amount')
            )
            
            # 지난달 데이터
            last_month_stats = Settlement.objects.filter(
                company=company,
                created_at__gte=last_month_start,
                created_at__lte=last_month_end
            ).aggregate(
                count=Count('id'),
                amount=Sum('rebate_amount')
            )
            
            # 성장률 계산
            this_amount = float(this_month_stats['amount'] or 0)
            last_amount = float(last_month_stats['amount'] or 0)
            growth_rate = ((this_amount - last_amount) / last_amount * 100) if last_amount > 0 else 0
            
            performance_data.append({
                'name': company.name,
                'this_count': this_month_stats['count'] or 0,
                'this_amount': this_amount,
                'last_count': last_month_stats['count'] or 0,
                'last_amount': last_amount,
                'growth_rate': growth_rate
            })
        
        # 이번달 금액 기준으로 정렬
        performance_data.sort(key=lambda x: x['this_amount'], reverse=True)
        
        # 데이터 작성
        for rank, data in enumerate(performance_data, 1):
            row_data = [
                data['name'],
                data['this_count'],
                data['this_amount'],
                data['last_count'],
                data['last_amount'],
                f"{data['growth_rate']:+.1f}%",
                rank
            ]
            
            for col, value in enumerate(row_data):
                if col in [2, 4]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [1, 3, 6]:  # 건수/순위 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 20), (1, 12), (2, 15), (3, 12), (4, 15), (5, 10), (6, 8)]
        self._set_column_widths(worksheet, column_widths)


class RetailExcelExporter(BaseExcelExporter):
    """판매점용 엑셀 내보내기 - 받을 리베이트만"""
    
    def get_report_title(self) -> str:
        return "판매점 리베이트 현황 리포트"
    
    def generate_excel(self) -> HttpResponse:
        """판매점용 엑셀 파일 생성"""
        workbook, output = self._create_workbook()
        
        # 메인 시트 - 받을 리베이트
        main_sheet = workbook.add_worksheet('받을 리베이트')
        self._write_main_sheet(main_sheet)
        
        # 월별 성과 시트
        monthly_sheet = workbook.add_worksheet('월별 성과')
        self._write_monthly_performance_sheet(monthly_sheet)
        
        # 정책별 성과 시트
        policy_sheet = workbook.add_worksheet('정책별 성과')
        self._write_policy_performance_sheet(policy_sheet)
        
        # 그레이드 현황 시트
        grade_sheet = workbook.add_worksheet('그레이드 현황')
        self._write_grade_achievement_sheet(grade_sheet)
        
        workbook.close()
        output.seek(0)
        
        # HTTP 응답 생성
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        filename = f'판매점_리베이트현황_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _write_main_sheet(self, worksheet):
        """메인 시트 작성"""
        current_row = 0
        
        # 요약 정보
        current_row = self._write_summary_info(worksheet, current_row)
        
        # 요약 통계
        current_row = self._write_summary_statistics(worksheet, current_row)
        
        # 상세 데이터 헤더
        headers = [
            '정산ID', '생성일', '고객명', '정책명', '통신사', 
            '정산금액', '그레이드보너스', '총금액', '상태', '승인일', 
            '지급예정일', '메모'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 상세 데이터
        settlements = self.queryset.select_related(
            'order', 'order__policy'
        ).order_by('-created_at')
        
        for settlement in settlements:
            row_data = [
                str(settlement.id)[:8] + '...',
                settlement.created_at.strftime('%Y-%m-%d'),
                settlement.order.customer_name,
                settlement.order.policy.title,
                settlement.order.policy.carrier,
                float(settlement.rebate_amount),
                float(settlement.grade_bonus or 0),
                float(settlement.rebate_amount + (settlement.grade_bonus or 0)),
                settlement.get_status_display(),
                settlement.approved_at.strftime('%Y-%m-%d') if settlement.approved_at else '',
                settlement.expected_payment_date.strftime('%Y-%m-%d') if settlement.expected_payment_date else '',
                settlement.notes or ''
            ]
            
            for col, value in enumerate(row_data):
                if col in [5, 6, 7]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [1, 9, 10]:  # 날짜 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 12), (1, 12), (2, 15), (3, 25), (4, 8),
            (5, 12), (6, 12), (7, 12), (8, 10), (9, 12),
            (10, 12), (11, 20)
        ]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_monthly_performance_sheet(self, worksheet):
        """월별 성과 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 4, '월별 성과 분석', self.styles['header'])
        current_row = 2
        
        # 헤더
        headers = ['월', '정산건수', '총정산금액', '평균정산금액', '그레이드보너스']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 최근 12개월 데이터
        monthly_stats = []
        for i in range(12):
            target_date = timezone.now() - timedelta(days=30 * i)
            month_start = target_date.replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            
            stats = self.queryset.filter(
                created_at__gte=month_start,
                created_at__lt=next_month
            ).aggregate(
                count=Count('id'),
                total_amount=Sum('rebate_amount'),
                avg_amount=Avg('rebate_amount'),
                total_bonus=Sum('grade_bonus')
            )
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'count': stats['count'] or 0,
                'total_amount': float(stats['total_amount'] or 0),
                'avg_amount': float(stats['avg_amount'] or 0),
                'total_bonus': float(stats['total_bonus'] or 0)
            })
        
        # 최신 월부터 정렬
        monthly_stats.reverse()
        
        # 데이터 작성
        for stat in monthly_stats:
            if stat['count'] > 0:  # 데이터가 있는 월만 표시
                row_data = [
                    stat['month'],
                    stat['count'],
                    stat['total_amount'],
                    stat['avg_amount'],
                    stat['total_bonus']
                ]
                
                for col, value in enumerate(row_data):
                    if col in [2, 3, 4]:  # 금액 컬럼
                        worksheet.write(current_row, col, value, self.styles['currency'])
                    elif col == 1:  # 건수 컬럼
                        worksheet.write(current_row, col, value, self.styles['center'])
                    else:
                        worksheet.write(current_row, col, value, self.styles['center'])
                
                current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 10), (1, 10), (2, 15), (3, 15), (4, 15)]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_policy_performance_sheet(self, worksheet):
        """정책별 성과 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 5, '정책별 성과 분석', self.styles['header'])
        current_row = 2
        
        # 헤더
        headers = ['정책명', '통신사', '정산건수', '총정산금액', '평균정산금액', '그레이드보너스']
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 정책별 집계
        policy_stats = self.queryset.values(
            'order__policy__title', 'order__policy__carrier'
        ).annotate(
            count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_bonus=Sum('grade_bonus')
        ).order_by('-total_amount')
        
        for stat in policy_stats:
            row_data = [
                stat['order__policy__title'],
                stat['order__policy__carrier'],
                stat['count'],
                float(stat['total_amount'] or 0),
                float(stat['avg_amount'] or 0),
                float(stat['total_bonus'] or 0)
            ]
            
            for col, value in enumerate(row_data):
                if col in [3, 4, 5]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col == 2:  # 건수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [(0, 25), (1, 10), (2, 10), (3, 15), (4, 15), (5, 15)]
        self._set_column_widths(worksheet, column_widths)
    
    def _write_grade_achievement_sheet(self, worksheet):
        """그레이드 달성 현황 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 8, '그레이드 달성 현황', self.styles['header'])
        current_row = 2
        
        # 그레이드 추적 정보 조회
        company_user = CompanyUser.objects.get(django_user=self.user)
        grade_trackings = CommissionGradeTracking.objects.filter(
            company=company_user.company,
            is_active=True
        ).select_related('policy')
        
        if not grade_trackings.exists():
            worksheet.write(current_row, 0, '활성화된 그레이드 추적이 없습니다.', self.styles['center'])
            return
        
        # 헤더
        headers = [
            '정책명', '기간유형', '시작일', '종료일', '목표건수', 
            '현재건수', '달성률', '보너스단가', '달성보너스', '남은일수'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, self.styles['header'])
        current_row += 1
        
        # 그레이드 데이터
        for tracking in grade_trackings:
            achievement_rate = (tracking.current_orders / tracking.target_orders * 100) if tracking.target_orders > 0 else 0
            achieved_bonus = tracking.bonus_per_order * tracking.current_orders
            remaining_days = (tracking.period_end - timezone.now().date()).days
            
            row_data = [
                tracking.policy.title,
                tracking.get_period_type_display(),
                tracking.period_start.strftime('%Y-%m-%d'),
                tracking.period_end.strftime('%Y-%m-%d'),
                tracking.target_orders,
                tracking.current_orders,
                f'{achievement_rate:.1f}%',
                float(tracking.bonus_per_order),
                float(achieved_bonus),
                max(0, remaining_days)
            ]
            
            for col, value in enumerate(row_data):
                if col in [7, 8]:  # 금액 컬럼
                    worksheet.write(current_row, col, value, self.styles['currency'])
                elif col in [2, 3]:  # 날짜 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                elif col in [4, 5, 9]:  # 건수/일수 컬럼
                    worksheet.write(current_row, col, value, self.styles['center'])
                else:
                    worksheet.write(current_row, col, value, self.styles['left'])
            
            current_row += 1
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 25), (1, 10), (2, 12), (3, 12), (4, 10),
            (5, 10), (6, 10), (7, 12), (8, 12), (9, 10)
        ]
        self._set_column_widths(worksheet, column_widths)


class LargeDatasetExcelExporter:
    """
    대용량 데이터셋 엑셀 내보내기
    청크 단위로 처리하여 메모리 사용량 최적화
    """
    
    def __init__(self, user, filters: Dict[str, Any] = None, 
                 chunk_size: int = 1000, max_records: int = 10000):
        """
        대용량 데이터 내보내기 초기화
        
        Args:
            user: 현재 사용자
            filters: 동적 필터 조건
            chunk_size: 청크 크기 (기본 1000건)
            max_records: 최대 레코드 수 (기본 10000건)
        """
        self.user = user
        self.filters = filters or {}
        self.chunk_size = chunk_size
        self.max_records = max_records
        
        # 동적 필터 적용
        self.dynamic_filter = DynamicSettlementFilter(user)
        self.base_queryset = self.dynamic_filter.apply_multiple_filters(self.filters)
        
        # 총 레코드 수 확인
        self.total_count = self.base_queryset.count()
        if self.total_count > self.max_records:
            logger.warning(f"요청된 데이터 수({self.total_count})가 최대 허용치({self.max_records})를 초과합니다.")
            self.total_count = self.max_records
    
    def export(self) -> HttpResponse:
        """대용량 데이터 엑셀 내보내기"""
        try:
            # 메모리 효율적인 엑셀 생성
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {
                'in_memory': True,
                'constant_memory': True,  # 메모리 최적화 모드
                'tmpdir': '/tmp' if hasattr(os, 'name') and os.name != 'nt' else None
            })
            
            # 스타일 정의
            styles = self._create_styles(workbook)
            
            # 메인 데이터 시트
            main_sheet = workbook.add_worksheet('정산 데이터')
            self._write_large_dataset_sheet(main_sheet, styles)
            
            # 요약 시트
            summary_sheet = workbook.add_worksheet('요약 정보')
            self._write_summary_sheet(summary_sheet, styles)
            
            workbook.close()
            output.seek(0)
            
            # HTTP 응답 생성
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            filename = f'대용량_정산데이터_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.error(f"대용량 엑셀 내보내기 실패: {e}")
            raise
    
    def _create_styles(self, workbook):
        """엑셀 스타일 생성"""
        return {
            'header': workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0',
                'border': 1,
                'align': 'right'
            }),
            'date': workbook.add_format({
                'num_format': 'yyyy-mm-dd',
                'border': 1,
                'align': 'center'
            }),
            'center': workbook.add_format({
                'border': 1,
                'align': 'center'
            }),
            'left': workbook.add_format({
                'border': 1,
                'align': 'left'
            })
        }
    
    def _write_large_dataset_sheet(self, worksheet, styles):
        """대용량 데이터 시트 작성"""
        current_row = 0
        
        # 헤더 작성
        headers = [
            '정산ID', '생성일', '회사명', '회사유형', '고객명', 
            '정책명', '통신사', '정산금액', '그레이드보너스', '총금액', 
            '상태', '승인일', '메모'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(current_row, col, header, styles['header'])
        current_row += 1
        
        # 청크 단위로 데이터 처리
        processed_count = 0
        
        for chunk_start in range(0, min(self.total_count, self.max_records), self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, self.total_count, self.max_records)
            
            # 현재 청크 데이터 조회
            chunk_queryset = self.base_queryset.select_related(
                'order', 'order__policy', 'company', 'approved_by'
            )[chunk_start:chunk_end]
            
            # 청크 데이터 작성
            for settlement in chunk_queryset:
                if processed_count >= self.max_records:
                    break
                
                row_data = [
                    str(settlement.id)[:8] + '...',
                    settlement.created_at.strftime('%Y-%m-%d'),
                    settlement.company.name,
                    settlement.company.get_type_display(),
                    settlement.order.customer_name,
                    settlement.order.policy.title,
                    settlement.order.policy.carrier,
                    float(settlement.rebate_amount),
                    float(settlement.grade_bonus or 0),
                    float(settlement.rebate_amount + (settlement.grade_bonus or 0)),
                    settlement.get_status_display(),
                    settlement.approved_at.strftime('%Y-%m-%d') if settlement.approved_at else '',
                    settlement.notes or ''
                ]
                
                for col, value in enumerate(row_data):
                    if col in [7, 8, 9]:  # 금액 컬럼
                        worksheet.write(current_row, col, value, styles['currency'])
                    elif col in [1, 11]:  # 날짜 컬럼
                        worksheet.write(current_row, col, value, styles['center'])
                    else:
                        worksheet.write(current_row, col, value, styles['left'])
                
                current_row += 1
                processed_count += 1
            
            # 메모리 정리
            del chunk_queryset
            
            # 진행 상황 로깅
            logger.info(f"대용량 엑셀 처리 진행: {processed_count}/{min(self.total_count, self.max_records)}")
        
        # 컬럼 너비 설정
        column_widths = [
            (0, 12), (1, 12), (2, 15), (3, 10), (4, 15),
            (5, 25), (6, 8), (7, 12), (8, 12), (9, 12),
            (10, 10), (11, 12), (12, 20)
        ]
        
        for col_index, width in column_widths:
            worksheet.set_column(col_index, col_index, width)
    
    def _write_summary_sheet(self, worksheet, styles):
        """요약 정보 시트 작성"""
        current_row = 0
        
        # 제목
        worksheet.merge_range(0, 0, 0, 3, '대용량 데이터 내보내기 요약', styles['header'])
        current_row = 2
        
        # 기본 정보
        info_data = [
            ('생성일시', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('생성자', self.user.username),
            ('총 데이터 수', f'{self.total_count:,}건'),
            ('내보낸 데이터 수', f'{min(self.total_count, self.max_records):,}건'),
            ('청크 크기', f'{self.chunk_size:,}건'),
            ('최대 허용 레코드', f'{self.max_records:,}건')
        ]
        
        for label, value in info_data:
            worksheet.write(current_row, 0, label, styles['header'])
            worksheet.write(current_row, 1, value, styles['left'])
            current_row += 1
        
        current_row += 1
        
        # 필터 정보
        if self.filters:
            worksheet.write(current_row, 0, '적용된 필터:', styles['header'])
            current_row += 1
            
            for key, value in self.filters.items():
                if value:
                    worksheet.write(current_row, 0, f'  {key}', styles['left'])
                    worksheet.write(current_row, 1, str(value), styles['left'])
                    current_row += 1
        
        current_row += 1
        
        # 통계 정보 (샘플링 기반)
        sample_size = min(1000, self.total_count)
        sample_queryset = self.base_queryset[:sample_size]
        
        stats = sample_queryset.aggregate(
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_bonus=Sum('grade_bonus')
        )
        
        worksheet.write(current_row, 0, '통계 정보 (샘플 기반):', styles['header'])
        current_row += 1
        
        stats_data = [
            ('샘플 크기', f'{sample_size:,}건'),
            ('평균 정산 금액', f'{float(stats["avg_amount"] or 0):,.0f}원'),
            ('샘플 총 정산 금액', f'{float(stats["total_amount"] or 0):,.0f}원'),
            ('샘플 총 보너스', f'{float(stats["total_bonus"] or 0):,.0f}원')
        ]
        
        for label, value in stats_data:
            worksheet.write(current_row, 0, f'  {label}', styles['left'])
            worksheet.write(current_row, 1, value, styles['left'])
            current_row += 1
        
        # 컬럼 너비 설정
        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 1, 25)


class ExcelExportManager:
    """
    엑셀 내보내기 관리자
    다양한 내보내기 옵션을 통합 관리
    """
    
    @staticmethod
    def get_optimal_exporter(user, filters: Dict[str, Any], record_count: int):
        """
        데이터 크기에 따른 최적 내보내기 방식 선택
        
        Args:
            user: 사용자
            filters: 필터 조건
            record_count: 레코드 수
            
        Returns:
            적절한 엑셀 내보내기 객체
        """
        if record_count <= 5000:
            # 일반 내보내기
            return SettlementExcelExporter(user, filters)
        else:
            # 대용량 내보내기
            return LargeDatasetExcelExporter(
                user, 
                filters,
                chunk_size=1000,
                max_records=min(record_count, 50000)  # 최대 5만건
            )
    
    @staticmethod
    def estimate_export_feasibility(record_count: int) -> Dict[str, Any]:
        """
        내보내기 가능성 평가
        
        Args:
            record_count: 레코드 수
            
        Returns:
            가능성 평가 결과
        """
        if record_count <= 1000:
            return {
                'feasible': True,
                'recommendation': 'standard',
                'estimated_time': '10초 이내',
                'estimated_size': f'{record_count}KB',
                'warning': None
            }
        elif record_count <= 10000:
            return {
                'feasible': True,
                'recommendation': 'standard',
                'estimated_time': '1분 이내',
                'estimated_size': f'{record_count // 1000}MB',
                'warning': '데이터가 많아 처리 시간이 소요될 수 있습니다.'
            }
        elif record_count <= 50000:
            return {
                'feasible': True,
                'recommendation': 'large_dataset',
                'estimated_time': '5분 이내',
                'estimated_size': f'{record_count // 1000}MB',
                'warning': '대용량 데이터입니다. 청크 단위로 처리됩니다.'
            }
        else:
            return {
                'feasible': False,
                'recommendation': 'split_request',
                'estimated_time': '10분 이상',
                'estimated_size': f'{record_count // 1000}MB',
                'warning': '데이터가 너무 많습니다. 기간을 나누어 요청해주세요.'
            }

"""
정산 관리 뷰
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
import io
import xlsxwriter
from django.http import HttpResponse

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import HierarchyPermission, CompanyTypePermission
from .models import Settlement, SettlementBatch
from .serializers import (
    SettlementSerializer, SettlementBatchSerializer,
    SettlementStatsSerializer, SettlementCreateSerializer
)

logger = logging.getLogger(__name__)


class SettlementViewSet(viewsets.ModelViewSet):
    """
    정산 관리 ViewSet
    """
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated, HierarchyPermission]
    
    def get_queryset(self):
        """계층 구조에 따른 정산 목록 조회"""
        user = self.request.user
        queryset = Settlement.objects.all()
        
        # 슈퍼유저는 모든 정산 조회 가능
        if user.is_superuser:
            return queryset
        
        # CompanyUser 확인
        if not hasattr(user, 'companyuser'):
            return queryset.none()
        
        company = user.companyuser.company
        
        # 회사 타입에 따른 필터링
        if company.type == 'headquarters':
            # 본사는 모든 정산 조회 가능
            return queryset
        elif company.type == 'agency':
            # 협력사는 자신과 하위 판매점의 정산만 조회
            return queryset.filter(
                Q(company=company) |
                Q(company__parent_company=company)
            )
        else:  # retail
            # 판매점은 자신의 정산만 조회
            return queryset.filter(company=company)
    
    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'create':
            return SettlementCreateSerializer
        elif self.action == 'stats':
            return SettlementStatsSerializer
        return self.serializer_class
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """정산 통계 조회"""
        queryset = self.get_queryset()
        
        # 기간 파라미터
        period = request.query_params.get('period', 'month')
        
        # 기간별 필터링
        now = timezone.now()
        if period == 'day':
            start_date = now - timedelta(days=1)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        # 통계 계산
        stats = queryset.aggregate(
            total_amount=Sum('rebate_amount'),
            total_count=Count('id'),
            pending_count=Count('id', filter=Q(status='pending')),
            approved_count=Count('id', filter=Q(status='approved')),
            paid_count=Count('id', filter=Q(status='paid')),
            cancelled_count=Count('id', filter=Q(status='cancelled'))
        )
        
        # None 값 처리
        stats['total_amount'] = stats['total_amount'] or Decimal('0')
        
        # 평균 계산
        if stats['total_count'] > 0:
            stats['average_amount'] = stats['total_amount'] / stats['total_count']
        else:
            stats['average_amount'] = Decimal('0')
        
        serializer = self.get_serializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CompanyTypePermission])
    def approve(self, request, pk=None):
        """정산 승인 (본사만 가능)"""
        settlement = self.get_object()
        
        try:
            settlement.approve(request.user)
            serializer = self.get_serializer(settlement)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CompanyTypePermission])
    def mark_paid(self, request, pk=None):
        """지급 완료 처리 (본사만 가능)"""
        settlement = self.get_object()
        
        try:
            settlement.mark_as_paid()
            serializer = self.get_serializer(settlement)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """정산 취소"""
        settlement = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            settlement.cancel(reason)
            serializer = self.get_serializer(settlement)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """정산 내역 엑셀 출력 (최대 3개월)"""
        try:
            # 날짜 파라미터 가져오기
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            
            if not start_date_str or not end_date_str:
                return Response(
                    {'error': '시작일과 종료일을 입력해주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 최대 3개월 제한
            if (end_date - start_date).days > 90:
                return Response(
                    {'error': '최대 3개월까지만 조회 가능합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 권한에 따른 정산 데이터 필터링
            queryset = self.get_queryset().filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).select_related('order', 'company', 'order__policy')
            
            # 엑셀 파일 생성
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('정산내역')
            
            # 스타일 정의
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1,
                'align': 'center'
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'center'
            })
            
            amount_format = workbook.add_format({
                'border': 1,
                'align': 'right',
                'num_format': '#,##0'
            })
            
            # 헤더 작성
            headers = [
                '정산일', '주문일', '업체명', '업체타입', '고객명', 
                '정책명', '리베이트금액', '정산상태', '지급예정일', '메모'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # 데이터 작성
            for row, settlement in enumerate(queryset, start=1):
                worksheet.write(row, 0, settlement.created_at.strftime('%Y-%m-%d'), cell_format)
                worksheet.write(row, 1, settlement.order.created_at.strftime('%Y-%m-%d'), cell_format)
                worksheet.write(row, 2, settlement.company.name, cell_format)
                worksheet.write(row, 3, settlement.company.get_company_type_display(), cell_format)
                worksheet.write(row, 4, settlement.order.customer_name, cell_format)
                worksheet.write(row, 5, settlement.order.policy.title, cell_format)
                worksheet.write(row, 6, float(settlement.rebate_amount), amount_format)
                worksheet.write(row, 7, settlement.get_status_display(), cell_format)
                worksheet.write(row, 8, settlement.rebate_due_date.strftime('%Y-%m-%d') if settlement.rebate_due_date else '', cell_format)
                worksheet.write(row, 9, settlement.notes, cell_format)
            
            # 컬럼 너비 조정
            worksheet.set_column('A:A', 12)  # 정산일
            worksheet.set_column('B:B', 12)  # 주문일
            worksheet.set_column('C:C', 20)  # 업체명
            worksheet.set_column('D:D', 12)  # 업체타입
            worksheet.set_column('E:E', 15)  # 고객명
            worksheet.set_column('F:F', 25)  # 정책명
            worksheet.set_column('G:G', 15)  # 리베이트금액
            worksheet.set_column('H:H', 12)  # 정산상태
            worksheet.set_column('I:I', 12)  # 지급예정일
            worksheet.set_column('J:J', 30)  # 메모
            
            workbook.close()
            output.seek(0)
            
            # HTTP 응답 생성
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            filename = f'정산내역_{start_date_str}_{end_date_str}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"정산 엑셀 출력: {request.user.username} - {start_date} ~ {end_date}")
            
            return response
            
        except Exception as e:
            logger.error(f"정산 엑셀 출력 실패: {str(e)}")
            return Response(
                {'error': '엑셀 파일 생성 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SettlementBatchViewSet(viewsets.ModelViewSet):
    """
    정산 배치 관리 ViewSet
    """
    queryset = SettlementBatch.objects.all()
    serializer_class = SettlementBatchSerializer
    permission_classes = [IsAuthenticated, CompanyTypePermission]
    
    def perform_create(self, serializer):
        """배치 생성 시 생성자 자동 설정"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_settlements(self, request, pk=None):
        """배치에 정산 추가"""
        batch = self.get_object()
        settlement_ids = request.data.get('settlement_ids', [])
        
        if not settlement_ids:
            return Response(
                {'error': '추가할 정산 ID를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 권한에 따른 정산 필터링
        user = request.user
        settlements = Settlement.objects.filter(id__in=settlement_ids)
        
        if not user.is_superuser and hasattr(user, 'companyuser'):
            company = user.companyuser.company
            if company.type != 'headquarters':
                return Response(
                    {'error': '본사만 배치를 관리할 수 있습니다.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # 배치에 정산 추가
        added_count = 0
        for settlement in settlements:
            try:
                batch.items.create(settlement=settlement)
                added_count += 1
            except Exception as e:
                logger.error(f"정산 추가 실패: {settlement.id} - {str(e)}")
        
        # 총액 재계산
        batch.calculate_total()
        
        return Response({
            'message': f'{added_count}개의 정산이 배치에 추가되었습니다.',
            'total_amount': batch.total_amount
        })
    
    @action(detail=True, methods=['post'])
    def approve_all(self, request, pk=None):
        """배치의 모든 정산 승인"""
        batch = self.get_object()
        
        try:
            count = batch.approve_all(request.user)
            return Response({
                'message': f'{count}개의 정산이 승인되었습니다.',
                'batch': SettlementBatchSerializer(batch).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
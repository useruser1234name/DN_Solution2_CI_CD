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
from companies.models import Company
from policies.models import Policy
from .models import (
    Settlement, SettlementBatch, 
    CommissionGradeTracking, GradeAchievementHistory, GradeBonusSettlement
)
from .serializers import (
    SettlementSerializer, SettlementBatchSerializer,
    SettlementStatsSerializer, SettlementCreateSerializer,
    PaymentUpdateSerializer, ExpectedPaymentDateSerializer,
    CommissionGradeTrackingSerializer, GradeAchievementHistorySerializer, 
    GradeBonusSettlementSerializer, GradeTargetSetupSerializer, GradeStatsSerializer
)

logger = logging.getLogger(__name__)


class SettlementViewSet(viewsets.ModelViewSet):
    """
    정산 관리 ViewSet
    """
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated, HierarchyPermission]
    
    def get_queryset(self):
        """계층 구조에 따른 정산 목록 조회 (날짜 필터 지원)"""
        user = self.request.user
        
        # 기본 쿼리셋 (관련 데이터 포함)
        queryset = Settlement.objects.select_related(
            'order', 'company', 'order__policy'
        )
        
        # 슈퍼유저는 모든 정산 조회 가능
        if user.is_superuser:
            base_queryset = queryset
        else:
            # CompanyUser 확인
            if not hasattr(user, 'companyuser'):
                return queryset.none()
            
            company = user.companyuser.company
            
            # 회사 타입에 따른 필터링
            if company.type == 'headquarters':
                # 본사는 모든 정산 조회 가능
                base_queryset = queryset
            elif company.type == 'agency':
                # 협력사는 자신과 하위 판매점의 정산만 조회
                base_queryset = queryset.filter(
                    Q(company=company) |
                    Q(company__parent_company=company)
                )
            else:  # retail
                # 판매점은 자신의 정산만 조회
                base_queryset = queryset.filter(company=company)
        
        # 날짜 필터 적용 (GET 요청에서만)
        if self.request.method == 'GET':
            start_date_str = self.request.query_params.get('start_date')
            end_date_str = self.request.query_params.get('end_date')
            date_column = self.request.query_params.get('date_column', 'created_at')
            status_filter = self.request.query_params.get('status')
            
            logger.info(f"쿼리 파라미터: start_date={start_date_str}, end_date={end_date_str}, date_column={date_column}, status={status_filter}")
            
            # 날짜 필터 적용
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    
                    logger.info(f"날짜 필터 적용: {start_date} ~ {end_date}, 컬럼: {date_column}")
                    
                    # 날짜 컬럼에 따른 필터링
                    date_filter = {}
                    if date_column == 'created_at':
                        date_filter = {
                            'created_at__date__gte': start_date,
                            'created_at__date__lte': end_date
                        }
                    elif date_column == 'paid_at':
                        date_filter = {
                            'paid_at__date__gte': start_date,
                            'paid_at__date__lte': end_date
                        }
                    elif date_column == 'order__created_at':
                        date_filter = {
                            'order__created_at__date__gte': start_date,
                            'order__created_at__date__lte': end_date
                        }
                    elif date_column == 'order__activation_date':
                        # TelecomOrder의 activation_date는 직접 연결되지 않으므로 생략
                        pass
                    elif date_column == 'updated_at':
                        date_filter = {
                            'updated_at__date__gte': start_date,
                            'updated_at__date__lte': end_date
                        }
                    
                    logger.info(f"적용할 필터: {date_filter}")
                    
                    if date_filter:
                        original_count = base_queryset.count()
                        base_queryset = base_queryset.filter(**date_filter)
                        filtered_count = base_queryset.count()
                        logger.info(f"필터 적용 결과: {original_count} -> {filtered_count}")
                    else:
                        logger.warning(f"날짜 컬럼 '{date_column}'에 대한 필터가 설정되지 않음")
                    
                except ValueError:
                    # 날짜 형식 오류 시 기본 쿼리셋 반환
                    pass
            
            # 상태 필터 적용
            if status_filter and status_filter != 'all':
                base_queryset = base_queryset.filter(status=status_filter)
        
        return base_queryset
    
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
            unpaid_count=Count('id', filter=Q(status='unpaid')),  # 새로 추가
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
    def pay(self, request, pk=None):
        """입금 처리 (본사만 가능) - mark_paid의 별칭"""
        # mark_paid와 동일한 로직 사용
        return self.mark_paid(request, pk)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CompanyTypePermission])
    def mark_paid(self, request, pk=None):
        """입금 완료 처리 (본사만 가능)"""
        settlement = self.get_object()
        serializer = PaymentUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment_method = serializer.validated_data.get('payment_method', '')
            payment_reference = serializer.validated_data.get('payment_reference', '')
            
            settlement.mark_as_paid(
                user=request.user,
                payment_method=payment_method,
                payment_reference=payment_reference
            )
            
            result_serializer = self.get_serializer(settlement)
            return Response({
                'message': '입금 완료 처리가 완료되었습니다.',
                'settlement': result_serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CompanyTypePermission])
    def mark_unpaid(self, request, pk=None):
        """미입금 처리 (본사만 가능)"""
        settlement = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason.strip():
            return Response(
                {'error': '미입금 사유를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            settlement.mark_as_unpaid(reason, request.user)
            serializer = self.get_serializer(settlement)
            return Response({
                'message': '미입금 처리가 완료되었습니다.',
                'settlement': serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """입금 대기 중인 정산 목록"""
        queryset = self.get_queryset().filter(status='approved').order_by('-approved_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CompanyTypePermission])
    def set_expected_date(self, request, pk=None):
        """입금 예정일 설정 (본사만 가능)"""
        settlement = self.get_object()
        serializer = ExpectedPaymentDateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            expected_date = serializer.validated_data['expected_payment_date']
            settlement.set_expected_payment_date(expected_date, request.user)
            
            result_serializer = self.get_serializer(settlement)
            return Response({
                'message': f'입금 예정일이 {expected_date}로 설정되었습니다.',
                'settlement': result_serializer.data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def payment_schedule(self, request):
        """입금 예정 일정 조회"""
        # 오늘부터 30일 내 예정된 입금
        from datetime import date, timedelta
        
        today = date.today()
        end_date = today + timedelta(days=30)
        
        queryset = self.get_queryset().filter(
            status__in=['approved', 'unpaid'],
            expected_payment_date__gte=today,
            expected_payment_date__lte=end_date
        ).order_by('expected_payment_date')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unpaid_settlements(self, request):
        """미입금 정산 목록"""
        queryset = self.get_queryset().filter(status='unpaid').order_by('-updated_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def test_excel(self, request):
        """엑셀 테스트 엔드포인트"""
        try:
            logger.info("테스트 엑셀 시작")
            
            # 간단한 엑셀 생성
            import io
            import xlsxwriter
            
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('테스트')
            
            worksheet.write(0, 0, '테스트')
            worksheet.write(1, 0, '성공')
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="test.xlsx"'
            
            logger.info("테스트 엑셀 완료")
            return response
            
        except Exception as e:
            logger.error(f"테스트 엑셀 오류: {e}")
            return Response({'error': str(e)}, status=500)
    
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
        """정산 내역 엑셀 출력"""
        try:
            logger.info(f"엑셀 내보내기 시작: 사용자={request.user.username}")
            logger.info(f"쿼리 파라미터: {dict(request.query_params)}")
            # 파라미터 가져오기
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            status_filter = request.query_params.get('status')
            date_column = request.query_params.get('date_column', 'created_at')
            
            # 기본 쿼리셋 (더 많은 관련 데이터 포함)
            queryset = self.get_queryset().select_related(
                'order', 'company', 'order__policy'
            )
            
            # 날짜 필터 적용 (있는 경우, 없으면 최근 3개월)
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    
                    # 최대 1년 제한
                    if (end_date - start_date).days > 365:
                        return Response(
                            {'error': '최대 1년까지만 조회 가능합니다.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # 날짜 컬럼에 따른 필터링
                    date_filter = {}
                    if date_column == 'created_at':
                        date_filter = {
                            'created_at__date__gte': start_date,
                            'created_at__date__lte': end_date
                        }
                    elif date_column == 'paid_at':
                        date_filter = {
                            'paid_at__date__gte': start_date,
                            'paid_at__date__lte': end_date
                        }
                    elif date_column == 'order__created_at':
                        date_filter = {
                            'order__created_at__date__gte': start_date,
                            'order__created_at__date__lte': end_date
                        }
                    elif date_column == 'order__activation_date':
                        # TelecomOrder의 activation_date는 직접 연결되지 않으므로 생략
                        pass
                    elif date_column == 'updated_at':
                        date_filter = {
                            'updated_at__date__gte': start_date,
                            'updated_at__date__lte': end_date
                        }
                    
                    if date_filter:
                        queryset = queryset.filter(**date_filter)
                    
                except ValueError:
                    return Response(
                        {'error': '날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif start_date_str or end_date_str:
                # 시작일 또는 종료일 중 하나만 있는 경우
                return Response(
                    {'error': '시작일과 종료일을 모두 입력하거나 모두 비워주세요.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                # 날짜 필터가 없는 경우 최근 3개월로 제한
                from django.utils import timezone
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=90)
                queryset = queryset.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            
            # 상태 필터 적용 (있는 경우)
            if status_filter and status_filter != 'all':
                queryset = queryset.filter(status=status_filter)
            
            # 엑셀 파일 생성
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('정산내역')
            
            # 스타일 정의
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'left',
                'valign': 'vcenter'
            })
            
            number_format = workbook.add_format({
                'border': 1,
                'align': 'right',
                'valign': 'vcenter',
                'num_format': '#,##0'
            })
            
            date_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': 'yyyy-mm-dd'
            })
            
            # 헤더 작성
            headers = [
                '번호', '정산번호', '주문번호', '업체명', '업체유형', 
                '정산액', '상태', '생성일', '지급일', '정책명', '통신사', '비고'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # 컬럼 너비 설정
            worksheet.set_column(0, 0, 8)   # 번호
            worksheet.set_column(1, 1, 15)  # 정산번호
            worksheet.set_column(2, 2, 15)  # 주문번호
            worksheet.set_column(3, 3, 20)  # 업체명
            worksheet.set_column(4, 4, 12)  # 업체유형
            worksheet.set_column(5, 5, 15)  # 정산액
            worksheet.set_column(6, 6, 12)  # 상태
            worksheet.set_column(7, 7, 12)  # 생성일
            worksheet.set_column(8, 8, 12)  # 지급일
            worksheet.set_column(9, 9, 25)  # 정책명
            worksheet.set_column(10, 10, 10) # 통신사
            worksheet.set_column(11, 11, 30) # 비고
            
            # 데이터 작성 (QuerySet을 리스트로 변환)
            settlements_list = list(queryset)
            for row, settlement in enumerate(settlements_list, 1):
                # 상태 한글 변환
                status_map = {
                    'pending': '정산 대기',
                    'approved': '정산 승인',
                    'paid': '입금 완료',
                    'unpaid': '미입금',
                    'cancelled': '취소됨'
                }
                
                # 업체 유형 한글 변환
                company_type_map = {
                    'headquarters': '본사',
                    'agency': '협력사',
                    'retail': '판매점'
                }
                
                worksheet.write(row, 0, row, cell_format)  # 번호
                worksheet.write(row, 1, str(settlement.id)[:8], cell_format)  # 정산번호
                worksheet.write(row, 2, str(settlement.order.id)[:8] if settlement.order else '-', cell_format)  # 주문번호
                worksheet.write(row, 3, settlement.company.name if settlement.company else '-', cell_format)  # 업체명
                worksheet.write(row, 4, company_type_map.get(settlement.company.type, settlement.company.type) if settlement.company else '-', cell_format)  # 업체유형
                worksheet.write(row, 5, float(settlement.rebate_amount or 0), number_format)  # 정산액
                worksheet.write(row, 6, status_map.get(settlement.status, settlement.status), cell_format)  # 상태
                worksheet.write(row, 7, settlement.created_at.date(), date_format)  # 생성일
                worksheet.write(row, 8, settlement.paid_at.date() if settlement.paid_at else '-', cell_format)  # 지급일
                worksheet.write(row, 9, settlement.order.policy.title if settlement.order and settlement.order.policy else '-', cell_format)  # 정책명
                worksheet.write(row, 10, settlement.order.policy.carrier if settlement.order and settlement.order.policy else '-', cell_format)  # 통신사
                worksheet.write(row, 11, settlement.notes or '-', cell_format)  # 비고
            
            # 요약 정보 추가
            data_count = len(settlements_list)
            summary_row = data_count + 2
            worksheet.write(summary_row, 3, '합계:', header_format)
            worksheet.write(summary_row, 5, f'=SUM(F2:F{data_count+1})', number_format)
            
            workbook.close()
            output.seek(0)
            
            # HTTP 응답 생성
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # 파일명 생성
            filename = f'정산내역_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"엑셀 내보내기 완료: {request.user.username}, 건수: {data_count}")
            return response
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"정산 엑셀 출력 실패: {str(e)}\n{error_detail}")
            return Response(
                {'error': f'엑셀 파일 생성 중 오류가 발생했습니다: {str(e)}'},
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


class CommissionGradeTrackingViewSet(viewsets.ModelViewSet):
    """수수료 그레이드 추적 뷰셋"""
    
    serializer_class = CommissionGradeTrackingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = CommissionGradeTracking.objects.select_related(
            'company', 'policy'
        ).filter(is_active=True)
        
        # 본사가 아닌 경우 자신의 그레이드 추적만 조회 가능
        if not self.request.user.is_staff:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=self.request.user)
                queryset = queryset.filter(company=company_user.company)
            except CompanyUser.DoesNotExist:
                queryset = queryset.none()
        
        # 필터링
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        policy_id = self.request.query_params.get('policy')
        if policy_id:
            queryset = queryset.filter(policy_id=policy_id)
        
        period_type = self.request.query_params.get('period_type')
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'], permission_classes=[CompanyTypePermission(required_types=['headquarters'])])
    def setup_target(self, request):
        """그레이드 목표 설정"""
        serializer = GradeTargetSetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            company = Company.objects.get(id=data['company'])
            policy = Policy.objects.get(id=data['policy'])
            
            # 그레이드 추적 생성 또는 업데이트
            if data['period_type'] == 'monthly':
                tracking = CommissionGradeTracking.create_monthly_tracking(
                    company=company,
                    policy=policy,
                    year=data['year'],
                    month=data['month'],
                    target_orders=data['target_orders']
                )
            elif data['period_type'] == 'quarterly':
                tracking = CommissionGradeTracking.create_quarterly_tracking(
                    company=company,
                    policy=policy,
                    year=data['year'],
                    quarter=data['quarter'],
                    target_orders=data['target_orders']
                )
            else:
                return Response({
                    'error': '월별 또는 분기별 추적만 지원됩니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = CommissionGradeTrackingSerializer(tracking)
            return Response({
                'message': f'{company.name}의 그레이드 목표가 설정되었습니다.',
                'tracking': serializer.data
            })
            
        except Company.DoesNotExist:
            return Response({'error': '업체를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Policy.DoesNotExist:
            return Response({'error': '정책을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"그레이드 목표 설정 실패: {str(e)}")
            return Response({'error': '그레이드 목표 설정 중 오류가 발생했습니다.'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_orders(self, request, pk=None):
        """주문 수 업데이트"""
        tracking = self.get_object()
        
        try:
            old_level = tracking.achieved_grade_level
            tracking.update_current_orders()
            
            # 그레이드 레벨이 변경되었는지 확인
            if old_level != tracking.achieved_grade_level:
                # 그레이드 달성 이력 생성
                GradeAchievementHistory.objects.create(
                    grade_tracking=tracking,
                    from_level=old_level,
                    to_level=tracking.achieved_grade_level,
                    orders_at_change=tracking.current_orders,
                    bonus_amount=tracking.bonus_per_order
                )
                
                # 보너스 정산 생성 또는 업데이트
                if tracking.total_bonus > 0:
                    GradeBonusSettlement.create_bonus_settlement(tracking)
            
            serializer = CommissionGradeTrackingSerializer(tracking)
            return Response({
                'message': '주문 수가 업데이트되었습니다.',
                'tracking': serializer.data,
                'grade_changed': old_level != tracking.achieved_grade_level
            })
            
        except Exception as e:
            logger.error(f"주문 수 업데이트 실패: {str(e)}")
            return Response({'error': '주문 수 업데이트 중 오류가 발생했습니다.'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """그레이드 통계"""
        queryset = self.get_queryset()
        
        # 기본 통계
        total_companies = queryset.values('company').distinct().count()
        active_trackings = queryset.count()
        
        # 보너스 통계
        bonus_stats = GradeBonusSettlement.objects.aggregate(
            total_bonus=Sum('bonus_amount'),
            pending_bonus=Sum('bonus_amount', filter=Q(status='pending')),
            paid_bonus=Sum('bonus_amount', filter=Q(status='paid'))
        )
        
        # 그레이드별 분포
        grade_distribution = {}
        for level in range(6):  # 0-5 레벨
            count = queryset.filter(achieved_grade_level=level).count()
            grade_distribution[str(level)] = count
        
        # 기간 타입별 분포
        period_distribution = {}
        for period_type, _ in CommissionGradeTracking.PERIOD_TYPE_CHOICES:
            count = queryset.filter(period_type=period_type).count()
            period_distribution[period_type] = count
        
        stats_data = {
            'total_companies': total_companies,
            'active_trackings': active_trackings,
            'total_bonus_amount': bonus_stats['total_bonus'] or 0,
            'pending_bonus_amount': bonus_stats['pending_bonus'] or 0,
            'paid_bonus_amount': bonus_stats['paid_bonus'] or 0,
            'grade_distribution': grade_distribution,
            'period_type_distribution': period_distribution
        }
        
        serializer = GradeStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current_month(self, request):
        """현재 월 그레이드 추적 조회"""
        now = timezone.now()
        year = now.year
        month = now.month
        
        queryset = self.get_queryset().filter(
            period_type='monthly',
            period_start__year=year,
            period_start__month=month
        )
        
        serializer = CommissionGradeTrackingSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """상위 성과 업체 조회"""
        limit = int(request.query_params.get('limit', 10))
        
        queryset = self.get_queryset().filter(
            period_type='monthly',
            period_start__gte=timezone.now().replace(day=1)  # 이번 달
        ).order_by('-achieved_grade_level', '-current_orders')[:limit]
        
        serializer = CommissionGradeTrackingSerializer(queryset, many=True)
        return Response(serializer.data)


class GradeAchievementHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """그레이드 달성 이력 뷰셋"""
    
    serializer_class = GradeAchievementHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = GradeAchievementHistory.objects.select_related(
            'grade_tracking__company', 'grade_tracking__policy'
        )
        
        # 본사가 아닌 경우 자신의 이력만 조회 가능
        if not self.request.user.is_staff:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=self.request.user)
                queryset = queryset.filter(grade_tracking__company=company_user.company)
            except CompanyUser.DoesNotExist:
                queryset = queryset.none()
        
        # 필터링
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(grade_tracking__company_id=company_id)
        
        tracking_id = self.request.query_params.get('tracking_id')
        if tracking_id:
            queryset = queryset.filter(grade_tracking__id=tracking_id)
            
        return queryset.order_by('-achieved_at')


class GradeBonusSettlementViewSet(viewsets.ModelViewSet):
    """그레이드 보너스 정산 뷰셋"""
    
    serializer_class = GradeBonusSettlementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """쿼리셋 필터링"""
        queryset = GradeBonusSettlement.objects.select_related(
            'grade_tracking__company', 'approved_by'
        )
        
        # 본사가 아닌 경우 자신의 보너스 정산만 조회 가능
        if not self.request.user.is_staff:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=self.request.user)
                queryset = queryset.filter(grade_tracking__company=company_user.company)
            except CompanyUser.DoesNotExist:
                queryset = queryset.none()
        
        # 필터링
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(grade_tracking__company_id=company_id)
        
        policy_id = self.request.query_params.get('policy')
        if policy_id:
            queryset = queryset.filter(grade_tracking__policy_id=policy_id)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-created_at')
        
    @action(detail=True, methods=['post'], permission_classes=[CompanyTypePermission(required_types=['headquarters'])])
    def approve(self, request, pk=None):
        """보너스 정산 승인"""
        settlement = self.get_object()
        try:
            settlement.approve(self.request.user)
            return Response({'message': '보너스 정산이 승인되었습니다.'})
        except Exception as e:
            logger.error(f"보너스 정산 승인 실패: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=['post'], permission_classes=[CompanyTypePermission(required_types=['headquarters'])])
    def mark_as_paid(self, request, pk=None):
        """보너스 정산 지급 완료 처리"""
        settlement = self.get_object()
        try:
            settlement.mark_as_paid(self.request.user)
            return Response({'message': '보너스 정산 지급이 완료되었습니다.'})
        except Exception as e:
            logger.error(f"보너스 정산 지급 완료 처리 실패: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DynamicFilteredSettlementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    동적 필터링이 적용된 정산 뷰셋
    Phase 5-3: 사용자별 맞춤 필터링 시스템
    """
    
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """동적 필터가 적용된 쿼리셋 반환"""
        from .filters import DynamicSettlementFilter, SettlementFilterSerializer
        
        # 필터 파라미터 추출 및 검증
        filter_params = {}
        
        # URL 쿼리 파라미터에서 필터 추출
        for key, value in self.request.query_params.items():
            if key.endswith('[]'):  # 배열 파라미터 처리
                key = key[:-2]
                filter_params[key] = self.request.query_params.getlist(f'{key}[]')
            else:
                filter_params[key] = value
        
        # 필터 검증
        validated_filters = SettlementFilterSerializer.validate_filters(filter_params)
        
        # 동적 필터 적용
        dynamic_filter = DynamicSettlementFilter(self.request.user)
        queryset = dynamic_filter.apply_multiple_filters(validated_filters)
        
        return queryset.select_related(
            'order', 'order__policy', 'company', 'approved_by'
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def filter_options(self, request):
        """
        사용자가 사용할 수 있는 필터 옵션 반환
        
        GET /api/settlements/dynamic/filter_options/
        """
        try:
            from .filters import DynamicSettlementFilter
            
            dynamic_filter = DynamicSettlementFilter(request.user)
            options = dynamic_filter.get_filter_options()
            
            return Response(options)
            
        except Exception as e:
            logger.error(f"필터 옵션 조회 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def apply_filters(self, request):
        """
        복합 필터를 적용한 정산 목록 조회
        
        POST /api/settlements/dynamic/apply_filters/
        {
            "filters": {
                "period_type": "month",
                "statuses": ["approved", "paid"],
                "company_types": ["agency", "retail"],
                "min_amount": 10000,
                "max_amount": 100000
            },
            "page": 1,
            "page_size": 20
        }
        """
        try:
            from .filters import DynamicSettlementFilter, SettlementFilterSerializer
            
            filters = request.data.get('filters', {})
            page = int(request.data.get('page', 1))
            page_size = int(request.data.get('page_size', 20))
            
            # 필터 검증
            validated_filters = SettlementFilterSerializer.validate_filters(filters)
            
            # 동적 필터 적용
            dynamic_filter = DynamicSettlementFilter(request.user)
            queryset = dynamic_filter.apply_multiple_filters(validated_filters)
            
            # 페이지네이션 적용
            from django.core.paginator import Paginator
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 직렬화
            serializer = self.get_serializer(page_obj.object_list, many=True)
            
            return Response({
                'results': serializer.data,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'page_size': page_size,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                },
                'applied_filters': validated_filters,
                'summary': self._get_filtered_summary(queryset)
            })
            
        except Exception as e:
            logger.error(f"필터 적용 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def summary_stats(self, request):
        """
        필터가 적용된 정산 요약 통계
        
        GET /api/settlements/dynamic/summary_stats/?period_type=month&statuses[]=approved
        """
        try:
            from .filters import DynamicSettlementFilter, SettlementFilterSerializer
            
            # 필터 파라미터 추출
            filter_params = {}
            for key, value in request.query_params.items():
                if key.endswith('[]'):
                    key = key[:-2]
                    filter_params[key] = request.query_params.getlist(f'{key}[]')
                else:
                    filter_params[key] = value
            
            # 필터 검증 및 적용
            validated_filters = SettlementFilterSerializer.validate_filters(filter_params)
            dynamic_filter = DynamicSettlementFilter(request.user)
            queryset = dynamic_filter.apply_multiple_filters(validated_filters)
            
            # 요약 통계 생성
            summary = self._get_filtered_summary(queryset)
            
            return Response({
                'summary': summary,
                'applied_filters': validated_filters
            })
            
        except Exception as e:
            logger.error(f"요약 통계 조회 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_filtered_summary(self, queryset):
        """필터링된 쿼리셋의 요약 통계"""
        from django.db.models import Sum, Count, Avg
        
        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('rebate_amount'),
            avg_amount=Avg('rebate_amount'),
            total_grade_bonus=Sum('grade_bonus')
        )
        
        # 상태별 통계
        status_stats = {}
        for status_choice in Settlement.STATUS_CHOICES:
            status_code = status_choice[0]
            status_count = queryset.filter(status=status_code).count()
            if status_count > 0:
                status_stats[status_code] = {
                    'count': status_count,
                    'label': status_choice[1]
                }
        
        # 회사 유형별 통계
        company_type_stats = {}
        for company_type in ['headquarters', 'agency', 'retail']:
            type_data = queryset.filter(company__type=company_type).aggregate(
                count=Count('id'),
                amount=Sum('rebate_amount')
            )
            if type_data['count'] > 0:
                company_type_stats[company_type] = type_data
        
        return {
            'total_statistics': {
                'count': stats['total_count'] or 0,
                'total_amount': float(stats['total_amount'] or 0),
                'average_amount': float(stats['avg_amount'] or 0),
                'total_grade_bonus': float(stats['total_grade_bonus'] or 0)
            },
            'status_breakdown': status_stats,
            'company_type_breakdown': company_type_stats
        }


class AdvancedExcelExportViewSet(viewsets.ViewSet):
    """
    고급 엑셀 내보내기 ViewSet
    Phase 6: 사용자별 맞춤 엑셀 템플릿
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def export_with_filters(self, request):
        """
        동적 필터가 적용된 엑셀 내보내기
        
        POST /api/settlements/excel/export_with_filters/
        {
            "filters": {
                "period_type": "month",
                "statuses": ["approved", "paid"],
                "company_types": ["agency", "retail"]
            },
            "export_type": "auto"  // auto, headquarters, agency, retail
        }
        """
        try:
            from .excel_exporters import SettlementExcelExporter
            from .filters import SettlementFilterSerializer
            
            # 필터 및 내보내기 타입 추출
            filters = request.data.get('filters', {})
            export_type = request.data.get('export_type', 'auto')
            
            # 필터 검증
            validated_filters = SettlementFilterSerializer.validate_filters(filters)
            
            # 엑셀 내보내기 실행
            exporter = SettlementExcelExporter(request.user, validated_filters)
            
            if export_type == 'auto':
                # 사용자 유형에 따라 자동 선택
                response = exporter.export_for_user_type()
            elif export_type == 'headquarters':
                response = exporter.export_for_headquarters()
            elif export_type == 'agency':
                response = exporter.export_for_agency()
            elif export_type == 'retail':
                response = exporter.export_for_retail()
            else:
                return Response(
                    {'error': '유효하지 않은 내보내기 타입입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"엑셀 내보내기 완료: {request.user.username} - {export_type}")
            return response
            
        except Exception as e:
            logger.error(f"엑셀 내보내기 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def export_simple(self, request):
        """
        간단한 엑셀 내보내기 (GET 방식)
        
        GET /api/settlements/excel/export_simple/?period_type=month&statuses[]=approved
        """
        try:
            from .excel_exporters import SettlementExcelExporter
            from .filters import SettlementFilterSerializer
            
            # 쿼리 파라미터에서 필터 추출
            filter_params = {}
            for key, value in request.query_params.items():
                if key.endswith('[]'):
                    key = key[:-2]
                    filter_params[key] = request.query_params.getlist(f'{key}[]')
                else:
                    filter_params[key] = value
            
            # 필터 검증
            validated_filters = SettlementFilterSerializer.validate_filters(filter_params)
            
            # 엑셀 내보내기 실행
            exporter = SettlementExcelExporter(request.user, validated_filters)
            response = exporter.export_for_user_type()
            
            logger.info(f"간단 엑셀 내보내기 완료: {request.user.username}")
            return response
            
        except Exception as e:
            logger.error(f"간단 엑셀 내보내기 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def export_large_dataset(self, request):
        """
        대용량 데이터셋 엑셀 내보내기
        청크 단위로 처리하여 메모리 사용량 최적화
        
        POST /api/settlements/excel/export_large_dataset/
        {
            "filters": {...},
            "chunk_size": 1000,
            "max_records": 10000
        }
        """
        try:
            from .excel_exporters import LargeDatasetExcelExporter
            from .filters import SettlementFilterSerializer
            
            filters = request.data.get('filters', {})
            chunk_size = int(request.data.get('chunk_size', 1000))
            max_records = int(request.data.get('max_records', 10000))
            
            # 필터 검증
            validated_filters = SettlementFilterSerializer.validate_filters(filters)
            
            # 대용량 데이터 내보내기 실행
            exporter = LargeDatasetExcelExporter(
                request.user, 
                validated_filters,
                chunk_size=chunk_size,
                max_records=max_records
            )
            response = exporter.export()
            
            logger.info(f"대용량 엑셀 내보내기 완료: {request.user.username} - {max_records}건")
            return response
            
        except Exception as e:
            logger.error(f"대용량 엑셀 내보내기 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def export_templates(self, request):
        """
        사용 가능한 엑셀 템플릿 목록 반환
        
        GET /api/settlements/excel/export_templates/
        """
        try:
            from companies.models import CompanyUser
            
            # 사용자 회사 정보 조회
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                user_company_type = company_user.company.type
            except CompanyUser.DoesNotExist:
                user_company_type = None
            
            # 사용 가능한 템플릿 목록
            templates = []
            
            if request.user.is_superuser or user_company_type == 'headquarters':
                templates.extend([
                    {
                        'type': 'headquarters',
                        'name': '본사 전체 정산 현황',
                        'description': '전체 정산 데이터, 회사별/정책별/상태별 요약',
                        'sheets': ['전체 정산 현황', '회사별 요약', '정책별 요약', '상태별 요약']
                    },
                    {
                        'type': 'agency',
                        'name': '협력사 리베이트 현황',
                        'description': '받을/지급할 리베이트, 그레이드 현황, 판매점별 성과',
                        'sheets': ['받을 리베이트', '지급할 리베이트', '그레이드 현황', '판매점별 성과']
                    },
                    {
                        'type': 'retail',
                        'name': '판매점 리베이트 현황',
                        'description': '받을 리베이트, 월별/정책별 성과, 그레이드 현황',
                        'sheets': ['받을 리베이트', '월별 성과', '정책별 성과', '그레이드 현황']
                    }
                ])
            
            elif user_company_type == 'agency':
                templates.extend([
                    {
                        'type': 'agency',
                        'name': '협력사 리베이트 현황',
                        'description': '받을/지급할 리베이트, 그레이드 현황, 판매점별 성과',
                        'sheets': ['받을 리베이트', '지급할 리베이트', '그레이드 현황', '판매점별 성과']
                    },
                    {
                        'type': 'retail',
                        'name': '판매점 리베이트 현황',
                        'description': '받을 리베이트, 월별/정책별 성과, 그레이드 현황',
                        'sheets': ['받을 리베이트', '월별 성과', '정책별 성과', '그레이드 현황']
                    }
                ])
            
            elif user_company_type == 'retail':
                templates.append({
                    'type': 'retail',
                    'name': '판매점 리베이트 현황',
                    'description': '받을 리베이트, 월별/정책별 성과, 그레이드 현황',
                    'sheets': ['받을 리베이트', '월별 성과', '정책별 성과', '그레이드 현황']
                })
            
            return Response({
                'templates': templates,
                'user_company_type': user_company_type,
                'recommended_template': templates[0]['type'] if templates else None
            })
            
        except Exception as e:
            logger.error(f"템플릿 목록 조회 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def preview_data(self, request):
        """
        엑셀 내보내기 전 데이터 미리보기
        
        POST /api/settlements/excel/preview_data/
        {
            "filters": {...},
            "preview_limit": 100
        }
        """
        try:
            from .filters import DynamicSettlementFilter, SettlementFilterSerializer
            
            filters = request.data.get('filters', {})
            preview_limit = int(request.data.get('preview_limit', 100))
            
            # 필터 검증 및 적용
            validated_filters = SettlementFilterSerializer.validate_filters(filters)
            dynamic_filter = DynamicSettlementFilter(request.user)
            queryset = dynamic_filter.apply_multiple_filters(validated_filters)
            
            # 미리보기 데이터
            preview_settlements = queryset.select_related(
                'order', 'order__policy', 'company'
            )[:preview_limit]
            
            # 요약 통계
            summary = self._get_filtered_summary(queryset)
            
            # 미리보기 데이터 직렬화
            from .serializers import SettlementSerializer
            serializer = SettlementSerializer(preview_settlements, many=True)
            
            return Response({
                'preview_data': serializer.data,
                'total_count': queryset.count(),
                'preview_count': len(preview_settlements),
                'summary': summary,
                'estimated_file_size': self._estimate_file_size(queryset.count()),
                'processing_time_estimate': self._estimate_processing_time(queryset.count())
            })
            
        except Exception as e:
            logger.error(f"데이터 미리보기 오류: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _estimate_file_size(self, record_count: int) -> str:
        """파일 크기 추정"""
        # 대략적인 계산: 레코드당 평균 1KB
        estimated_kb = record_count * 1
        
        if estimated_kb < 1024:
            return f"{estimated_kb}KB"
        elif estimated_kb < 1024 * 1024:
            return f"{estimated_kb / 1024:.1f}MB"
        else:
            return f"{estimated_kb / (1024 * 1024):.1f}GB"
    
    def _estimate_processing_time(self, record_count: int) -> str:
        """처리 시간 추정"""
        # 대략적인 계산: 1000건당 1초
        estimated_seconds = record_count / 1000
        
        if estimated_seconds < 60:
            return f"{estimated_seconds:.0f}초"
        elif estimated_seconds < 3600:
            return f"{estimated_seconds / 60:.1f}분"
        else:
            return f"{estimated_seconds / 3600:.1f}시간"
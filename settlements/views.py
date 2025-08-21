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
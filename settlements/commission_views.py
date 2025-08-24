"""
수수료 팩트 테이블 및 데이터 웨어하우스 API 뷰
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import CommissionFact, CommissionGradeTracking, GradeBonusSettlement
from .serializers import CommissionGradeTrackingSerializer, GradeBonusSettlementSerializer
from .analytics import CommissionAnalyzer, GradeAnalyzer, DataWarehouseManager
from core.permissions import IsHeadquartersUser


class CommissionFactViewSet(viewsets.ReadOnlyModelViewSet):
    """
    수수료 팩트 테이블 ViewSet (읽기 전용)
    데이터 웨어하우스 분석 및 리포팅용
    """
    
    queryset = CommissionFact.objects.all()
    permission_classes = [IsAuthenticated, IsHeadquartersUser]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """수수료 요약 통계"""
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # 날짜 파싱
        try:
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'error': '날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식을 사용하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 분석기 초기화 및 요약 데이터 생성
        analyzer = CommissionAnalyzer(start_date, end_date)
        summary_data = analyzer.get_commission_summary()
        
        return Response(summary_data)
    
    @action(detail=False, methods=['get'])
    def company_ranking(self, request):
        """업체별 수수료 순위"""
        
        limit = int(request.query_params.get('limit', 10))
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'error': '날짜 형식이 잘못되었습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        analyzer = CommissionAnalyzer(start_date, end_date)
        ranking_data = analyzer.get_company_ranking(limit)
        
        return Response({'rankings': ranking_data})


class GradeTrackingViewSet(viewsets.ModelViewSet):
    """그레이드 추적 ViewSet"""
    
    queryset = CommissionGradeTracking.objects.all()
    serializer_class = CommissionGradeTrackingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자별 접근 권한에 따른 쿼리셋"""
        from companies.models import CompanyUser
        
        user = self.request.user
        
        try:
            company_user = CompanyUser.objects.get(django_user=user)
            user_company = company_user.company
            
            if user_company.type == 'headquarters':
                return super().get_queryset().select_related('company', 'policy')
            else:
                return super().get_queryset().filter(
                    Q(company=user_company) |
                    Q(company__parent_company=user_company)
                ).select_related('company', 'policy')
        
        except CompanyUser.DoesNotExist:
            return CommissionGradeTracking.objects.none()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """그레이드 달성 통계"""
        
        period_type = request.query_params.get('period_type', 'monthly')
        analyzer = GradeAnalyzer()
        stats_data = analyzer.get_grade_achievement_stats(period_type)
        
        return Response(stats_data)


class GradeBonusSettlementViewSet(viewsets.ModelViewSet):
    """그레이드 보너스 정산 ViewSet"""
    
    queryset = GradeBonusSettlement.objects.all()
    serializer_class = GradeBonusSettlementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """사용자별 접근 권한에 따른 쿼리셋"""
        from companies.models import CompanyUser
        
        user = self.request.user
        
        try:
            company_user = CompanyUser.objects.get(django_user=user)
            user_company = company_user.company
            
            if user_company.type == 'headquarters':
                return super().get_queryset().select_related(
                    'grade_tracking__company', 'grade_tracking__policy'
                )
            else:
                return super().get_queryset().filter(
                    Q(grade_tracking__company=user_company) |
                    Q(grade_tracking__company__parent_company=user_company)
                ).select_related(
                    'grade_tracking__company', 'grade_tracking__policy'
                )
        
        except CompanyUser.DoesNotExist:
            return GradeBonusSettlement.objects.none()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """보너스 정산 승인"""
        
        bonus_settlement = self.get_object()
        
        try:
            bonus_settlement.approve(request.user)
            return Response({
                'message': '보너스 정산이 승인되었습니다.',
                'settlement': GradeBonusSettlementSerializer(bonus_settlement).data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

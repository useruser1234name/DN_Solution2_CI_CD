"""
정산 시스템 시리얼라이저
"""

from rest_framework import serializers
from .models import Settlement, SettlementBatch, SettlementBatchItem
from companies.serializers import CompanySerializer
from orders.serializers import OrderSerializer


class SettlementSerializer(serializers.ModelSerializer):
    """정산 시리얼라이저"""
    
    company_name = serializers.CharField(source='company.name', read_only=True)
    order_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Settlement
        fields = [
            'id', 'order', 'company', 'company_name', 'order_info',
            'rebate_amount', 'status', 'status_display',
            'approved_by', 'approved_at', 'paid_at',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['approved_at', 'paid_at', 'created_at', 'updated_at']
    
    def get_order_info(self, obj):
        """주문 정보 요약"""
        return {
            'id': str(obj.order.id),
            'customer_name': obj.order.customer_name,
            'total_amount': str(obj.order.total_amount),
            'created_at': obj.order.created_at.isoformat()
        }


class SettlementCreateSerializer(serializers.ModelSerializer):
    """정산 생성 시리얼라이저"""
    
    class Meta:
        model = Settlement
        fields = ['order', 'company', 'rebate_amount', 'notes']
    
    def validate(self, data):
        """유효성 검증"""
        order = data.get('order')
        company = data.get('company')
        
        # 중복 정산 방지
        if Settlement.objects.filter(order=order, company=company).exists():
            raise serializers.ValidationError(
                "해당 주문과 업체에 대한 정산이 이미 존재합니다."
            )
        
        # 주문 상태 확인
        if order.status not in ['completed', 'shipped']:
            raise serializers.ValidationError(
                "완료되거나 배송 중인 주문만 정산할 수 있습니다."
            )
        
        return data


class SettlementStatsSerializer(serializers.Serializer):
    """정산 통계 시리얼라이저"""
    
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    cancelled_count = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class SettlementBatchItemSerializer(serializers.ModelSerializer):
    """정산 배치 항목 시리얼라이저"""
    
    settlement_info = SettlementSerializer(source='settlement', read_only=True)
    
    class Meta:
        model = SettlementBatchItem
        fields = ['id', 'settlement', 'settlement_info', 'added_at']
        read_only_fields = ['added_at']


class SettlementBatchSerializer(serializers.ModelSerializer):
    """정산 배치 시리얼라이저"""
    
    items = SettlementBatchItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    class Meta:
        model = SettlementBatch
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'total_amount', 'items', 'item_count',
            'created_by', 'created_by_name', 'created_at',
            'approved_by', 'approved_by_name', 'approved_at'
        ]
        read_only_fields = [
            'total_amount', 'created_at', 'approved_at',
            'created_by', 'approved_by'
        ]
    
    def validate(self, data):
        """유효성 검증"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "시작일이 종료일보다 늦을 수 없습니다."
            )
        
        return data
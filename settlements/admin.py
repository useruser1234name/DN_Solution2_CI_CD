from django.contrib import admin
from .models import Settlement, SettlementBatch, SettlementBatchItem


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['company', 'order', 'rebate_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'company__company_type']
    search_fields = ['company__name', 'order__customer_name']
    readonly_fields = ['created_at', 'updated_at', 'approved_at', 'paid_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('order', 'company', 'rebate_amount', 'status')
        }),
        ('승인/지급 정보', {
            'fields': ('approved_by', 'approved_at', 'paid_at')
        }),
        ('추가 정보', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(SettlementBatch)
class SettlementBatchAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'total_amount', 'created_at']
    list_filter = ['created_at', 'approved_at']
    search_fields = ['title', 'description']
    readonly_fields = ['total_amount', 'created_at', 'approved_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'description', 'start_date', 'end_date')
        }),
        ('정산 정보', {
            'fields': ('total_amount',)
        }),
        ('승인 정보', {
            'fields': ('created_by', 'created_at', 'approved_by', 'approved_at')
        }),
    )


@admin.register(SettlementBatchItem)
class SettlementBatchItemAdmin(admin.ModelAdmin):
    list_display = ['batch', 'settlement', 'added_at']
    list_filter = ['added_at', 'batch']
    search_fields = ['batch__title', 'settlement__company__name']
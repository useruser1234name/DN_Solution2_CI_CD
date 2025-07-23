# orders/admin.py
import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import Order, OrderMemo, Invoice

logger = logging.getLogger('orders')


class OrderMemoInline(admin.TabularInline):
    """
    주문서 상세 페이지에서 메모를 인라인으로 표시
    """
    model = OrderMemo
    extra = 1
    fields = ['memo', 'created_by', 'created_at']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('created_by').order_by('-created_at')


class InvoiceInline(admin.StackedInline):
    """
    주문서 상세 페이지에서 송장 정보를 인라인으로 표시
    """
    model = Invoice
    extra = 0
    fields = [
        'courier', 'invoice_number', 'recipient_name', 'recipient_phone',
        'sent_at', 'delivered_at'
    ]
    readonly_fields = ['sent_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    주문서 모델의 Django Admin 설정
    주문서 정보를 효율적으로 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'customer_name', 'model_name', 'carrier_display_badge', 'status_badge',
        'apply_type_badge', 'company_link', 'memo_count', 'invoice_status',
        'created_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'status', 'apply_type', 'carrier', 'company', 'policy',
        'created_by', 'created_at', 'updated_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'customer_name', 'customer_phone', 'customer_email',
        'model_name', 'memo'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'memo_count_detail', 'invoice_detail',
        'created_at', 'updated_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('고객 정보', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('주문 정보', {
            'fields': ('model_name', 'carrier', 'apply_type', 'status')
        }),
        ('연결 정보', {
            'fields': ('policy', 'company', 'created_by')
        }),
        ('추가 정보', {
            'fields': ('memo', 'delivery_address')
        }),
        ('상세 정보', {
            'fields': ('id', 'memo_count_detail', 'invoice_detail'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 인라인 모델 추가
    inlines = [OrderMemoInline, InvoiceInline]
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['customer_name']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['status']  # 뱃지로 표시되므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-created_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['policy', 'company', 'created_by']
    
    # 액션 설정
    actions = ['mark_as_received', 'mark_as_processing', 'mark_as_completed']
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'policy', 'company', 'created_by'
        ).prefetch_related('order_memos', 'invoice')
    
    def carrier_display_badge(self, obj):
        """통신사를 뱃지 형태로 표시"""
        colors = {
            'skt': '#e74c3c',       # 빨간색
            'kt': '#f39c12',        # 주황색
            'lgu': '#e91e63',       # 분홍색
            'skt_mvno': '#c0392b',  # 진한 빨간색
            'kt_mvno': '#d68910',   # 진한 주황색
            'lgu_mvno': '#ad1457'   # 진한 분홍색
        }
        color = colors.get(obj.carrier, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_carrier_display()
        )
    carrier_display_badge.short_description = '통신사'
    
    def status_badge(self, obj):
        """주문 상태를 뱃지 형태로 표시"""
        colors = {
            'reserved': '#6c757d',    # 회색
            'received': '#17a2b8',    # 청록색
            'processing': '#ffc107',  # 노란색
            'completed': '#28a745',   # 녹색
            'cancelled': '#dc3545'    # 빨간색
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 3px; font-size: 12px; font-weight: bold;">{}</span>',
            color,
            'black' if obj.status == 'processing' else 'white',
            obj.get_status_display()
        )
    status_badge.short_description = '처리 상태'
    
    def apply_type_badge(self, obj):
        """신청 타입을 뱃지 형태로 표시"""
        colors = {
            'new': '#007bff',         # 파란색
            'change': '#28a745',      # 녹색
            'transfer': '#ffc107',    # 노란색
            'additional': '#6f42c1'   # 보라색
        }
        color = colors.get(obj.apply_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            'black' if obj.apply_type == 'transfer' else 'white',
            obj.get_apply_type_display()
        )
    apply_type_badge.short_description = '신청 타입'
    
    def company_link(self, obj):
        """처리 업체를 링크로 표시"""
        if obj.company:
            url = reverse('admin:companies_company_change', args=[obj.company.id])
            return format_html('<a href="{}">{}</a>', url, obj.company.name)
        return '-'
    company_link.short_description = '처리 업체'
    company_link.admin_order_field = 'company__name'
    
    def memo_count(self, obj):
        """메모 수 표시"""
        try:
            count = obj.order_memos.count()
            if count > 0:
                url = reverse('admin:orders_ordermemo_changelist')
                return format_html(
                    '<a href="{}?order__id__exact={}">{} 개</a>',
                    url, obj.id, count
                )
            return '0 개'
        except Exception as e:
            logger.warning(f"메모 수 조회 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return '오류'
    memo_count.short_description = '메모'
    
    def memo_count_detail(self, obj):
        """상세 페이지에서 메모 목록 표시"""
        if obj.pk:
            memos = obj.order_memos.select_related('created_by').order_by('-created_at')
            if memos:
                memo_list = []
                for memo in memos[:5]:  # 최근 5개만 표시
                    memo_url = reverse('admin:orders_ordermemo_change', args=[memo.id])
                    author = memo.created_by.username if memo.created_by else "시스템"
                    created_at = memo.created_at.strftime('%m/%d %H:%M')
                    preview = memo.memo[:50] + '...' if len(memo.memo) > 50 else memo.memo
                    memo_list.append(
                        f'<li><a href="{memo_url}">[{created_at}] {author}: {preview}</a></li>'
                    )
                if len(memos) > 5:
                    memo_list.append(f'<li>... 외 {len(memos) - 5}개</li>')
                return mark_safe('<ul>' + ''.join(memo_list) + '</ul>')
            return '메모 없음'
        return '저장 후 표시됩니다'
    memo_count_detail.short_description = '메모 목록'
    
    def invoice_status(self, obj):
        """송장 상태 표시"""
        try:
            if hasattr(obj, 'invoice') and obj.invoice:
                invoice = obj.invoice
                if invoice.is_delivered():
                    return format_html(
                        '<span style="color: green;">✓ 배송완료</span><br>'
                        '<small>{}</small>',
                        invoice.delivered_at.strftime('%m/%d')
                    )
                else:
                    return format_html(
                        '<span style="color: blue;">📦 배송중</span><br>'
                        '<small>{}</small>',
                        invoice.get_courier_display()
                    )
            return format_html('<span style="color: gray;">송장 없음</span>')
        except Exception as e:
            logger.warning(f"송장 상태 조회 중 오류: {str(e)} - 주문: {obj.customer_name}")
            return '오류'
    invoice_status.short_description = '배송 상태'
    
    def invoice_detail(self, obj):
        """상세 페이지에서 송장 정보 표시"""
        if obj.pk and hasattr(obj, 'invoice') and obj.invoice:
            invoice = obj.invoice
            invoice_url = reverse('admin:orders_invoice_change', args=[invoice.id])
            
            info = f'<a href="{invoice_url}"><strong>{invoice.get_courier_display()}</strong></a><br>'
            info += f'송장번호: {invoice.invoice_number}<br>'
            info += f'발송일: {invoice.sent_at.strftime("%Y-%m-%d %H:%M")}<br>'
            
            if invoice.is_delivered():
                info += f'<span style="color: green;">배송완료: {invoice.delivered_at.strftime("%Y-%m-%d %H:%M")}</span>'
                if invoice.delivery_duration is not None:
                    info += f'<br>소요일: {invoice.get_delivery_duration()}일'
            else:
                info += '<span style="color: blue;">배송중</span>'
            
            return mark_safe(info)
        return '송장 없음'
    invoice_detail.short_description = '송장 정보'
    
    def created_at_formatted(self, obj):
        """접수일시를 한국 시간으로 포맷팅"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = '접수일시'
    created_at_formatted.admin_order_field = 'created_at'
    
    # 액션 메서드들
    def mark_as_received(self, request, queryset):
        """선택된 주문들을 접수 상태로 변경"""
        updated_count = 0
        for order in queryset:
            if order.update_status('received', request.user):
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개 주문이 접수 상태로 변경되었습니다.')
        logger.info(f"Admin에서 주문 일괄 접수 처리: {updated_count}개 - 관리자: {request.user}")
    mark_as_received.short_description = "선택된 주문을 접수 상태로 변경"
    
    def mark_as_processing(self, request, queryset):
        """선택된 주문들을 처리중 상태로 변경"""
        updated_count = 0
        for order in queryset:
            if order.update_status('processing', request.user):
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개 주문이 처리중 상태로 변경되었습니다.')
        logger.info(f"Admin에서 주문 일괄 처리중 처리: {updated_count}개 - 관리자: {request.user}")
    mark_as_processing.short_description = "선택된 주문을 처리중 상태로 변경"
    
    def mark_as_completed(self, request, queryset):
        """선택된 주문들을 완료 상태로 변경"""
        updated_count = 0
        for order in queryset:
            if order.update_status('completed', request.user):
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개 주문이 완료 상태로 변경되었습니다.')
        logger.info(f"Admin에서 주문 일괄 완료 처리: {updated_count}개 - 관리자: {request.user}")
    mark_as_completed.short_description = "선택된 주문을 완료 상태로 변경"
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅 및 접수자 자동 설정"""
        # 접수자가 설정되지 않은 경우 현재 사용자로 설정
        if not obj.created_by:
            obj.created_by = request.user
        
        action = '수정' if change else '접수'
        old_status = None
        
        if change:
            try:
                old_instance = Order.objects.get(pk=obj.pk)
                old_status = old_instance.status
            except Order.DoesNotExist:
                pass
        
        try:
            super().save_model(request, obj, form, change)
            
            # 상태 변경 로깅
            if change and old_status and old_status != obj.status:
                logger.info(f"Admin에서 주문 상태 변경: {obj.customer_name} - {old_status} → {obj.status} - 관리자: {request.user}")
            else:
                logger.info(f"Admin에서 주문 {action}: {obj.customer_name} - 관리자: {request.user}")
        
        except Exception as e:
            logger.error(f"Admin에서 주문 {action} 실패: {str(e)} - 주문: {obj.customer_name}")
            raise
    
    def delete_model(self, request, obj):
        """모델 삭제 시 로깅"""
        customer_name = obj.customer_name
        try:
            super().delete_model(request, obj)
            logger.info(f"Admin에서 주문 삭제: {customer_name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 주문 삭제 실패: {str(e)} - 주문: {customer_name}")
            raise


@admin.register(OrderMemo)
class OrderMemoAdmin(admin.ModelAdmin):
    """
    주문 메모 모델의 Django Admin 설정
    주문 처리 과정의 메모를 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'order_link', 'memo_preview', 'created_by_user',
        'created_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'created_by', 'created_at', 'order__status', 'order__company'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'memo', 'order__customer_name', 'order__customer_phone'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'created_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('메모 정보', {
            'fields': ('order', 'memo')
        }),
        ('작성 정보', {
            'fields': ('created_by', 'created_at', 'id'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['memo_preview']
    
    # 페이지당 표시할 항목 수
    list_per_page = 30
    
    # 정렬 기준
    ordering = ['-created_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['order', 'created_by']
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        queryset = super().get_queryset(request)
        return queryset.select_related('order', 'created_by')
    
    def order_link(self, obj):
        """연관 주문서를 링크로 표시"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}">{}</a><br><small>상태: {}</small>',
                url, obj.order.customer_name, obj.order.get_status_display()
            )
        return '-'
    order_link.short_description = '연관 주문서'
    order_link.admin_order_field = 'order__customer_name'
    
    def memo_preview(self, obj):
        """메모 내용 미리보기"""
        preview = obj.memo[:80] + '...' if len(obj.memo) > 80 else obj.memo
        return format_html('<div style="max-width: 300px;">{}</div>', preview)
    memo_preview.short_description = '메모 내용'
    
    def created_by_user(self, obj):
        """작성자 표시"""
        if obj.created_by:
            return obj.created_by.username
        return '시스템'
    created_by_user.short_description = '작성자'
    created_by_user.admin_order_field = 'created_by__username'
    
    def created_at_formatted(self, obj):
        """작성일시를 한국 시간으로 포맷팅"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = '작성일시'
    created_at_formatted.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅 및 작성자 자동 설정"""
        # 작성자가 설정되지 않은 경우 현재 사용자로 설정
        if not obj.created_by:
            obj.created_by = request.user
        
        action = '수정' if change else '작성'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 주문 메모 {action}: {obj.order.customer_name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 주문 메모 {action} 실패: {str(e)} - 주문: {obj.order.customer_name}")
            raise


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    송장 모델의 Django Admin 설정
    배송 처리 및 송장 추적을 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'order_link', 'courier_badge', 'invoice_number',
        'delivery_status_badge', 'sent_at_formatted', 'delivery_duration'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'courier', 'sent_at', 'delivered_at', 'order__company', 'order__status'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'invoice_number', 'order__customer_name', 'order__customer_phone',
        'recipient_name', 'recipient_phone'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'delivery_info', 'sent_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('주문 정보', {
            'fields': ('order',)
        }),
        ('배송 정보', {
            'fields': ('courier', 'invoice_number')
        }),
        ('수취인 정보', {
            'fields': ('recipient_name', 'recipient_phone')
        }),
        ('배송 상태', {
            'fields': ('delivered_at', 'delivery_info')
        }),
        ('시간 정보', {
            'fields': ('id', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['invoice_number']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['delivered_at']  # 복잡한 로직이 있으므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-sent_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['order']
    
    # 액션 설정
    actions = ['mark_as_delivered']
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        queryset = super().get_queryset(request)
        return queryset.select_related('order', 'order__company')
    
    def order_link(self, obj):
        """연관 주문서를 링크로 표시"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}">{}</a><br>'
                '<small>{}</small>',
                url, obj.order.customer_name, obj.order.model_name
            )
        return '-'
    order_link.short_description = '연관 주문서'
    order_link.admin_order_field = 'order__customer_name'
    
    def courier_badge(self, obj):
        """택배사를 뱃지 형태로 표시"""
        colors = {
            'cj': '#e74c3c',      # 빨간색
            'lotte': '#f39c12',   # 주황색
            'hanjin': '#3498db',  # 파란색
            'post': '#27ae60',    # 녹색
            'kdexp': '#9b59b6',   # 보라색
            'logen': '#1abc9c',   # 청록색
            'daesin': '#34495e',  # 짙은 회색
            'etc': '#95a5a6'      # 회색
        }
        color = colors.get(obj.courier, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 12px; font-weight: bold;">{}</span>',
            color, obj.get_courier_display()
        )
    courier_badge.short_description = '택배사'
    
    def delivery_status_badge(self, obj):
        """배송 상태를 뱃지 형태로 표시"""
        if obj.is_delivered():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">✓ 배송완료</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">📦 배송중</span>'
            )
    delivery_status_badge.short_description = '배송 상태'
    
    def sent_at_formatted(self, obj):
        """발송일시를 한국 시간으로 포맷팅"""
        return obj.sent_at.strftime('%Y-%m-%d %H:%M')
    sent_at_formatted.short_description = '발송일시'
    sent_at_formatted.admin_order_field = 'sent_at'
    
    def delivery_duration(self, obj):
        """배송 소요 시간 표시"""
        try:
            if obj.is_delivered():
                duration = obj.delivered_at - obj.sent_at
                days = duration.days
                if days == 0:
                    return '당일'
                elif days == 1:
                    return '1일'
                else:
                    return f'{days}일'
            return '-'
        except Exception as e:
            logger.warning(f"배송 소요 시간 계산 중 오류: {str(e)}")
            return '오류'
    delivery_duration.short_description = '소요 시간'
    
    def delivery_info(self, obj):
        """상세 페이지에서 배송 정보 표시"""
        if obj.pk:
            info = f'발송일: {obj.sent_at.strftime("%Y-%m-%d %H:%M")}<br>'
            
            if obj.is_delivered():
                info += f'<span style="color: green;">배송완료: {obj.delivered_at.strftime("%Y-%m-%d %H:%M")}</span><br>'
                duration = obj.delivered_at - obj.sent_at
                info += f'소요 시간: {duration.days}일'
            else:
                info += '<span style="color: blue;">배송 중</span><br>'
                duration = timezone.now() - obj.sent_at
                info += f'경과 시간: {duration.days}일'
            
            info += f'<br>수취인: {obj.recipient_name or obj.order.customer_name}'
            info += f'<br>연락처: {obj.recipient_phone or obj.order.customer_phone}'
            
            return mark_safe(info)
        return '저장 후 표시됩니다'
    delivery_info.short_description = '배송 상세 정보'
    
    # 액션 메서드
    def mark_as_delivered(self, request, queryset):
        """선택된 송장들을 배송완료로 처리"""
        from django.utils import timezone
        
        updated_count = 0
        for invoice in queryset:
            if not invoice.is_delivered():
                invoice.mark_as_delivered(timezone.now())
                updated_count += 1
        
        self.message_user(request, f'{updated_count}개 송장이 배송완료로 처리되었습니다.')
        logger.info(f"Admin에서 송장 일괄 배송완료 처리: {updated_count}개 - 관리자: {request.user}")
    mark_as_delivered.short_description = "선택된 송장을 배송완료로 처리"
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅"""
        action = '수정' if change else '등록'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 송장 {action}: {obj.order.customer_name} - {obj.courier} ({obj.invoice_number}) - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 송장 {action} 실패: {str(e)} - 주문: {obj.order.customer_name}")
            raise
    
    def delete_model(self, request, obj):
        """모델 삭제 시 로깅"""
        customer_name = obj.order.customer_name
        invoice_info = f"{obj.get_courier_display()} ({obj.invoice_number})"
        try:
            super().delete_model(request, obj)
            logger.info(f"Admin에서 송장 삭제: {customer_name} - {invoice_info} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 송장 삭제 실패: {str(e)} - 송장: {invoice_info}")
            raise
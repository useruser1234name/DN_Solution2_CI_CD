from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Policy, PolicyNotice, PolicyAssignment


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    """
    정책 관리 Admin 인터페이스
    """
    list_display = [
        'title', 'form_type', 'carrier', 'contract_period', 
        'rebate_agency', 'rebate_retail', 'expose', 
        'premium_market_expose', 'created_at', 'assignment_count'
    ]
    
    list_filter = [
        'form_type', 'carrier', 'contract_period', 
        'expose', 'premium_market_expose', 'created_at'
    ]
    
    search_fields = ['title', 'description']
    
    readonly_fields = ['id', 'created_at', 'updated_at', 'html_content']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'title', 'description', 'form_type')
        }),
        ('필터링 설정', {
            'fields': ('carrier', 'contract_period')
        }),
        ('리베이트 설정', {
            'fields': ('rebate_agency', 'rebate_retail')
        }),
        ('노출 설정', {
            'fields': ('expose', 'premium_market_expose')
        }),
        ('HTML 내용', {
            'fields': ('html_content',),
            'classes': ('collapse',)
        }),
        ('생성 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['toggle_expose', 'toggle_premium_market_expose', 'regenerate_html']
    
    def assignment_count(self, obj):
        """배정된 업체 수 표시"""
        count = obj.get_assignment_count()
        if count > 0:
            url = reverse('admin:policies_policyassignment_changelist') + f'?policy__id__exact={obj.id}'
            return format_html('<a href="{}">{}개 업체</a>', url, count)
        return '0개 업체'
    assignment_count.short_description = '배정 업체 수'
    
    def toggle_expose(self, request, queryset):
        """선택된 정책들의 노출 상태 토글"""
        updated = 0
        for policy in queryset:
            if policy.toggle_expose():
                updated += 1
        
        if updated > 0:
            self.message_user(
                request, 
                f'{updated}개 정책의 노출 상태가 변경되었습니다.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                '노출 상태 변경에 실패했습니다.',
                messages.ERROR
            )
    toggle_expose.short_description = "선택된 정책들의 노출 상태 토글"
    
    def toggle_premium_market_expose(self, request, queryset):
        """선택된 정책들의 프리미엄 마켓 노출 상태 토글"""
        updated = 0
        for policy in queryset:
            if policy.toggle_premium_market_expose():
                updated += 1
        
        if updated > 0:
            self.message_user(
                request, 
                f'{updated}개 정책의 프리미엄 마켓 노출 상태가 변경되었습니다.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                '프리미엄 마켓 노출 상태 변경에 실패했습니다.',
                messages.ERROR
            )
    toggle_premium_market_expose.short_description = "선택된 정책들의 프리미엄 마켓 노출 상태 토글"
    
    def regenerate_html(self, request, queryset):
        """선택된 정책들의 HTML 내용 재생성"""
        updated = 0
        for policy in queryset:
            try:
                policy.generate_html_content()
                policy.save()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f'정책 "{policy.title}" HTML 재생성 실패: {str(e)}',
                    messages.ERROR
                )
        
        if updated > 0:
            self.message_user(
                request, 
                f'{updated}개 정책의 HTML 내용이 재생성되었습니다.',
                messages.SUCCESS
            )
    regenerate_html.short_description = "선택된 정책들의 HTML 내용 재생성"
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 생성자 설정"""
        if not change:  # 새로 생성하는 경우
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class PolicyNoticeInline(admin.TabularInline):
    """
    정책 안내사항 인라인 편집
    """
    model = PolicyNotice
    extra = 1
    fields = ['notice_type', 'title', 'content', 'is_important', 'order']


@admin.register(PolicyNotice)
class PolicyNoticeAdmin(admin.ModelAdmin):
    """
    정책 안내사항 관리 Admin 인터페이스
    """
    list_display = [
        'title', 'policy', 'notice_type', 'is_important', 
        'order', 'created_at'
    ]
    
    list_filter = ['notice_type', 'is_important', 'created_at']
    
    search_fields = ['title', 'content', 'policy__title']
    
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'policy', 'notice_type', 'title')
        }),
        ('안내 내용', {
            'fields': ('content',)
        }),
        ('설정', {
            'fields': ('is_important', 'order')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_important', 'mark_as_normal']
    
    def mark_as_important(self, request, queryset):
        """선택된 안내사항들을 중요 안내로 설정"""
        updated = queryset.update(is_important=True)
        self.message_user(
            request, 
            f'{updated}개 안내사항이 중요 안내로 설정되었습니다.',
            messages.SUCCESS
        )
    mark_as_important.short_description = "선택된 안내사항들을 중요 안내로 설정"
    
    def mark_as_normal(self, request, queryset):
        """선택된 안내사항들을 일반 안내로 설정"""
        updated = queryset.update(is_important=False)
        self.message_user(
            request, 
            f'{updated}개 안내사항이 일반 안내로 설정되었습니다.',
            messages.SUCCESS
        )
    mark_as_normal.short_description = "선택된 안내사항들을 일반 안내로 설정"


@admin.register(PolicyAssignment)
class PolicyAssignmentAdmin(admin.ModelAdmin):
    """
    정책 배정 관리 Admin 인터페이스
    """
    list_display = [
        'policy', 'company', 'custom_rebate', 'effective_rebate',
        'rebate_source', 'expose_to_child', 'assigned_at'
    ]
    
    list_filter = ['expose_to_child', 'assigned_at', 'policy__form_type']
    
    search_fields = ['policy__title', 'company__name']
    
    readonly_fields = ['id', 'assigned_at', 'effective_rebate', 'rebate_source']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'policy', 'company')
        }),
        ('리베이트 설정', {
            'fields': ('custom_rebate', 'effective_rebate', 'rebate_source')
        }),
        ('노출 설정', {
            'fields': ('expose_to_child',)
        }),
        ('시간 정보', {
            'fields': ('assigned_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['toggle_expose_to_child']
    
    def effective_rebate(self, obj):
        """실제 적용되는 리베이트 표시"""
        return f"{obj.get_effective_rebate():,}원"
    effective_rebate.short_description = '실제 리베이트'
    
    def rebate_source(self, obj):
        """리베이트 출처 표시"""
        return obj.get_rebate_source()
    rebate_source.short_description = '리베이트 출처'
    
    def toggle_expose_to_child(self, request, queryset):
        """선택된 배정들의 하위 노출 상태 토글"""
        updated = 0
        for assignment in queryset:
            assignment.expose_to_child = not assignment.expose_to_child
            assignment.save()
            updated += 1
        
        self.message_user(
            request, 
            f'{updated}개 정책 배정의 하위 노출 상태가 변경되었습니다.',
            messages.SUCCESS
        )
    toggle_expose_to_child.short_description = "선택된 배정들의 하위 노출 상태 토글"


# Policy 모델에 PolicyNotice 인라인 추가
PolicyAdmin.inlines = [PolicyNoticeInline]

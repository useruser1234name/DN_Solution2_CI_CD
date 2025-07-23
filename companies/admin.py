# companies/admin.py
import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, CompanyUser, CompanyMessage

logger = logging.getLogger('companies')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    업체 모델의 Django Admin 설정
    업체 정보를 효율적으로 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'name', 'type_badge', 'status_badge', 'visible_badge',
        'default_courier', 'users_count', 'created_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'type', 'status', 'visible', 'created_at', 'updated_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'name', 'default_courier'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'users_count_detail'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'name', 'type')
        }),
        ('운영 설정', {
            'fields': ('status', 'visible', 'default_courier')
        }),
        ('추가 정보', {
            'fields': ('users_count_detail', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['name']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['status', 'visible']  # 뱃지로 표시되므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-created_at']
    
    def type_badge(self, obj):
        """업체 타입을 뱃지 형태로 표시"""
        colors = {
            'agency': '#28a745',  # 녹색
            'retail': '#007bff'   # 파란색
        }
        color = colors.get(obj.type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color, obj.get_type_display()
        )
    type_badge.short_description = '업체 타입'
    
    def status_badge(self, obj):
        """운영 상태를 뱃지 형태로 표시"""
        if obj.status:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">운영중</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">중단</span>'
            )
    status_badge.short_description = '운영 상태'
    
    def visible_badge(self, obj):
        """노출 여부를 아이콘으로 표시"""
        if obj.visible:
            return format_html('✅')
        else:
            return format_html('❌')
    visible_badge.short_description = '노출 여부'
    
    def users_count(self, obj):
        """소속 사용자 수 표시"""
        try:
            count = obj.users.count()
            if count > 0:
                url = reverse('admin:companies_companyuser_changelist')
                return format_html(
                    '<a href="{}?company__id__exact={}">{} 명</a>',
                    url, obj.id, count
                )
            return '0 명'
        except Exception as e:
            logger.warning(f"사용자 수 조회 중 오류: {str(e)} - 업체: {obj.name}")
            return '오류'
    users_count.short_description = '소속 사용자'
    
    def users_count_detail(self, obj):
        """상세 페이지에서 사용자 목록 표시"""
        if obj.pk:
            users = obj.users.all()
            if users:
                user_list = []
                for user in users:
                    user_url = reverse('admin:companies_companyuser_change', args=[user.id])
                    user_list.append(f'<a href="{user_url}">{user.username} ({user.get_role_display()})</a>')
                return mark_safe('<br>'.join(user_list))
            return '소속 사용자 없음'
        return '저장 후 표시됩니다'
    users_count_detail.short_description = '소속 사용자 목록'
    
    def created_at_formatted(self, obj):
        """생성일시를 한국 시간으로 포맷팅"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = '생성일시'
    created_at_formatted.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅"""
        action = '수정' if change else '생성'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 업체 {action}: {obj.name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 업체 {action} 실패: {str(e)} - 업체: {obj.name}")
            raise
    
    def delete_model(self, request, obj):
        """모델 삭제 시 로깅"""
        company_name = obj.name
        try:
            super().delete_model(request, obj)
            logger.info(f"Admin에서 업체 삭제: {company_name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 업체 삭제 실패: {str(e)} - 업체: {company_name}")
            raise


@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    """
    업체 사용자 모델의 Django Admin 설정
    업체별 사용자를 효율적으로 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'username', 'company_link', 'role_badge', 
        'last_login_formatted', 'created_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'role', 'company', 'created_at', 'last_login'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'username', 'company__name'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'created_at', 'last_login'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'username', 'password', 'company')
        }),
        ('권한 설정', {
            'fields': ('role',)
        }),
        ('활동 정보', {
            'fields': ('last_login', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['username']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['role']  # 뱃지로 표시되므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-created_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['company']
    
    def company_link(self, obj):
        """소속 업체를 링크로 표시"""
        if obj.company:
            url = reverse('admin:companies_company_change', args=[obj.company.id])
            return format_html('<a href="{}">{}</a>', url, obj.company.name)
        return '-'
    company_link.short_description = '소속 업체'
    company_link.admin_order_field = 'company__name'
    
    def role_badge(self, obj):
        """역할을 뱃지 형태로 표시"""
        colors = {
            'admin': '#dc3545',   # 빨간색
            'staff': '#6c757d'    # 회색
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = '역할'
    
    def last_login_formatted(self, obj):
        """마지막 로그인 시간 포맷팅"""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return '로그인 기록 없음'
    last_login_formatted.short_description = '마지막 로그인'
    last_login_formatted.admin_order_field = 'last_login'
    
    def created_at_formatted(self, obj):
        """생성일시를 한국 시간으로 포맷팅"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = '생성일시'
    created_at_formatted.admin_order_field = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅"""
        action = '수정' if change else '생성'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 업체 사용자 {action}: {obj.username} ({obj.company.name}) - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 업체 사용자 {action} 실패: {str(e)} - 사용자: {obj.username}")
            raise


@admin.register(CompanyMessage)
class CompanyMessageAdmin(admin.ModelAdmin):
    """
    업체 메시지 모델의 Django Admin 설정
    업체에 발송된 메시지를 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'message_preview', 'message_type_badge', 'target_company',
        'sent_by_user', 'sent_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'is_bulk', 'sent_by', 'company', 'sent_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'message', 'company__name', 'sent_by__username'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'sent_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('메시지 내용', {
            'fields': ('message',)
        }),
        ('발송 설정', {
            'fields': ('is_bulk', 'company', 'sent_by')
        }),
        ('발송 정보', {
            'fields': ('id', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['message_preview']
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-sent_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['company', 'sent_by']
    
    def message_preview(self, obj):
        """메시지 내용 미리보기"""
        preview = obj.message[:50]
        if len(obj.message) > 50:
            preview += '...'
        return preview
    message_preview.short_description = '메시지 내용'
    
    def message_type_badge(self, obj):
        """메시지 타입을 뱃지로 표시"""
        if obj.is_bulk:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">일괄 발송</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 2px 8px; '
                'border-radius: 3px; font-size: 12px;">개별 발송</span>'
            )
    message_type_badge.short_description = '발송 타입'
    
    def target_company(self, obj):
        """수신 업체 표시"""
        if obj.is_bulk:
            return '전체 업체'
        elif obj.company:
            url = reverse('admin:companies_company_change', args=[obj.company.id])
            return format_html('<a href="{}">{}</a>', url, obj.company.name)
        return '-'
    target_company.short_description = '수신 업체'
    
    def sent_by_user(self, obj):
        """발송자 표시"""
        if obj.sent_by:
            return obj.sent_by.username
        return '시스템'
    sent_by_user.short_description = '발송자'
    sent_by_user.admin_order_field = 'sent_by__username'
    
    def sent_at_formatted(self, obj):
        """발송일시를 한국 시간으로 포맷팅"""
        return obj.sent_at.strftime('%Y-%m-%d %H:%M')
    sent_at_formatted.short_description = '발송일시'
    sent_at_formatted.admin_order_field = 'sent_at'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅 및 발송자 자동 설정"""
        # 발송자가 설정되지 않은 경우 현재 사용자로 설정
        if not obj.sent_by:
            obj.sent_by = request.user
        
        action = '수정' if change else '발송'
        try:
            super().save_model(request, obj, form, change)
            message_type = '일괄' if obj.is_bulk else '개별'
            target = '전체 업체' if obj.is_bulk else obj.company.name if obj.company else '없음'
            logger.info(f"Admin에서 {message_type} 메시지 {action}: {target} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 메시지 {action} 실패: {str(e)} - 관리자: {request.user}")
            raise
    
    def has_delete_permission(self, request, obj=None):
        """메시지 삭제 권한 제한 (발송된 메시지는 기본적으로 삭제 불가)"""
        # 필요에 따라 특정 권한이 있는 사용자만 삭제 가능하도록 설정
        return request.user.is_superuser
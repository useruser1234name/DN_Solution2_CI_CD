"""
업체 관리 시스템 Django Admin 설정

이 모듈은 Django Admin에서 업체 및 사용자 관리를 위한 설정을 제공합니다.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, CompanyUser, CompanyMessage


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """업체 관리 Admin"""
    
    list_display = [
        'code', 'name', 'type', 'parent_company', 'status', 
        'visible', 'users_count', 'created_at'
    ]
    list_filter = ['type', 'status', 'visible', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'type', 'parent_company')
        }),
        ('운영 설정', {
            'fields': ('status', 'visible', 'default_courier')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def users_count(self, obj):
        """소속 사용자 수"""
        count = obj.companyuser_set.count()
        return format_html(
            '<a href="{}?company__id__exact={}">{}명</a>',
            reverse('admin:companies_companyuser_changelist'),
            obj.id,
            count
        )
    users_count.short_description = '소속 사용자'
    
    def get_queryset(self, request):
        """권한에 따른 쿼리셋 필터링"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        from .utils import get_accessible_company_ids
        accessible_ids = get_accessible_company_ids(request.user)
        return qs.filter(id__in=accessible_ids)


@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    """업체 사용자 관리 Admin"""
    
    list_display = [
        'username', 'company', 'role', 'status', 'is_approved',
        'last_login', 'created_at'
    ]
    list_filter = ['role', 'status', 'is_approved', 'company__type', 'created_at']
    search_fields = ['username', 'company__name']
    readonly_fields = ['created_at', 'last_login']
    ordering = ['-created_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('username', 'django_user', 'company', 'role')
        }),
        ('승인 상태', {
            'fields': ('is_approved', 'status')
        }),
        ('활동 정보', {
            'fields': ('last_login', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """권한에 따른 쿼리셋 필터링"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        from .utils import get_accessible_company_ids
        accessible_ids = get_accessible_company_ids(request.user)
        return qs.filter(company__id__in=accessible_ids)
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 추가 처리"""
        if not change:  # 새로 생성하는 경우
            # Django User 생성
            from django.contrib.auth.models import User
            from django.contrib.auth.hashers import make_password
            import secrets
            import string
            
            if not obj.django_user:
                # 안전한 임시 비밀번호 생성
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
                
                django_user = User.objects.create_user(
                    username=obj.username,
                    password=temp_password
                )
                obj.django_user = django_user
                
                # 관리자에게 임시 비밀번호 알림 (로그에 기록)
                import logging
                logger = logging.getLogger('companies')
                logger.info(f"[CompanyUserAdmin] Django User 생성됨 - 사용자: {obj.username}, 임시 비밀번호는 별도 채널로 전달 필요")
        
        super().save_model(request, obj, form, change)


@admin.register(CompanyMessage)
class CompanyMessageAdmin(admin.ModelAdmin):
    """업체 메시지 관리 Admin"""
    
    list_display = [
        'message_type', 'company', 'is_bulk', 'sent_by', 'sent_at'
    ]
    list_filter = ['message_type', 'is_bulk', 'sent_at']
    search_fields = ['message', 'company__name', 'sent_by__username']
    readonly_fields = ['sent_at']
    ordering = ['-sent_at']
    
    fieldsets = (
        ('메시지 정보', {
            'fields': ('message', 'message_type', 'is_bulk')
        }),
        ('발송 정보', {
            'fields': ('sent_by', 'company', 'sent_at')
        }),
    )
    
    def get_queryset(self, request):
        """권한에 따른 쿼리셋 필터링"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company__status=True)

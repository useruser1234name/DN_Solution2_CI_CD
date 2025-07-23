# policies/admin.py
import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Policy, PolicyAssignment

logger = logging.getLogger('policies')


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    """
    정책 모델의 Django Admin 설정
    정책 정보를 효율적으로 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'title', 'form_type_badge', 'rebate_info', 'expose_badge',
        'assignment_count', 'created_by_user', 'created_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'form_type', 'expose', 'created_by', 'created_at', 'updated_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'title', 'description', 'created_by__username'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'html_content_preview', 'assignment_count_detail',
        'created_at', 'updated_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'title', 'description', 'form_type')
        }),
        ('리베이트 설정', {
            'fields': ('rebate_agency', 'rebate_retail')
        }),
        ('노출 설정', {
            'fields': ('expose', 'created_by')
        }),
        ('HTML 내용', {
            'fields': ('html_content_preview',),
            'classes': ('collapse',)
        }),
        ('배정 정보', {
            'fields': ('assignment_count_detail',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['title']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['expose']  # 뱃지로 표시되므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-created_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['created_by']
    
    def form_type_badge(self, obj):
        """신청서 타입을 뱃지 형태로 표시"""
        colors = {
            'general': '#28a745',   # 녹색
            'link': '#007bff',      # 파란색
            'offline': '#6c757d',   # 회색
            'egg': '#ffc107'        # 노란색
        }
        color = colors.get(obj.form_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            'black' if obj.form_type == 'egg' else 'white',
            obj.get_form_type_display()
        )
    form_type_badge.short_description = '신청서 타입'
    
    def rebate_info(self, obj):
        """리베이트 정보를 요약하여 표시"""
        agency = f"{obj.rebate_agency:,}원" if obj.rebate_agency > 0 else "0원"
        retail = f"{obj.rebate_retail:,}원" if obj.rebate_retail > 0 else "0원"
        return f"대리점: {agency} / 판매점: {retail}"
    rebate_info.short_description = '리베이트 정보'
    
    def expose_badge(self, obj):
        """노출 여부를 아이콘으로 표시"""
        if obj.expose:
            return format_html(
                '<span style="color: green; font-size: 16px;">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-size: 16px;">✗</span>'
            )
    expose_badge.short_description = '노출'
    
    def assignment_count(self, obj):
        """배정된 업체 수 표시"""
        try:
            count = obj.get_assignment_count()
            if count > 0:
                url = reverse('admin:policies_policyassignment_changelist')
                return format_html(
                    '<a href="{}?policy__id__exact={}">{} 개</a>',
                    url, obj.id, count
                )
            return '0 개'
        except Exception as e:
            logger.warning(f"배정 수 조회 중 오류: {str(e)} - 정책: {obj.title}")
            return '오류'
    assignment_count.short_description = '배정 업체 수'
    
    def assignment_count_detail(self, obj):
        """상세 페이지에서 배정 업체 목록 표시"""
        if obj.pk:
            assignments = obj.assignments.select_related('company').all()
            if assignments:
                assignment_list = []
                for assignment in assignments:
                    assignment_url = reverse('admin:policies_policyassignment_change', args=[assignment.id])
                    rebate_info = f" ({assignment.get_effective_rebate():,}원)" if assignment.get_effective_rebate() > 0 else ""
                    assignment_list.append(
                        f'<a href="{assignment_url}">{assignment.company.name} '
                        f'({assignment.company.get_type_display()}){rebate_info}</a>'
                    )
                return mark_safe('<br>'.join(assignment_list))
            return '배정된 업체 없음'
        return '저장 후 표시됩니다'
    assignment_count_detail.short_description = '배정 업체 목록'
    
    def created_by_user(self, obj):
        """생성자 표시"""
        if obj.created_by:
            return obj.created_by.username
        return '시스템'
    created_by_user.short_description = '생성자'
    created_by_user.admin_order_field = 'created_by__username'
    
    def created_at_formatted(self, obj):
        """생성일시를 한국 시간으로 포맷팅"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = '생성일시'
    created_at_formatted.admin_order_field = 'created_at'
    
    def html_content_preview(self, obj):
        """HTML 내용 미리보기"""
        if obj.html_content:
            preview = obj.html_content[:200]
            if len(obj.html_content) > 200:
                preview += '...'
            return format_html(
                '<div style="max-height: 200px; overflow-y: scroll; border: 1px solid #ccc; '
                'padding: 10px; background-color: #f8f9fa;"><pre>{}</pre></div>',
                preview
            )
        return '생성된 HTML이 없습니다'
    html_content_preview.short_description = 'HTML 내용 미리보기'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅 및 생성자 자동 설정"""
        # 생성자가 설정되지 않은 경우 현재 사용자로 설정
        if not obj.created_by:
            obj.created_by = request.user
        
        action = '수정' if change else '생성'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 정책 {action}: {obj.title} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 정책 {action} 실패: {str(e)} - 정책: {obj.title}")
            raise
    
    def delete_model(self, request, obj):
        """모델 삭제 시 로깅"""
        policy_title = obj.title
        try:
            super().delete_model(request, obj)
            logger.info(f"Admin에서 정책 삭제: {policy_title} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 정책 삭제 실패: {str(e)} - 정책: {policy_title}")
            raise
    
    actions = ['generate_html_for_selected', 'toggle_expose_for_selected']
    
    def generate_html_for_selected(self, request, queryset):
        """선택된 정책들의 HTML 재생성"""
        updated_count = 0
        for policy in queryset:
            try:
                policy.html_content = None
                policy.generate_html_content()
                policy.save()
                updated_count += 1
                logger.info(f"Admin에서 정책 HTML 재생성: {policy.title}")
            except Exception as e:
                logger.error(f"Admin에서 정책 HTML 재생성 실패: {str(e)} - 정책: {policy.title}")
        
        self.message_user(request, f'{updated_count}개 정책의 HTML이 재생성되었습니다.')
    generate_html_for_selected.short_description = "선택된 정책의 HTML 재생성"
    
    def toggle_expose_for_selected(self, request, queryset):
        """선택된 정책들의 노출 상태 전환"""
        updated_count = 0
        for policy in queryset:
            try:
                policy.toggle_expose()
                updated_count += 1
                logger.info(f"Admin에서 정책 노출 상태 전환: {policy.title}")
            except Exception as e:
                logger.error(f"Admin에서 정책 노출 상태 전환 실패: {str(e)} - 정책: {policy.title}")
        
        self.message_user(request, f'{updated_count}개 정책의 노출 상태가 전환되었습니다.')
    toggle_expose_for_selected.short_description = "선택된 정책의 노출 상태 전환"


@admin.register(PolicyAssignment)
class PolicyAssignmentAdmin(admin.ModelAdmin):
    """
    정책 배정 모델의 Django Admin 설정
    정책과 업체 간의 배정 관계를 관리하기 위한 인터페이스 제공
    """
    
    # 목록 페이지에서 보여질 필드들
    list_display = [
        'policy_link', 'company_link', 'effective_rebate_formatted',
        'rebate_source_badge', 'expose_to_child_badge', 'assigned_at_formatted'
    ]
    
    # 목록 페이지에서 필터링 가능한 필드들
    list_filter = [
        'expose_to_child', 'policy__form_type', 'company__type',
        'assigned_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = [
        'policy__title', 'company__name'
    ]
    
    # 읽기 전용 필드들
    readonly_fields = [
        'id', 'effective_rebate_info', 'assigned_at'
    ]
    
    # 상세 페이지 필드 배치
    fieldsets = (
        ('배정 정보', {
            'fields': ('id', 'policy', 'company')
        }),
        ('리베이트 설정', {
            'fields': ('custom_rebate', 'effective_rebate_info')
        }),
        ('노출 설정', {
            'fields': ('expose_to_child',)
        }),
        ('시간 정보', {
            'fields': ('assigned_at',),
            'classes': ('collapse',)
        }),
    )
    
    # 목록에서 클릭 가능한 필드
    list_display_links = ['policy_link']
    
    # 목록에서 편집 가능한 필드
    # list_editable = ['expose_to_child']  # 뱃지로 표시되므로 비활성화
    
    # 페이지당 표시할 항목 수
    list_per_page = 25
    
    # 정렬 기준
    ordering = ['-assigned_at']
    
    # 외래키 필드의 선택 최적화
    raw_id_fields = ['policy', 'company']
    
    def policy_link(self, obj):
        """정책을 링크로 표시"""
        if obj.policy:
            url = reverse('admin:policies_policy_change', args=[obj.policy.id])
            return format_html(
                '<a href="{}">{}</a>',
                url, obj.policy.title
            )
        return '-'
    policy_link.short_description = '정책'
    policy_link.admin_order_field = 'policy__title'
    
    def company_link(self, obj):
        """업체를 링크로 표시"""
        if obj.company:
            url = reverse('admin:companies_company_change', args=[obj.company.id])
            return format_html(
                '<a href="{}">{} ({})</a>',
                url, obj.company.name, obj.company.get_type_display()
            )
        return '-'
    company_link.short_description = '업체'
    company_link.admin_order_field = 'company__name'
    
    def effective_rebate_formatted(self, obj):
        """실제 적용 리베이트 금액 포맷팅"""
        try:
            rebate = obj.get_effective_rebate()
            if rebate > 0:
                return f"{rebate:,}원"
            return "0원"
        except Exception as e:
            logger.warning(f"리베이트 정보 조회 중 오류: {str(e)}")
            return "오류"
    effective_rebate_formatted.short_description = '적용 리베이트'
    
    def rebate_source_badge(self, obj):
        """리베이트 출처를 뱃지로 표시"""
        try:
            source = obj.get_rebate_source()
            if source == "커스텀":
                return format_html(
                    '<span style="background-color: #dc3545; color: white; padding: 2px 6px; '
                    'border-radius: 3px; font-size: 11px;">커스텀</span>'
                )
            else:
                return format_html(
                    '<span style="background-color: #6c757d; color: white; padding: 2px 6px; '
                    'border-radius: 3px; font-size: 11px;">기본값</span>'
                )
        except Exception as e:
            logger.warning(f"리베이트 출처 조회 중 오류: {str(e)}")
            return '오류'
    rebate_source_badge.short_description = '출처'
    
    def expose_to_child_badge(self, obj):
        """하위 노출 여부를 아이콘으로 표시"""
        if obj.expose_to_child:
            return format_html(
                '<span style="color: green; font-size: 16px;">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-size: 16px;">✗</span>'
            )
    expose_to_child_badge.short_description = '하위 노출'
    
    def assigned_at_formatted(self, obj):
        """배정일시를 한국 시간으로 포맷팅"""
        return obj.assigned_at.strftime('%Y-%m-%d %H:%M')
    assigned_at_formatted.short_description = '배정일시'
    assigned_at_formatted.admin_order_field = 'assigned_at'
    
    def effective_rebate_info(self, obj):
        """상세 페이지에서 리베이트 정보 표시"""
        if obj.pk:
            try:
                effective = obj.get_effective_rebate()
                source = obj.get_rebate_source()
                
                info = f"적용 리베이트: {effective:,}원 ({source})"
                
                if source == "기본값":
                    if obj.company.type == 'agency':
                        base_rebate = obj.policy.rebate_agency
                    else:
                        base_rebate = obj.policy.rebate_retail
                    info += f"<br>기본 리베이트: {base_rebate:,}원"
                
                if obj.custom_rebate is not None:
                    info += f"<br>커스텀 리베이트: {obj.custom_rebate:,}원"
                
                return mark_safe(info)
            except Exception as e:
                return f"오류: {str(e)}"
        return '저장 후 표시됩니다'
    effective_rebate_info.short_description = '리베이트 상세 정보'
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 로깅"""
        action = '수정' if change else '배정'
        try:
            super().save_model(request, obj, form, change)
            logger.info(f"Admin에서 정책 {action}: {obj.policy.title} → {obj.company.name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 정책 {action} 실패: {str(e)} - {obj.policy.title} → {obj.company.name}")
            raise
    
    def delete_model(self, request, obj):
        """모델 삭제 시 로깅"""
        policy_title = obj.policy.title
        company_name = obj.company.name
        try:
            super().delete_model(request, obj)
            logger.info(f"Admin에서 정책 배정 해제: {policy_title} → {company_name} - 관리자: {request.user}")
        except Exception as e:
            logger.error(f"Admin에서 정책 배정 해제 실패: {str(e)} - {policy_title} → {company_name}")
            raise
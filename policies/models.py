"""
정책 관리 시스템 모델

이 모듈은 스마트기기 판매 정책 관리를 위한 모델들을 정의합니다.
리베이트 설정, HTML 자동 생성, 접수 방식, 안내사항 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.html import format_html
from companies.models import Company

logger = logging.getLogger('policies')


class Policy(models.Model):
    """
    스마트기기 판매 정책 관리 모델
    정책 생성과 HTML 자동 생성 기능 제공
    """
    
    # 신청서 양식 타입 선택지
    FORM_TYPE_CHOICES = [
        ('general', '일반 신청서'),
        ('link', '링크 신청서'),
        ('offline', '오프라인 신청서'),
        ('egg', '에그 신청서'),
    ]
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
        ('all', '전체'),
    ]
    
    # 가입유형 선택지
    JOIN_TYPE_CHOICES = [
        ('number_transfer', '번호이동'),
        ('device_change', '기기변경'),
        ('new_subscription', '신규가입'),
        ('all', '전체'),
    ]
    
    # 가입기간 선택지
    CONTRACT_PERIOD_CHOICES = [
        ('12', '12개월'),
        ('24', '24개월'),
        ('36', '36개월'),
        ('all', '전체'),
    ]
    
    # 정책 타입 선택지
    TYPE_CHOICES = [
        ('normal', '일반'),
        ('special', '특별'),
        ('event', '이벤트'),
    ]
    
    # 정책 상태 선택지
    STATUS_CHOICES = [
        ('draft', '초안'),
        ('active', '활성'),
        ('inactive', '비활성'),
        ('expired', '만료'),
    ]
    
    # 기본 키는 UUID 사용
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="정책의 고유 식별자"
    )
    
    # 정책 기본 정보
    title = models.CharField(
        max_length=200,
        verbose_name="정책 제목",
        help_text="정책의 제목을 입력하세요"
    )
    
    description = models.TextField(
        verbose_name="정책 설명",
        help_text="정책의 상세 설명을 입력하세요"
    )
    
    # 신청서 양식 타입
    form_type = models.CharField(
        max_length=20,
        choices=FORM_TYPE_CHOICES,
        default='general',
        verbose_name="신청서 타입",
        help_text="사용할 신청서 양식을 선택하세요"
    )
    
    # 정책 타입 및 상태
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='normal',
        verbose_name="정책 타입",
        help_text="정책의 타입을 선택하세요"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="정책 상태",
        help_text="정책의 상태를 선택하세요"
    )
    
    # 통신사 및 가입기간 필터링
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="적용할 통신사를 선택하세요"
    )
    
    join_type = models.CharField(
        max_length=20,
        choices=JOIN_TYPE_CHOICES,
        default='all',
        verbose_name="가입유형",
        help_text="적용할 가입유형을 선택하세요"
    )
    
    contract_period = models.CharField(
        max_length=10,
        choices=CONTRACT_PERIOD_CHOICES,
        default='all',
        verbose_name="가입기간",
        help_text="적용할 가입기간을 선택하세요"
    )
    
    # 리베이트 설정
    rebate_agency = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="대리점 리베이트",
        help_text="대리점에 지급할 리베이트 금액"
    )
    
    rebate_retail = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="판매점 리베이트",
        help_text="판매점에 지급할 리베이트 금액"
    )
    
    # 정책 노출 설정
    expose = models.BooleanField(
        default=True,
        verbose_name="정책 노출",
        help_text="프론트엔드에 정책을 노출할지 여부"
    )
    
    # 프리미엄 마켓 노출 설정
    premium_market_expose = models.BooleanField(
        default=False,
        verbose_name="프리미엄 마켓 노출",
        help_text="프리미엄 마켓에 자동 노출할지 여부"
    )
    
    # 정책 활성화 여부
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화 여부",
        help_text="정책의 활성화 여부"
    )
    
    # HTML 상세페이지 자동 생성 내용
    html_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="HTML 내용",
        help_text="자동 생성된 HTML 상세페이지 내용"
    )

    # 프론트엔드 라우팅/외부 문서 링크 등 정책 전용 URL
    external_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="정책 URL",
        help_text="정책 상세 안내 또는 외부 라우팅 URL (선택)"
    )
    
    # 정책 생성자
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="생성자",
        help_text="정책을 생성한 관리자"
    )
    
    # 시간 정보
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "정책"
        verbose_name_plural = "정책 목록"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['form_type', 'expose']),
            models.Index(fields=['title']),
            models.Index(fields=['carrier', 'contract_period']),
            models.Index(fields=['premium_market_expose']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_form_type_display()})"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.title or not self.title.strip():
            raise ValidationError("정책 제목은 필수 입력 사항입니다.")
        
        if not self.description or not self.description.strip():
            raise ValidationError("정책 설명은 필수 입력 사항입니다.")
        
        # 리베이트 금액 검증
        if self.rebate_agency < 0:
            raise ValidationError("대리점 리베이트는 0 이상이어야 합니다.")
        
        if self.rebate_retail < 0:
            raise ValidationError("판매점 리베이트는 0 이상이어야 합니다.")
        
        # 중복 제목 검사
        existing = Policy.objects.filter(title=self.title).exclude(id=self.id)
        if existing.exists():
            raise ValidationError("동일한 제목의 정책이 이미 존재합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 HTML 자동 생성 처리"""
        is_new = self.pk is None
        skip_html_generation = kwargs.pop('skip_html_generation', False)
        
        try:
            self.clean()
            
            # HTML 자동 생성 (skip_html_generation이 False일 때만)
            if not skip_html_generation and not self.html_content:
                self.generate_html_content()
            
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 정책이 생성되었습니다: {self.title} ({self.form_type})")
            else:
                logger.info(f"정책이 수정되었습니다: {self.title} (ID: {self.id})")
        
        except Exception as e:
            logger.error(f"정책 저장 중 오류 발생: {str(e)} - 정책: {self.title}")
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅 처리"""
        policy_title = self.title
        policy_id = self.id
        
        try:
            # 연관된 배정 정보가 있는지 확인
            assignments_count = self.assignments.count()
            if assignments_count > 0:
                logger.warning(f"배정된 업체가 있는 정책 삭제 시도: {policy_title} (배정 수: {assignments_count})")
                raise ValidationError(f"이 정책은 {assignments_count}개 업체에 배정되어 있어 삭제할 수 없습니다.")
            
            super().delete(*args, **kwargs)
            logger.info(f"정책이 삭제되었습니다: {policy_title} (ID: {policy_id})")
        
        except Exception as e:
            logger.error(f"정책 삭제 중 오류 발생: {str(e)} - 정책: {policy_title}")
            raise
    
    def generate_html_content(self):
        """
        정책 데이터를 기반으로 HTML 상세페이지 자동 생성
        """
        try:
            # HTML 템플릿 컨텍스트 준비
            context = {
                'policy': self,
                'title': self.title,
                'description': self.description,
                'form_type_display': self.get_form_type_display(),
                'carrier_display': self.get_carrier_display(),
                'contract_period_display': self.get_contract_period_display(),
                'rebate_agency': self.rebate_agency,
                'rebate_retail': self.rebate_retail,
                'created_at': self.created_at,
                'created_by': self.created_by,
                'created_by_username': self.created_by.username if self.created_by else '시스템',
            }
            
            # 정책 타입에 따른 템플릿 선택
            template_name = f'policies/policy_{self.form_type}.html'
            
            # HTML 생성 시도 (템플릿이 없으면 기본 템플릿 사용)
            try:
                self.html_content = render_to_string(template_name, context)
            except:
                # 기본 템플릿 사용
                self.html_content = self._generate_default_html()
            
            logger.info(f"정책 HTML 자동 생성 완료: {self.title}")
            
        except Exception as e:
            logger.error(f"HTML 자동 생성 실패: {str(e)} - 정책: {self.title}")
            self.html_content = self._generate_default_html()
    
    def _generate_default_html(self):
        """기본 HTML 생성"""
        return f"""
        <div class="policy-detail">
            <h1>{self.title}</h1>
            <div class="policy-info">
                <p><strong>신청서 타입:</strong> {self.get_form_type_display()}</p>
                <p><strong>통신사:</strong> {self.get_carrier_display()}</p>
                <p><strong>가입기간:</strong> {self.get_contract_period_display()}</p>
                <p><strong>대리점 리베이트:</strong> {self.rebate_agency:,}원</p>
                <p><strong>판매점 리베이트:</strong> {self.rebate_retail:,}원</p>
            </div>
            <div class="policy-description">
                <h2>정책 설명</h2>
                <p>{self.description}</p>
            </div>
            <div class="policy-meta">
                <p>생성일: {self.created_at.strftime('%Y년 %m월 %d일') if self.created_at else 'N/A'}</p>
                {f'<p>생성자: {self.created_by.username}</p>' if self.created_by else '<p>생성자: 시스템</p>'}
            </div>
        </div>
        """
    
    def get_assignment_count(self):
        """배정된 업체 수 반환"""
        try:
            return self.assignments.count()
        except Exception as e:
            logger.warning(f"정책 배정 수 조회 중 오류: {str(e)} - 정책: {self.title}")
            return 0
    
    def get_assigned_companies(self):
        """이 정책이 배정된 업체 목록 반환"""
        return Company.objects.filter(policy_assignments__policy=self)
    
    def assign_to_companies(self, companies, custom_rebate=None, expose_to_child=True):
        """
        정책을 여러 업체에 일괄 배정
        
        Args:
            companies: Company 객체 리스트 또는 QuerySet
            custom_rebate: 커스텀 리베이트 (선택사항)
            expose_to_child: 하위 업체 노출 여부
        """
        assignments = []
        for company in companies:
            assignment, created = PolicyAssignment.objects.get_or_create(
                policy=self,
                company=company,
                defaults={
                    'custom_rebate': custom_rebate,
                    'expose_to_child': expose_to_child
                }
            )
            if not created:
                # 기존 배정이 있으면 업데이트
                assignment.custom_rebate = custom_rebate
                assignment.expose_to_child = expose_to_child
                assignment.save()
            assignments.append(assignment)
        
        logger.info(f"정책 '{self.title}'을 {len(assignments)}개 업체에 배정했습니다.")
        return assignments
    
    def assign_to_child_companies(self, parent_company, include_parent=False, custom_rebate=None, expose_to_child=True):
        """
        특정 상위 업체의 하위 업체들에 정책 배정
        
        Args:
            parent_company: 상위 업체 (Company 객체)
            include_parent: 상위 업체도 포함할지 여부
            custom_rebate: 커스텀 리베이트 (선택사항)
            expose_to_child: 하위 업체 노출 여부
        """
        # 하위 업체들 조회
        child_companies = Company.objects.filter(parent_company=parent_company)
        
        if include_parent:
            # 상위 업체도 포함
            target_companies = list(child_companies) + [parent_company]
        else:
            target_companies = list(child_companies)
        
        return self.assign_to_companies(target_companies, custom_rebate, expose_to_child)
    
    def assign_to_selected_companies(self, company_ids, custom_rebate=None, expose_to_child=True):
        """
        선택된 업체 ID들에 정책 배정
        
        Args:
            company_ids: 업체 ID 리스트
            custom_rebate: 커스텀 리베이트 (선택사항)
            expose_to_child: 하위 업체 노출 여부
        """
        companies = Company.objects.filter(id__in=company_ids)
        return self.assign_to_companies(companies, custom_rebate, expose_to_child)
    
    def remove_from_companies(self, companies):
        """
        정책을 여러 업체에서 일괄 제거
        
        Args:
            companies: Company 객체 리스트 또는 QuerySet
        """
        count = PolicyAssignment.objects.filter(
            policy=self,
            company__in=companies
        ).delete()[0]
        
        logger.info(f"정책 '{self.title}'을 {count}개 업체에서 제거했습니다.")
        return count
    
    def toggle_expose(self):
        """정책 노출 상태를 토글하는 메서드"""
        try:
            old_expose = self.expose
            self.expose = not self.expose
            self.save()
            
            expose_text = "노출" if self.expose else "비노출"
            logger.info(f"정책 노출 상태가 변경되었습니다: {self.title} - {expose_text}")
            
            return True
        
        except Exception as e:
            logger.error(f"정책 노출 상태 변경 중 오류 발생: {str(e)} - 정책: {self.title}")
            return False
    
    def toggle_premium_market_expose(self):
        """프리미엄 마켓 노출 상태를 토글하는 메서드"""
        try:
            self.premium_market_expose = not self.premium_market_expose
            self.save()
            
            expose_text = "노출" if self.premium_market_expose else "비노출"
            logger.info(f"프리미엄 마켓 노출 상태가 변경되었습니다: {self.title} - {expose_text}")
            
            return True
        
        except Exception as e:
            logger.error(f"프리미엄 마켓 노출 상태 변경 중 오류 발생: {str(e)} - 정책: {self.title}")
            return False
    
    def ensure_order_form(self, force_update=False):
        """
        정책에 최신 주문서 양식이 적용되어 있는지 확인하고,
        없거나 오래된 경우 최신 양식을 적용
        
        Args:
            force_update: 강제 업데이트 여부 (기본값: False)
            
        Returns:
            OrderFormTemplate 객체
        """
        from .utils.order_form_manager import OrderFormManager
        return OrderFormManager.ensure_latest_order_form(self, force=force_update)
    
    def update_order_form(self):
        """
        정책의 주문서 양식을 최신 버전으로 강제 업데이트
        
        Returns:
            업데이트된 OrderFormTemplate 객체 또는 None (양식이 없는 경우)
        """
        if hasattr(self, 'order_form'):
            from .utils.order_form_manager import OrderFormManager
            return OrderFormManager.update_order_form(self.order_form, force=True)
        else:
            logger.warning(f"정책 '{self.title}'에 주문서 양식이 없습니다.")
            return self.ensure_order_form()
    
    def get_order_form_status(self):
        """
        주문서 양식 상태 확인
        
        Returns:
            상태 정보를 담은 딕셔너리
        """
        if not hasattr(self, 'order_form'):
            return {
                'has_form': False,
                'message': '주문서 양식이 없습니다.',
                'fields_count': 0,
                'is_latest': False
            }
        
        from policies.form_builder import FormBuilder
        
        current_fields_count = self.order_form.fields.count()
        default_fields_count = len(FormBuilder.load_fields_from_config())
        is_latest = current_fields_count == default_fields_count
        
        return {
            'has_form': True,
            'message': '최신 주문서 양식이 적용되어 있습니다.' if is_latest else '주문서 양식 업데이트가 필요합니다.',
            'fields_count': current_fields_count,
            'is_latest': is_latest,
            'default_fields_count': default_fields_count
        }


class PolicyNotice(models.Model):
    """
    정책별 안내사항 모델
    고객 안내, 업체 공지, 정책 특이사항 등을 관리
    """
    
    NOTICE_TYPES = [
        ('customer', '고객 안내'),
        ('company', '업체 공지'),
        ('policy', '정책 특이사항'),
        ('general', '일반 안내'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="안내사항의 고유 식별자"
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='notices',
        verbose_name="정책",
        help_text="안내사항이 속한 정책"
    )
    
    notice_type = models.CharField(
        max_length=20,
        choices=NOTICE_TYPES,
        verbose_name="안내 유형",
        help_text="안내사항의 유형을 선택하세요"
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name="안내 제목",
        help_text="안내사항의 제목을 입력하세요"
    )
    
    content = models.TextField(
        verbose_name="안내 내용",
        help_text="안내사항의 상세 내용을 입력하세요"
    )
    
    is_important = models.BooleanField(
        default=False,
        verbose_name="중요 안내",
        help_text="중요한 안내사항인지 여부"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="표시 순서",
        help_text="안내사항의 표시 순서 (낮은 숫자가 먼저 표시)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "정책 안내사항"
        verbose_name_plural = "정책 안내사항 목록"
        ordering = ['policy', 'order', '-created_at']
        indexes = [
            models.Index(fields=['policy', 'notice_type']),
            models.Index(fields=['is_important']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.get_notice_type_display()}: {self.title}"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.title or not self.title.strip():
            raise ValidationError("안내 제목은 필수 입력 사항입니다.")
        
        if not self.content or not self.content.strip():
            raise ValidationError("안내 내용은 필수 입력 사항입니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 정책 안내사항이 생성되었습니다: {self.title} (정책: {self.policy.title})")
            else:
                logger.info(f"정책 안내사항이 수정되었습니다: {self.title} (정책: {self.policy.title})")
        
        except Exception as e:
            logger.error(f"정책 안내사항 저장 중 오류 발생: {str(e)} - 안내: {self.title}")
            raise


class PolicyAssignment(models.Model):
    """
    정책을 특정 업체에 배정/공유하는 모델
    업체별 커스텀 리베이트 설정 및 하위 노출 관리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="배정의 고유 식별자"
    )
    
    # 정책 연결 (Foreign Key)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="정책",
        help_text="배정할 정책"
    )
    
    # 업체 연결 (Foreign Key)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='policy_assignments',
        verbose_name="업체",
        help_text="정책을 배정받을 업체"
    )
    
    # 업체별 커스텀 리베이트 설정
    custom_rebate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="커스텀 리베이트",
        help_text="해당 업체에 특별히 적용할 리베이트 (빈 값이면 정책 기본값 사용)"
    )
    
    # 하위 업체에 노출 여부
    expose_to_child = models.BooleanField(
        default=True,
        verbose_name="하위 노출",
        help_text="하위 업체에 이 정책을 노출할지 여부"
    )
    
    # 배정일시
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="배정일시"
    )
    
    # 할당된 회사 이름
    assigned_to_name = models.CharField(
        max_length=200,
        verbose_name="할당된 회사 이름",
        help_text="정책이 할당된 회사의 이름",
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = "정책 배정"
        verbose_name_plural = "정책 배정 목록"
        ordering = ['-assigned_at']
        # 동일 정책을 같은 업체에 중복 배정 방지
        unique_together = ['policy', 'company']
        indexes = [
            models.Index(fields=['policy', 'company']),
            models.Index(fields=['company', 'expose_to_child']),
            models.Index(fields=['assigned_at']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} → {self.company.name}"
    
    def clean(self):
        """모델 데이터 검증"""
        # 커스텀 리베이트 검증
        if self.custom_rebate is not None and self.custom_rebate < 0:
            raise ValidationError("커스텀 리베이트는 0 이상이어야 합니다.")
        
        # 비활성 업체에 배정 방지
        if self.company and not self.company.status:
            raise ValidationError("운영 중단된 업체에는 정책을 배정할 수 없습니다.")
        
        # 비노출 정책 배정 경고 (에러는 아니지만 로깅)
        if self.policy and not self.policy.expose:
            logger.warning(f"비노출 정책을 배정하려고 합니다: {self.policy.title} → {self.company.name}")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                rebate_info = f" (커스텀 리베이트: {self.custom_rebate})" if self.custom_rebate else ""
                logger.info(f"정책이 업체에 배정되었습니다: {self.policy.title} → {self.company.name}{rebate_info}")
            else:
                logger.info(f"정책 배정이 수정되었습니다: {self.policy.title} → {self.company.name}")
            
            # assigned_to_name 필드 업데이트 (중복 저장 방지)
            if self.company and not self.assigned_to_name:
                self.assigned_to_name = self.company.name
                super().save(update_fields=['assigned_to_name'])
        
        except Exception as e:
            logger.error(f"정책 배정 저장 중 오류 발생: {str(e)} - {self.policy.title} → {self.company.name}")
            raise
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅 처리"""
        policy_title = self.policy.title
        company_name = self.company.name
        
        try:
            super().delete(*args, **kwargs)
            logger.info(f"정책 배정이 해제되었습니다: {policy_title} → {company_name}")
        
        except Exception as e:
            logger.error(f"정책 배정 해제 중 오류 발생: {str(e)} - {policy_title} → {company_name}")
            raise
    
    def get_effective_rebate(self):
        """
        효과적인 리베이트 금액 반환
        커스텀 리베이트가 설정되어 있으면 그 값을, 없으면 정책 기본값을 사용
        """
        if self.custom_rebate is not None:
            return self.custom_rebate
        
        # 업체 타입에 따른 기본 리베이트 반환
        if self.company.type == 'agency':
            return self.policy.rebate_agency
        elif self.company.type == 'retail':
            return self.policy.rebate_retail
        
        return 0.00
    
    def get_rebate_source(self):
        """리베이트 출처 반환 (커스텀/기본값 구분)"""
        if self.custom_rebate is not None:
            return "커스텀"
        return "기본값"


class PolicyExposure(models.Model):
    """
    정책 노출 관리 모델
    본사가 협력사 및 하위 판매점에 정책을 노출하는 것을 관리
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='exposures', verbose_name='정책')
    agency = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='exposed_policies', verbose_name='노출 업체')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    exposed_at = models.DateTimeField(auto_now_add=True, verbose_name='노출 시작일')
    exposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='노출 설정자')
    
    class Meta:
        unique_together = ['policy', 'agency']
        verbose_name = '정책 노출'
        verbose_name_plural = '정책 노출 관리'
        ordering = ['-exposed_at']
    
    def __str__(self):
        return f"{self.policy.title} → {self.agency.name}"
    
    def clean(self):
        """유효성 검증"""
        # 협력사 및 판매점 타입 검증 (본사는 제외)
        if self.agency and self.agency.type not in ['agency', 'retail']:
            raise ValidationError("협력사 또는 판매점에만 정책을 노출할 수 있습니다.")
        
        # 비활성 업체에 노출 방지
        if self.agency and not self.agency.status:
            raise ValidationError("운영 중단된 업체에는 정책을 노출할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"정책이 협력사에 노출되었습니다: {self.policy.title} → {self.agency.name}")
            else:
                logger.info(f"정책 노출이 수정되었습니다: {self.policy.title} → {self.agency.name}")
        
        except Exception as e:
            logger.error(f"정책 노출 저장 중 오류 발생: {str(e)} - {self.policy.title} → {self.agency.name}")
            raise


class AgencyRebate(models.Model):
    """
    협력사 리베이트 설정 모델
    협력사가 판매점에 제공할 리베이트를 설정
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_exposure = models.ForeignKey(PolicyExposure, on_delete=models.CASCADE, related_name='rebates', verbose_name='노출된 정책')
    retail_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='agency_rebates', verbose_name='판매점')
    rebate_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='리베이트 금액')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        unique_together = ['policy_exposure', 'retail_company']
        verbose_name = '협력사 리베이트'
        verbose_name_plural = '협력사 리베이트 설정'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.policy_exposure.policy.title} → {self.retail_company.name}: {self.rebate_amount}원"
    
    def clean(self):
        """유효성 검증"""
        # 판매점 타입 검증
        if self.retail_company and self.retail_company.type != 'retail':
            raise ValidationError("판매점에만 리베이트를 설정할 수 있습니다.")
        
        # 리베이트 금액 검증
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
        
        # 비활성 업체에 리베이트 설정 방지
        if self.retail_company and not self.retail_company.status:
            raise ValidationError("운영 중단된 업체에는 리베이트를 설정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"협력사 리베이트가 설정되었습니다: {self.policy_exposure.policy.title} → {self.retail_company.name}: {self.rebate_amount}원")
            else:
                logger.info(f"협력사 리베이트가 수정되었습니다: {self.policy_exposure.policy.title} → {self.retail_company.name}: {self.rebate_amount}원")
        
        except Exception as e:
            logger.error(f"협력사 리베이트 저장 중 오류 발생: {str(e)}")
            raise


class AgencyRebateMatrix(models.Model):
    """
    협력사 리베이트 매트릭스 모델
    협력사가 판매점에게 제공할 리베이트 매트릭스를 관리
    """
    
    # 요금제 범위 선택지 (RebateMatrix와 동일)
    PLAN_RANGE_CHOICES = [
        (11000, '11K'),
        (22000, '22K'),
        (33000, '33K'),
        (44000, '44K'),
        (55000, '55K'),
        (66000, '66K'),
        (77000, '77K'),
        (88000, '88K'),
        (99000, '99K'),
        (110000, '110K'),
        (121000, '121K'),
        (132000, '132K'),
        (143000, '143K'),
        (154000, '154K'),
        (165000, '165K'),
    ]
    
    # 가입기간 선택지 (RebateMatrix와 동일)
    CONTRACT_PERIOD_CHOICES = [
        (12, '12개월'),
        (24, '24개월'),
        (36, '36개월'),
        (48, '48개월'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="협력사 리베이트 매트릭스의 고유 식별자"
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='agency_rebate_matrix',
        verbose_name="정책",
        help_text="리베이트 매트릭스가 속한 정책"
    )
    
    agency = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='rebate_matrices',
        verbose_name="협력사",
        help_text="리베이트를 설정하는 협력사"
    )
    
    # 통신사 선택지 (RebateMatrix와 동일)
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
        ('all', '전체'),
    ]
    
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="리베이트가 적용될 통신사"
    )
    
    plan_range = models.IntegerField(
        choices=PLAN_RANGE_CHOICES,
        verbose_name="요금제 금액",
        help_text="리베이트가 적용될 요금제 금액 (K 단위)"
    )
    
    contract_period = models.IntegerField(
        choices=CONTRACT_PERIOD_CHOICES,
        verbose_name="계약기간",
        help_text="리베이트가 적용될 계약기간 (개월)"
    )
    
    rebate_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="리베이트 금액",
        help_text="해당 조건의 리베이트 금액"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "협력사 리베이트 매트릭스"
        verbose_name_plural = "협력사 리베이트 매트릭스"
        ordering = ['policy', 'agency', 'plan_range', 'contract_period']
        unique_together = ['policy', 'agency', 'carrier', 'plan_range', 'contract_period']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['agency']),
            models.Index(fields=['policy', 'agency']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.agency.name} - {self.get_plan_range_display()} - {self.get_contract_period_display()}: {self.rebate_amount:,}원"
    
    def clean(self):
        """모델 데이터 검증"""
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
        
        # 협력사 타입 검증
        if self.agency and self.agency.type != 'agency':
            raise ValidationError("협력사만 리베이트 매트릭스를 설정할 수 있습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"협력사 리베이트 매트릭스가 생성되었습니다: {self}")
            else:
                logger.info(f"협력사 리베이트 매트릭스가 수정되었습니다: {self}")
        
        except Exception as e:
            logger.error(f"협력사 리베이트 매트릭스 저장 중 오류 발생: {str(e)}")
            raise


class CommissionMatrix(models.Model):
    """
    수수료 매트릭스 모델 (기존 RebateMatrix에서 이름 변경)
    통신사별 요금제와 가입기간에 따른 수수료 금액을 관리
    """
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
        ('all', '전체'),
    ]
    
    # 요금제 범위 선택지 (동적으로 확장 가능)
    PLAN_RANGE_CHOICES = [
        (11000, '11K'),
        (22000, '22K'),
        (33000, '33K'),
        (44000, '44K'),
        (55000, '55K'),
        (66000, '66K'),
        (77000, '77K'),
        (88000, '88K'),
        (99000, '99K'),
        (110000, '110K'),  # 확장 가능
        (121000, '121K'),
        (132000, '132K'),
        (143000, '143K'),
        (154000, '154K'),
        (165000, '165K'),
    ]
    
    # 가입기간 선택지 (동적으로 확장 가능)
    CONTRACT_PERIOD_CHOICES = [
        (12, '12개월'),
        (24, '24개월'),
        (36, '36개월'),  # 확장 가능
        (48, '48개월'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="리베이트 매트릭스의 고유 식별자"
    )
    
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='rebate_matrix',
        verbose_name="정책",
        help_text="리베이트 매트릭스가 속한 정책"
    )
    
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="리베이트가 적용될 통신사"
    )
    
    plan_range = models.IntegerField(
        choices=PLAN_RANGE_CHOICES,
        verbose_name="요금제 금액",
        help_text="리베이트가 적용될 요금제 금액 (K 단위)"
    )
    
    contract_period = models.IntegerField(
        choices=CONTRACT_PERIOD_CHOICES,
        verbose_name="계약기간",
        help_text="리베이트가 적용될 계약기간 (개월)"
    )
    
    rebate_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="리베이트 금액",
        help_text="해당 조건의 리베이트 금액"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    class Meta:
        verbose_name = "리베이트 매트릭스"
        verbose_name_plural = "리베이트 매트릭스"
        ordering = ['policy', 'carrier', 'plan_range', 'contract_period']
        unique_together = ['policy', 'carrier', 'plan_range', 'contract_period']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['carrier', 'plan_range', 'contract_period']),
            models.Index(fields=['policy', 'carrier']),
        ]
    
    def __str__(self):
        return f"{self.policy.title} - {self.get_carrier_display()} - {self.get_plan_range_display()} - {self.get_contract_period_display()}: {self.rebate_amount:,}원"
    
    def clean(self):
        """모델 데이터 검증"""
        if self.rebate_amount < 0:
            raise ValidationError("리베이트 금액은 0 이상이어야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"리베이트 매트릭스가 생성되었습니다: {self}")
            else:
                logger.info(f"리베이트 매트릭스가 수정되었습니다: {self}")
        
        except Exception as e:
            logger.error(f"리베이트 매트릭스 저장 중 오류 발생: {str(e)}")
            raise
    
    @classmethod
    def get_commission_amount(cls, policy, carrier, plan_amount, contract_period):
        """
        주어진 조건에 맞는 수수료 금액 조회 (기존 get_rebate_amount에서 이름 변경)
        
        Args:
            policy: Policy 객체
            carrier: 통신사 코드
            plan_amount: 요금제 금액
            contract_period: 가입기간 (개월)
            
        Returns:
            수수료 금액 또는 None
        """
        # 요금제 금액에 맞는 범위 찾기
        plan_range = None
        for range_value, _ in cls.PLAN_RANGE_CHOICES:
            if plan_amount <= range_value:
                plan_range = range_value
                break
        
        if not plan_range:
            # 가장 높은 범위 사용
            plan_range = cls.PLAN_RANGE_CHOICES[-1][0]
        
        try:
            # 먼저 특정 통신사에 대한 매트릭스를 찾기
            matrix = cls.objects.get(
                policy=policy,
                carrier=carrier,
                plan_range=plan_range,
                contract_period=contract_period
            )
            return matrix.rebate_amount
        except cls.DoesNotExist:
            try:
                # 특정 통신사가 없으면 전체 통신사 매트릭스를 찾기
                matrix = cls.objects.get(
                    policy=policy,
                    carrier='all',
                    plan_range=plan_range,
                    contract_period=contract_period
                )
                return matrix.rebate_amount
            except cls.DoesNotExist:
                return None
    
    @classmethod
    def create_default_matrix(cls, policy):
        """
        정책에 대한 기본 수수료 매트릭스 생성 (기존 리베이트 매트릭스에서 이름 변경)
        
        Args:
            policy: Policy 객체
        """
        default_rebates = {
            # (통신사, 요금제 범위, 가입기간): 리베이트 금액
            ('all', 30000, 12): 50000,
            ('all', 30000, 24): 80000,
            ('all', 50000, 12): 70000,
            ('all', 50000, 24): 120000,
            ('all', 70000, 12): 100000,
            ('all', 70000, 24): 160000,
            ('all', 90000, 12): 150000,
            ('all', 90000, 24): 250000,
        }
        
        for (carrier, plan_range, period), amount in default_rebates.items():
            cls.objects.get_or_create(
                policy=policy,
                carrier=carrier,
                plan_range=plan_range,
                contract_period=period,
                defaults={'rebate_amount': amount}
            )
        
        logger.info(f"정책 '{policy.title}'에 기본 리베이트 매트릭스가 생성되었습니다.")


class CarrierPlan(models.Model):
    """
    통신사별 요금제 관리 모델
    본사에서 통신사별 요금제를 관리
    """
    
    # 통신사 선택지
    CARRIER_CHOICES = [
        ('skt', 'SKT'),
        ('kt', 'KT'),
        ('lg', 'LG U+'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="요금제의 고유 식별자"
    )
    
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        verbose_name="통신사",
        help_text="요금제를 제공하는 통신사"
    )
    
    plan_name = models.CharField(
        max_length=200,
        verbose_name="요금제명",
        help_text="요금제의 이름"
    )
    
    plan_price = models.IntegerField(
        verbose_name="요금제 금액",
        help_text="월 요금제 금액 (원)"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="요금제 설명",
        help_text="요금제에 대한 상세 설명"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화 여부",
        help_text="요금제 사용 가능 여부"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="생성자",
        help_text="요금제를 생성한 관리자"
    )
    
    class Meta:
        verbose_name = "통신사 요금제"
        verbose_name_plural = "통신사 요금제 관리"
        ordering = ['carrier', 'plan_price', 'plan_name']
        unique_together = ['carrier', 'plan_name']
        indexes = [
            models.Index(fields=['carrier', 'is_active']),
            models.Index(fields=['plan_price']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_carrier_display()} - {self.plan_name} ({self.plan_price:,}원)"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.plan_name or not self.plan_name.strip():
            raise ValidationError("요금제명은 필수 입력 사항입니다.")
        
        if self.plan_price <= 0:
            raise ValidationError("요금제 금액은 0보다 커야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 요금제가 생성되었습니다: {self}")
            else:
                logger.info(f"요금제가 수정되었습니다: {self}")
        
        except Exception as e:
            logger.error(f"요금제 저장 중 오류 발생: {str(e)} - {self.plan_name}")
            raise


class DeviceModel(models.Model):
    """
    기기 모델 관리 모델
    본사에서 판매 가능한 기기 모델을 관리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="기기 모델의 고유 식별자"
    )
    
    model_name = models.CharField(
        max_length=200,
        verbose_name="모델명",
        help_text="기기의 모델명"
    )
    
    manufacturer = models.CharField(
        max_length=100,
        verbose_name="제조사",
        help_text="기기 제조사"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="모델 설명",
        help_text="기기 모델에 대한 상세 설명"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화 여부",
        help_text="모델 판매 가능 여부"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일시"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="생성자",
        help_text="모델을 생성한 관리자"
    )
    
    class Meta:
        verbose_name = "기기 모델"
        verbose_name_plural = "기기 모델 관리"
        ordering = ['manufacturer', 'model_name']
        unique_together = ['manufacturer', 'model_name']
        indexes = [
            models.Index(fields=['manufacturer', 'is_active']),
            models.Index(fields=['model_name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.manufacturer} {self.model_name}"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.model_name or not self.model_name.strip():
            raise ValidationError("모델명은 필수 입력 사항입니다.")
        
        if not self.manufacturer or not self.manufacturer.strip():
            raise ValidationError("제조사는 필수 입력 사항입니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 기기 모델이 생성되었습니다: {self}")
            else:
                logger.info(f"기기 모델이 수정되었습니다: {self}")
        
        except Exception as e:
            logger.error(f"기기 모델 저장 중 오류 발생: {str(e)} - {self.model_name}")
            raise


class DeviceColor(models.Model):
    """
    기기 색상 관리 모델
    기기 모델별 사용 가능한 색상을 관리
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="기기 색상의 고유 식별자"
    )
    
    device_model = models.ForeignKey(
        DeviceModel,
        on_delete=models.CASCADE,
        related_name='colors',
        verbose_name="기기 모델",
        help_text="색상이 적용될 기기 모델"
    )
    
    color_name = models.CharField(
        max_length=100,
        verbose_name="색상명",
        help_text="색상의 이름"
    )
    
    color_code = models.CharField(
        max_length=7,
        blank=True,
        verbose_name="색상 코드",
        help_text="색상의 HEX 코드 (예: #FF0000)"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화 여부",
        help_text="색상 선택 가능 여부"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일시"
    )
    
    class Meta:
        verbose_name = "기기 색상"
        verbose_name_plural = "기기 색상 관리"
        ordering = ['device_model', 'color_name']
        unique_together = ['device_model', 'color_name']
        indexes = [
            models.Index(fields=['device_model', 'is_active']),
            models.Index(fields=['color_name']),
        ]
    
    def __str__(self):
        return f"{self.device_model} - {self.color_name}"
    
    def clean(self):
        """모델 데이터 검증"""
        if not self.color_name or not self.color_name.strip():
            raise ValidationError("색상명은 필수 입력 사항입니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 처리"""
        is_new = self.pk is None
        
        try:
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"새로운 기기 색상이 생성되었습니다: {self}")
            else:
                logger.info(f"기기 색상이 수정되었습니다: {self}")
        
        except Exception as e:
            logger.error(f"기기 색상 저장 중 오류 발생: {str(e)} - {self.color_name}")
            raise


class OrderFormTemplate(models.Model):
    """
    주문서 양식 템플릿 모델
    정책별 주문서 양식을 관리
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.OneToOneField(Policy, on_delete=models.CASCADE, related_name='order_form', verbose_name='정책')
    title = models.CharField(max_length=200, verbose_name='양식 제목')
    description = models.TextField(blank=True, verbose_name='양식 설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='생성자')
    
    class Meta:
        verbose_name = '주문서 양식'
        verbose_name_plural = '주문서 양식 관리'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.policy.title} - 주문서 양식"


class OrderFormField(models.Model):
    """
    주문서 양식 필드 모델
    주문서 양식의 개별 필드를 정의
    """
    FIELD_TYPE_CHOICES = [
        # 기본 필드 타입
        ('text', '텍스트'),
        ('number', '숫자'),
        ('select', '선택'),
        ('radio', '라디오'),
        ('checkbox', '체크박스'),
        ('textarea', '텍스트 영역'),
        ('date', '날짜'),
        ('datetime', '날짜/시간'),
        ('phone', '전화번호'),
        ('email', '이메일'),
        ('url', 'URL'),
        
        # 특수 필드 타입
        ('barcode_scan', '바코드 스캔'),
        ('large_textarea', '대형 텍스트 영역'),
        ('dropdown_from_policy', '정책 드롭다운'),
        ('file_upload', '파일 업로드'),
        ('customer_type', '고객유형'),
        ('carrier_plan', '통신사 요금제'),  # 통신사별 요금제 선택
        ('device_model', '기기 모델'),  # 기기 모델 선택
        ('device_color', '기기 색상'),  # 기기 색상 선택
        ('sim_type', '유심 타입'),  # 유심 타입 선택
        ('contract_period', '계약 기간'),  # 계약 기간 선택
        ('payment_method', '결제 방법'),  # 결제 방법 선택
        ('rebate_table', '리베이트 테이블'),  # 요금제별 리베이트 입력용
        ('course', '코스'),  # 심플/스탠다드/프리미엄
        ('common_support', '공통지원금'),  # 숫자 입력
        ('additional_support', '추가지원금'),  # 숫자 입력
        ('free_amount', '프리금액'),  # 숫자 입력
        ('installment_principal', '할부원금'),  # 숫자 입력
        ('additional_fee', '부가'),  # 텍스트 입력
        ('insurance', '보험'),  # 파손/도난/종합/없음
        ('welfare', '복지'),  # 텍스트 입력
        ('legal_info', '법대정보'),  # 텍스트 입력
        ('foreigner_info', '외국인정보'),  # 국적/발급일자
        ('installment_months', '할부개월수'),  # 12/24/36개월
        ('join_type', '가입유형'),  # 기변/신규/번호이동
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(OrderFormTemplate, on_delete=models.CASCADE, related_name='fields', verbose_name='양식 템플릿')
    field_name = models.CharField(max_length=100, verbose_name='필드 이름')
    field_label = models.CharField(max_length=200, verbose_name='필드 라벨')
    field_type = models.CharField(max_length=30, choices=FIELD_TYPE_CHOICES, verbose_name='필드 타입')
    is_required = models.BooleanField(default=False, verbose_name='필수 여부')
    field_options = models.JSONField(blank=True, null=True, verbose_name='필드 옵션')  # 선택 옵션들
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='플레이스홀더')
    help_text = models.CharField(max_length=500, blank=True, verbose_name='도움말')
    order = models.IntegerField(default=0, verbose_name='순서')
    
    # 추가 필드 속성
    is_readonly = models.BooleanField(default=False, verbose_name='읽기 전용')
    is_masked = models.BooleanField(default=False, verbose_name='마스킹 여부')
    auto_fill = models.CharField(max_length=50, blank=True, verbose_name='자동 채우기 타입')
    auto_generate = models.BooleanField(default=False, verbose_name='자동 생성')
    allow_manual = models.BooleanField(default=True, verbose_name='수기 입력 허용')
    data_source = models.CharField(max_length=100, blank=True, verbose_name='데이터 소스')
    rows = models.IntegerField(default=3, verbose_name='textarea 행 수')
    multiple = models.BooleanField(default=False, verbose_name='다중 선택')
    max_files = models.IntegerField(default=4, verbose_name='최대 파일 수')
    accept = models.CharField(max_length=200, blank=True, default='image/*,.pdf,.doc,.docx', verbose_name='허용 파일 타입')
    
    class Meta:
        verbose_name = '주문서 필드'
        verbose_name_plural = '주문서 필드 관리'
        ordering = ['order', 'field_name']
    
    def __str__(self):
        return f"{self.template.title} - {self.field_label}"
    
    def get_default_options(self):
        """필드 타입에 따른 기본 옵션 반환"""
        default_options = {
            'sim_type': {
                'choices': [
                    {'value': 'prepaid', 'label': '선불 (본사 7,700원 지급)'},
                    {'value': 'postpaid', 'label': '후불 (본사 7,700원 차감)'},
                    {'value': 'esim', 'label': 'eSIM'},
                    {'value': 'reuse', 'label': '재사용'}
                ]
            },
            'contract_period': {
                'choices': [
                    {'value': '12', 'label': '12개월'},
                    {'value': '24', 'label': '24개월'},
                    {'value': '36', 'label': '36개월'}
                ]
            },
            'payment_method': {
                'choices': [
                    {'value': 'cash', 'label': '현금'},
                    {'value': 'installment', 'label': '할부'}
                ]
            },
            'carrier_plan': {
                'dynamic': True,  # 동적으로 로드되는 옵션
                'source': 'CarrierPlan'
            },
            'device_model': {
                'dynamic': True,
                'source': 'DeviceModel'
            },
            'device_color': {
                'dynamic': True,
                'source': 'DeviceColor',
                'depends_on': 'device_model'  # 기기 모델에 따라 색상 옵션이 달라짐
            },
            'installment_months': {
                'choices': [
                    {'value': '12', 'label': '12개월'},
                    {'value': '24', 'label': '24개월'},
                    {'value': '36', 'label': '36개월'}
                ]
            },
            'insurance': {
                'choices': [
                    {'value': 'damage', 'label': '파손'},
                    {'value': 'theft', 'label': '도난'},
                    {'value': 'comprehensive', 'label': '종합'},
                    {'value': 'none', 'label': '없음'}
                ]
            },
            'course': {
                'choices': [
                    {'value': 'simple', 'label': '심플'},
                    {'value': 'standard', 'label': '스탠다드'},
                    {'value': 'premium', 'label': '프리미엄'}
                ]
            },
            'join_type': {
                'choices': [
                    {'value': 'device_change', 'label': '기변'},
                    {'value': 'new_subscription', 'label': '신규'},
                    {'value': 'number_transfer', 'label': '번호이동'}
                ]
            },
            'payment_method': {
                'choices': [
                    {'value': 'cash', 'label': '현금'},
                    {'value': 'installment', 'label': '할부'}
                ]
            },
            'sim_type': {
                'choices': [
                    {'value': 'prepaid', 'label': '선불 (+7,700원)'},
                    {'value': 'postpaid', 'label': '후불 (-7,700원)'},
                    {'value': 'esim', 'label': '이심'},
                    {'value': 'reuse', 'label': '재사용'}
                ]
            },
            'contract_period': {
                'choices': [
                    {'value': '12', 'label': '12개월'},
                    {'value': '24', 'label': '24개월'},
                    {'value': '36', 'label': '36개월'}
                ]
            }
        }
        
        return default_options.get(self.field_type, {})
    
    def save(self, *args, **kwargs):
        """저장 시 기본 옵션 설정"""
        if not self.field_options:
            self.field_options = self.get_default_options()
        
        super().save(*args, **kwargs)
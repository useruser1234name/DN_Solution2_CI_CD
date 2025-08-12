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
    
    # 가입기간 선택지
    CONTRACT_PERIOD_CHOICES = [
        ('12', '12개월'),
        ('24', '24개월'),
        ('36', '36개월'),
        ('all', '전체'),
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
    
    # 통신사 및 가입기간 필터링
    carrier = models.CharField(
        max_length=10,
        choices=CARRIER_CHOICES,
        default='all',
        verbose_name="통신사",
        help_text="적용할 통신사를 선택하세요"
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
    
    # HTML 상세페이지 자동 생성 내용
    html_content = models.TextField(
        blank=True,
        null=True,
        verbose_name="HTML 내용",
        help_text="자동 생성된 HTML 상세페이지 내용"
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
    본사가 협력사에 정책을 노출하는 것을 관리
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='exposures', verbose_name='정책')
    agency = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='exposed_policies', verbose_name='협력사')
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
        # 협력사 타입 검증
        if self.agency and self.agency.type != 'agency':
            raise ValidationError("협력사에만 정책을 노출할 수 있습니다.")
        
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
        ('text', '텍스트'),
        ('number', '숫자'),
        ('select', '선택'),
        ('radio', '라디오'),
        ('checkbox', '체크박스'),
        ('textarea', '텍스트 영역'),
        ('date', '날짜'),
        ('rebate_table', '리베이트 테이블'),  # 요금제별 리베이트 입력용
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(OrderFormTemplate, on_delete=models.CASCADE, related_name='fields', verbose_name='양식 템플릿')
    field_name = models.CharField(max_length=100, verbose_name='필드 이름')
    field_label = models.CharField(max_length=200, verbose_name='필드 라벨')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, verbose_name='필드 타입')
    is_required = models.BooleanField(default=False, verbose_name='필수 여부')
    field_options = models.JSONField(blank=True, null=True, verbose_name='필드 옵션')  # 선택 옵션들
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='플레이스홀더')
    help_text = models.CharField(max_length=500, blank=True, verbose_name='도움말')
    order = models.IntegerField(default=0, verbose_name='순서')
    
    class Meta:
        verbose_name = '주문서 필드'
        verbose_name_plural = '주문서 필드 관리'
        ordering = ['order', 'field_name']
    
    def __str__(self):
        return f"{self.template.title} - {self.field_label}"
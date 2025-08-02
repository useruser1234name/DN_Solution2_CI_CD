<<<<<<< HEAD
"""
정책 관리 시스템 모델

이 모듈은 상품 정책 관리를 위한 모델들을 정의합니다.
리베이트 설정, HTML 자동 생성, 접수 방식 등을 포함합니다.
"""

import uuid
import logging
from django.db import models
from django.core.exceptions import ValidationError
from companies.models import Company

logger = logging.getLogger(__name__)
=======
# policies/models.py
import uuid
import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.html import format_html
from companies.models import Company

logger = logging.getLogger('policies')
>>>>>>> 25_08_03/main


class Policy(models.Model):
    """
<<<<<<< HEAD
    정책 모델
    
    상품 정책을 관리하는 핵심 모델입니다.
    리베이트 설정, HTML 자동 생성, 접수 방식 등을 포함합니다.
    """
    
    RECEPTION_TYPES = [
        ('general', '일반'),
        ('link', '링크'),
        ('registration', '등록'),
        ('egg', '에그'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='등록 업체'
    )
    title = models.CharField(max_length=200, verbose_name='정책 제목')
    description = models.TextField(verbose_name='정책 설명')
    rebate_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name='기본 리베이트율 (%)'
    )
    reception_type = models.CharField(
        max_length=20, 
        choices=RECEPTION_TYPES,
        verbose_name='접수 방식'
    )
    html_content = models.TextField(blank=True, verbose_name='HTML 내용')
    is_shared = models.BooleanField(default=False, verbose_name='공유 여부')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '정책'
        verbose_name_plural = '정책'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['reception_type']),
            models.Index(fields=['is_shared']),
            models.Index(fields=['is_active']),
=======
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
>>>>>>> 25_08_03/main
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
<<<<<<< HEAD
        return f"{self.title} ({self.company.name})"
    
    def clean(self):
        """정책 생성/수정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 리베이트율 범위 검증
        if self.rebate_rate < 0 or self.rebate_rate > 100:
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 비활성 업체에 정책 등록 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 정책을 등록할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅 및 HTML 자동 생성"""
        self.full_clean()
        is_new = self.pk is None
        
        # HTML 내용 자동 생성
        if not self.html_content:
            self.html_content = self.generate_html_content()
        
        if is_new:
            logger.info(f"[Policy.save] 새 정책 생성 - 제목: {self.title}, 업체: {self.company.name}")
        else:
            logger.info(f"[Policy.save] 정책 수정 - 제목: {self.title}, 업체: {self.company.name}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """삭제 시 로깅"""
        logger.warning(f"[Policy.delete] 정책 삭제 - 제목: {self.title}, 업체: {self.company.name}")
        super().delete(*args, **kwargs)
    
    def generate_html_content(self):
        """
        HTML 내용 자동 생성
        
        Returns:
            str: 생성된 HTML 내용
        """
        html_template = f"""
        <div class="policy-detail">
            <h2>{self.title}</h2>
            <div class="policy-info">
                <p><strong>업체:</strong> {self.company.name}</p>
                <p><strong>리베이트율:</strong> {self.rebate_rate}%</p>
                <p><strong>접수방식:</strong> {self.get_reception_type_display()}</p>
            </div>
            <div class="policy-description">
                <h3>정책 설명</h3>
                <p>{self.description}</p>
            </div>
            <div class="policy-actions">
                <button class="btn btn-primary" onclick="applyPolicy('{self.id}')">정책 신청</button>
            </div>
        </div>
        """
        return html_template
    
    def toggle_share(self):
        """공유 상태 토글"""
        self.is_shared = not self.is_shared
        self.save()
        logger.info(f"[Policy.toggle_share] 정책 공유 상태 변경 - 제목: {self.title}, 공유: {self.is_shared}")
    
    def toggle_active(self):
        """활성화 상태 토글"""
        self.is_active = not self.is_active
        self.save()
        logger.info(f"[Policy.toggle_active] 정책 활성화 상태 변경 - 제목: {self.title}, 활성화: {self.is_active}")
=======
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
        
        try:
            self.clean()
            
            # HTML 자동 생성
            if not self.html_content:
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
                'rebate_agency': self.rebate_agency,
                'rebate_retail': self.rebate_retail,
                'created_at': self.created_at,
                'created_by': self.created_by,
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
                <p><strong>대리점 리베이트:</strong> {self.rebate_agency:,}원</p>
                <p><strong>판매점 리베이트:</strong> {self.rebate_retail:,}원</p>
            </div>
            <div class="policy-description">
                <h2>정책 설명</h2>
                <p>{self.description}</p>
            </div>
            <div class="policy-meta">
                <p>생성일: {self.created_at.strftime('%Y년 %m월 %d일')}</p>
                {f'<p>생성자: {self.created_by.username}</p>' if self.created_by else ''}
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
        """배정된 업체 목록 반환"""
        try:
            return [assignment.company for assignment in self.assignments.select_related('company')]
        except Exception as e:
            logger.warning(f"정책 배정 업체 목록 조회 중 오류: {str(e)} - 정책: {self.title}")
            return []
    
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
>>>>>>> 25_08_03/main


class PolicyAssignment(models.Model):
    """
<<<<<<< HEAD
    정책 배정 모델
    
    특정 정책을 특정 업체에 배정하고 커스텀 리베이트율을 설정합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        verbose_name='정책'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='배정 업체'
    )
    custom_rebate_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='커스텀 리베이트율 (%)'
    )
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='배정일시')
    
    class Meta:
        verbose_name = '정책 배정'
        verbose_name_plural = '정책 배정'
        unique_together = ['policy', 'company']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['policy']),
            models.Index(fields=['company']),
            models.Index(fields=['is_active']),
=======
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
>>>>>>> 25_08_03/main
        ]
    
    def __str__(self):
        return f"{self.policy.title} → {self.company.name}"
    
    def clean(self):
<<<<<<< HEAD
        """정책 배정 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 커스텀 리베이트율 범위 검증
        if self.custom_rebate_rate and (self.custom_rebate_rate < 0 or self.custom_rebate_rate > 100):
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 비활성 업체에 정책 배정 금지
        if not self.company.status:
            raise ValidationError("비활성 업체에는 정책을 배정할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[PolicyAssignment.save] 새 정책 배정 - 정책: {self.policy.title}, 업체: {self.company.name}")
        else:
            logger.info(f"[PolicyAssignment.save] 정책 배정 수정 - 정책: {self.policy.title}, 업체: {self.company.name}")
        
        super().save(*args, **kwargs)
    
    def get_effective_rebate(self):
        """
        실제 적용되는 리베이트율 반환
        
        Returns:
            Decimal: 커스텀 리베이트율이 있으면 커스텀값, 없으면 기본값
        """
        return self.custom_rebate_rate if self.custom_rebate_rate else self.policy.rebate_rate


class PolicyShare(models.Model):
    """
    정책 공유 모델
    
    검증된 업체 간 정책 공유를 관리합니다.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='shared_from',
        verbose_name='원본 정책'
    )
    target_company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        verbose_name='대상 업체'
    )
    shared_rebate_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='공유 리베이트율 (%)'
    )
    is_approved = models.BooleanField(default=False, verbose_name='승인 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='공유 요청일시')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='승인일시')
    
    class Meta:
        verbose_name = '정책 공유'
        verbose_name_plural = '정책 공유'
        unique_together = ['source_policy', 'target_company']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_policy']),
            models.Index(fields=['target_company']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.source_policy.title} → {self.target_company.name}"
    
    def clean(self):
        """정책 공유 시 비즈니스 규칙 검증"""
        super().clean()
        
        # 리베이트율 범위 검증
        if self.shared_rebate_rate < 0 or self.shared_rebate_rate > 100:
            raise ValidationError("리베이트율은 0%에서 100% 사이여야 합니다.")
        
        # 같은 업체 간 공유 금지
        if self.source_policy.company == self.target_company:
            raise ValidationError("같은 업체 간에는 정책을 공유할 수 없습니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 로깅"""
        self.full_clean()
        is_new = self.pk is None
        
        if is_new:
            logger.info(f"[PolicyShare.save] 새 정책 공유 요청 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
        else:
            logger.info(f"[PolicyShare.save] 정책 공유 수정 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
        
        super().save(*args, **kwargs)
    
    def approve(self):
        """정책 공유 승인"""
        from django.utils import timezone
        
        self.is_approved = True
        self.approved_at = timezone.now()
        self.save()
        
        logger.info(f"[PolicyShare.approve] 정책 공유 승인 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
    
    def reject(self):
        """정책 공유 거절"""
        self.is_approved = False
        self.save()
        
        logger.info(f"[PolicyShare.reject] 정책 공유 거절 - 정책: {self.source_policy.title}, 대상: {self.target_company.name}")
=======
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
>>>>>>> 25_08_03/main

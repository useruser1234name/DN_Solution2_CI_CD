"""
Company 비즈니스 로직 서비스 계층

비즈니스 로직을 View에서 분리하여 재사용성과 테스트 용이성을 향상시킵니다.
"""

import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Company, CompanyUser, CompanyMessage
from .utils import get_accessible_company_ids, get_visible_companies, get_visible_users

logger = logging.getLogger('companies')


class CompanyService:
    """업체 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def create_company_with_admin(
        company_data: Dict[str, Any], 
        admin_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        업체와 관리자를 함께 생성하는 서비스
        
        Args:
            company_data: 업체 정보
            admin_data: 관리자 정보
            
        Returns:
            Dict: 생성 결과
            
        Raises:
            ValidationError: 데이터 검증 실패
        """
        with transaction.atomic():
            # 1. 사용자명 중복 검사
            username = admin_data.get('username')
            if User.objects.filter(username=username).exists():
                raise ValidationError("이미 사용 중인 사용자명입니다.")
            
            # 2. 부모 업체 검증
            parent_company = None
            company_type = company_data.get('type')
            parent_code = company_data.get('parent_code')
            
            if company_type != 'headquarters' and parent_code:
                try:
                    parent_company = Company.objects.get(code=parent_code, status=True)
                    CompanyService._validate_company_hierarchy(parent_company, company_type)
                except Company.DoesNotExist:
                    raise ValidationError("유효하지 않은 상위 업체 코드입니다.")
            
            # 3. Django User 생성
            django_user = User.objects.create_user(
                username=username,
                password=admin_data.get('password'),
                email=admin_data.get('email', '')
            )
            
            # 4. 업체 생성
            company = Company.objects.create(
                name=company_data.get('name'),
                type=company_type,
                parent_company=parent_company,
                status=True,
                visible=True
            )
            
            # 5. CompanyUser 생성
            company_user = CompanyUser.objects.create(
                company=company,
                django_user=django_user,
                username=username,
                role=admin_data.get('role', 'admin'),
                status='pending',
                is_approved=False
            )
            
            logger.info(f"[CompanyService] 업체와 관리자 생성 완료 - 업체: {company.name}, 관리자: {username}")
            
            return {
                'success': True,
                'company': company,
                'company_user': company_user,
                'message': '회원가입이 완료되었습니다. 상위 업체 관리자 승인 후 로그인할 수 있습니다.'
            }
    
    @staticmethod
    def _validate_company_hierarchy(parent_company: Company, child_type: str) -> None:
        """업체 계층 구조 검증"""
        hierarchy_rules = {
            'agency': ['headquarters'],
            'dealer': ['headquarters'],
            'retail': ['agency', 'dealer']
        }
        
        valid_parent_types = hierarchy_rules.get(child_type, [])
        if parent_company.type not in valid_parent_types:
            raise ValidationError(f"{child_type}은(는) {', '.join(valid_parent_types)} 하위에만 생성할 수 있습니다.")
    
    @staticmethod
    def get_accessible_companies(user: User) -> List[Company]:
        """사용자가 접근 가능한 업체 목록 조회"""
        return get_visible_companies(user)
    
    @staticmethod
    def get_company_stats(user: User) -> Dict[str, Any]:
        """업체 관련 통계 정보 (캐시 활용)"""
        from .cache_utils import StatsCacheManager
        return StatsCacheManager.get_company_stats(user)


class CompanyUserService:
    """업체 사용자 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def create_staff_user(
        username: str, 
        password: str, 
        company_code: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        직원 사용자 생성 서비스
        
        Args:
            username: 사용자명
            password: 비밀번호
            company_code: 업체 코드
            additional_data: 추가 정보
            
        Returns:
            Dict: 생성 결과
        """
        with transaction.atomic():
            # 1. 사용자명 중복 검사
            if User.objects.filter(username=username).exists():
                raise ValidationError("이미 사용 중인 사용자명입니다.")
            
            # 2. 업체 검증
            try:
                company = Company.objects.get(code=company_code, status=True)
                if company.type != 'headquarters':
                    raise ValidationError("본사만 직원 가입이 가능합니다.")
            except Company.DoesNotExist:
                raise ValidationError("유효하지 않은 업체 코드입니다.")
            
            # 3. Django User 생성
            django_user = User.objects.create_user(
                username=username,
                password=password,
                email=additional_data.get('email', '') if additional_data else ''
            )
            
            # 4. CompanyUser 생성
            company_user = CompanyUser.objects.create(
                company=company,
                django_user=django_user,
                username=username,
                role='staff',
                status='pending',
                is_approved=False
            )
            
            logger.info(f"[CompanyUserService] 직원 사용자 생성 완료 - 사용자: {username}, 업체: {company.name}")
            
            return {
                'success': True,
                'company_user': company_user,
                'message': '회원가입이 완료되었습니다. 해당 업체 관리자 승인 후 로그인할 수 있습니다.'
            }
    
    @staticmethod
    def approve_user(user_id: str, approver: User, action: str) -> Dict[str, Any]:
        """
        사용자 승인/거절 처리
        
        Args:
            user_id: 대상 사용자 ID
            approver: 승인자
            action: 'approve' 또는 'reject'
            
        Returns:
            Dict: 처리 결과
        """
        try:
            target_user = CompanyUser.objects.get(id=user_id)
        except CompanyUser.DoesNotExist:
            raise ValidationError('사용자를 찾을 수 없습니다.')
        
        # 승인 권한 검증
        if not CompanyUserService._can_approve_user(approver, target_user):
            raise ValidationError('해당 사용자를 승인할 권한이 없습니다.')
        
        # 상태 업데이트
        if action == 'approve':
            target_user.status = 'approved'
            target_user.is_approved = True
            message = '사용자가 승인되었습니다.'
        elif action == 'reject':
            target_user.status = 'rejected'
            target_user.is_approved = False
            message = '사용자가 거절되었습니다.'
        else:
            raise ValidationError('잘못된 액션입니다.')
        
        target_user.save()
        
        logger.info(f"[CompanyUserService] 사용자 {action} - 대상: {target_user.username}, 승인자: {approver.username}")
        
        return {
            'success': True,
            'message': message,
            'target_user': target_user
        }
    
    @staticmethod
    def _can_approve_user(approver: User, target_user: CompanyUser) -> bool:
        """승인 권한 검증"""
        if approver.is_superuser:
            return True
        
        try:
            approver_company_user = CompanyUser.objects.get(django_user=approver)
        except CompanyUser.DoesNotExist:
            return False
        
        # 승인자는 관리자여야 함
        if approver_company_user.role != 'admin':
            return False
        
        approver_company = approver_company_user.company
        target_company = target_user.company
        
        # 자기 회사 또는 하위 회사인지 확인
        if approver_company == target_company:
            return True
        
        # 하위 회사인지 확인
        parent = target_company.parent_company
        while parent:
            if parent == approver_company:
                return True
            parent = parent.parent_company
        
        return False
    
    @staticmethod
    def get_pending_users(user: User) -> List[CompanyUser]:
        """승인 대기 중인 사용자 목록"""
        visible_users = get_visible_users(user)
        return visible_users.filter(status='pending')
    
    @staticmethod
    def get_user_activities(user: User, hours: int = 24) -> List[Dict[str, Any]]:
        """사용자 활동 내역"""
        visible_users = get_visible_users(user)
        
        recent_logins = visible_users.filter(
            last_login__gte=timezone.now() - timedelta(hours=hours)
        ).order_by('-last_login')[:5]
        
        activities = []
        for u in recent_logins:
            if u.last_login:
                activities.append({
                    'type': 'user',
                    'message': f'{u.username}님이 로그인했습니다.',
                    'time': u.last_login.strftime('%Y-%m-%d %H:%M'),
                    'user_id': str(u.id)
                })
        
        return activities


class CompanyMessageService:
    """업체 메시지 관련 비즈니스 로직 서비스"""
    
    @staticmethod
    def send_message(
        sender: User,
        message: str,
        message_type: str,
        is_bulk: bool = False,
        target_company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        메시지 발송 서비스
        
        Args:
            sender: 발송자
            message: 메시지 내용
            message_type: 메시지 유형
            is_bulk: 일괄 발송 여부
            target_company_id: 대상 업체 ID (개별 발송 시)
            
        Returns:
            Dict: 발송 결과
        """
        target_company = None
        
        if not is_bulk and target_company_id:
            try:
                target_company = Company.objects.get(id=target_company_id)
            except Company.DoesNotExist:
                raise ValidationError("대상 업체를 찾을 수 없습니다.")
        
        company_message = CompanyMessage.objects.create(
            message=message,
            message_type=message_type,
            is_bulk=is_bulk,
            sent_by=sender,
            company=target_company
        )
        
        logger.info(f"[CompanyMessageService] 메시지 발송 - 발송자: {sender.username}, 유형: {message_type}")
        
        return {
            'success': True,
            'message_id': str(company_message.id),
            'message': '메시지가 성공적으로 발송되었습니다.'
        }
    
    @staticmethod
    def get_messages_for_company(company: Company, limit: int = 10) -> List[CompanyMessage]:
        """특정 업체의 메시지 목록"""
        return CompanyMessage.objects.filter(
            models.Q(company=company) | models.Q(is_bulk=True)
        ).order_by('-sent_at')[:limit]

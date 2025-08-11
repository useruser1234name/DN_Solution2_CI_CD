# -*- coding: utf-8 -*-
"""
데이터 검증 유틸리티
"""
import re
from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class DataValidator:
    """데이터 검증 클래스"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """
        전화번호 검증 및 정규화
        
        Args:
            phone: 전화번호 문자열
            
        Returns:
            정규화된 전화번호
            
        Raises:
            ValidationError: 유효하지 않은 전화번호
        """
        # 숫자만 추출
        digits = re.sub(r'\D', '', phone)
        
        # 한국 전화번호 패턴 확인
        if re.match(r'^01[0-9]{8,9}$', digits):
            # 휴대폰 번호
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        elif re.match(r'^0[2-6][0-9]{7,8}$', digits):
            # 지역 번호
            if len(digits) == 9:
                return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
            else:
                return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        else:
            raise ValidationError("유효하지 않은 전화번호 형식입니다.")
    
    @staticmethod
    def validate_business_number(number: str) -> str:
        """
        사업자등록번호 검증
        
        Args:
            number: 사업자등록번호
            
        Returns:
            정규화된 사업자등록번호
            
        Raises:
            ValidationError: 유효하지 않은 사업자등록번호
        """
        # 숫자만 추출
        digits = re.sub(r'\D', '', number)
        
        if len(digits) != 10:
            raise ValidationError("사업자등록번호는 10자리여야 합니다.")
        
        # 체크섬 검증
        check_nums = [1, 3, 7, 1, 3, 7, 1, 3, 5]
        check_sum = 0
        
        for i in range(9):
            check_sum += int(digits[i]) * check_nums[i]
        
        check_sum += (int(digits[8]) * 5) // 10
        
        if (10 - (check_sum % 10)) % 10 != int(digits[9]):
            raise ValidationError("유효하지 않은 사업자등록번호입니다.")
        
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        필수 필드 검증
        
        Args:
            data: 검증할 데이터 딕셔너리
            required_fields: 필수 필드 목록
            
        Raises:
            ValidationError: 필수 필드가 없거나 비어있음
        """
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                empty_fields.append(field)
        
        errors = []
        if missing_fields:
            errors.append(f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}")
        if empty_fields:
            errors.append(f"필수 필드가 비어있습니다: {', '.join(empty_fields)}")
        
        if errors:
            raise ValidationError('; '.join(errors))
    
    @staticmethod
    def validate_email_format(email: str) -> str:
        """
        이메일 형식 검증
        
        Args:
            email: 이메일 주소
            
        Returns:
            정규화된 이메일 주소
            
        Raises:
            ValidationError: 유효하지 않은 이메일 형식
        """
        email = email.strip().lower()
        validate_email(email)
        return email
    
    @staticmethod
    def validate_company_type(company_type: str) -> str:
        """
        회사 타입 검증
        
        Args:
            company_type: 회사 타입
            
        Returns:
            검증된 회사 타입
            
        Raises:
            ValidationError: 유효하지 않은 회사 타입
        """
        valid_types = ['headquarters', 'agency', 'retail']
        if company_type not in valid_types:
            raise ValidationError(
                f"유효하지 않은 회사 타입입니다. 다음 중 하나여야 합니다: {', '.join(valid_types)}"
            )
        return company_type
    
    @staticmethod
    def validate_hierarchy(parent_company, child_company_type: str) -> None:
        """
        회사 계층 구조 검증
        
        Args:
            parent_company: 상위 회사 객체
            child_company_type: 하위 회사 타입
            
        Raises:
            ValidationError: 유효하지 않은 계층 구조
        """
        if child_company_type == 'headquarters':
            if parent_company is not None:
                raise ValidationError("본사는 상위 회사를 가질 수 없습니다.")
        
        elif child_company_type == 'agency':
            if parent_company is None:
                raise ValidationError("대리점은 반드시 본사를 상위 회사로 가져야 합니다.")
            if parent_company.type != 'headquarters':
                raise ValidationError("대리점의 상위 회사는 본사여야 합니다.")
        
        elif child_company_type == 'retail':
            if parent_company is None:
                raise ValidationError("소매점은 반드시 대리점을 상위 회사로 가져야 합니다.")
            if parent_company.type != 'agency':
                raise ValidationError("소매점의 상위 회사는 대리점이어야 합니다.")
    
    @staticmethod
    def validate_amount(amount: Any, min_value: float = 0, max_value: Optional[float] = None) -> float:
        """
        금액 검증
        
        Args:
            amount: 금액
            min_value: 최소값
            max_value: 최대값 (선택)
            
        Returns:
            검증된 금액
            
        Raises:
            ValidationError: 유효하지 않은 금액
        """
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValidationError("유효한 숫자 형식이 아닙니다.")
        
        if amount < min_value:
            raise ValidationError(f"금액은 {min_value:,.0f}원 이상이어야 합니다.")
        
        if max_value is not None and amount > max_value:
            raise ValidationError(f"금액은 {max_value:,.0f}원 이하여야 합니다.")
        
        return amount
    
    @staticmethod
    def validate_date_range(start_date, end_date) -> None:
        """
        날짜 범위 검증
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Raises:
            ValidationError: 유효하지 않은 날짜 범위
        """
        if start_date > end_date:
            raise ValidationError("시작 날짜는 종료 날짜보다 이전이어야 합니다.")
    
    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        HTML 콘텐츠 정화
        
        Args:
            html_content: HTML 문자열
            
        Returns:
            정화된 HTML
        """
        import bleach
        
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'pre', 'code'
        ]
        allowed_attributes = {
            'a': ['href', 'title', 'target'],
            'code': ['class']
        }
        
        return bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
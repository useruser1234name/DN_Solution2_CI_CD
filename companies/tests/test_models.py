"""
Company 모델 테스트
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from companies.models import Company, CompanyUser
from datetime import datetime


class CompanyModelTest(TestCase):
    """Company 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.headquarters = Company.objects.create(
            name="테스트 본사",
            type="headquarters"
        )
        
        self.agency = Company.objects.create(
            name="테스트 협력사",
            type="agency",
            parent_company=self.headquarters
        )
    
    def test_company_code_generation(self):
        """업체 코드 자동 생성 테스트"""
        self.assertIsNotNone(self.headquarters.code)
        self.assertTrue(self.headquarters.code.startswith('A-'))
        
        self.assertIsNotNone(self.agency.code)
        self.assertTrue(self.agency.code.startswith('B-'))
    
    def test_company_hierarchy_validation(self):
        """업체 계층 구조 검증 테스트"""
        # 본사는 상위 업체를 가질 수 없음
        with self.assertRaises(ValidationError):
            invalid_hq = Company(
                name="잘못된 본사",
                type="headquarters",
                parent_company=self.agency
            )
            invalid_hq.full_clean()
        
        # 협력사는 본사를 상위 업체로 가져야 함
        with self.assertRaises(ValidationError):
            invalid_agency = Company(
                name="잘못된 협력사",
                type="agency",
                parent_company=None
            )
            invalid_agency.full_clean()
        
        # 판매점은 협력사를 상위 업체로 가져야 함
        with self.assertRaises(ValidationError):
            invalid_retail = Company(
                name="잘못된 판매점",
                type="retail",
                parent_company=self.headquarters  # 본사를 상위로 지정
            )
            invalid_retail.full_clean()
    
    def test_company_properties(self):
        """Company 속성 테스트"""
        self.assertTrue(self.headquarters.is_headquarters)
        self.assertFalse(self.headquarters.is_agency)
        
        self.assertTrue(self.agency.is_agency)
        self.assertFalse(self.agency.is_headquarters)
    
    def test_child_companies(self):
        """하위 업체 조회 테스트"""
        retail = Company.objects.create(
            name="테스트 판매점",
            type="retail",
            parent_company=self.agency
        )
        
        # 본사의 하위 업체는 협력사
        hq_children = self.headquarters.child_companies
        self.assertEqual(hq_children.count(), 1)
        self.assertIn(self.agency, hq_children)
        
        # 협력사의 하위 업체는 판매점
        agency_children = self.agency.child_companies
        self.assertEqual(agency_children.count(), 1)
        self.assertIn(retail, agency_children)


class CompanyUserModelTest(TestCase):
    """CompanyUser 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.company = Company.objects.create(
            name="테스트 회사",
            type="headquarters"
        )
        
        self.django_user = User.objects.create_user(
            username="testuser",
            password="testpass123!"
        )
        
        self.company_user = CompanyUser.objects.create(
            company=self.company,
            django_user=self.django_user,
            username="testuser",
            role="admin"
        )
        
        self.superuser = User.objects.create_superuser(
            username="superuser",
            password="superpass123!"
        )
        
        self.super_company_user = CompanyUser.objects.create(
            company=self.company,
            django_user=self.superuser,
            username="superuser",
            role="admin"
        )
    
    def test_company_user_creation(self):
        """CompanyUser 생성 테스트"""
        self.assertEqual(self.company_user.username, "testuser")
        self.assertEqual(self.company_user.role, "admin")
        self.assertFalse(self.company_user.is_approved)
        self.assertEqual(self.company_user.status, "pending")
    
    def test_username_uniqueness(self):
        """사용자명 중복 검사 테스트"""
        with self.assertRaises(ValidationError):
            duplicate_user = CompanyUser(
                company=self.company,
                django_user=User.objects.create_user(
                    username="anotheruser",
                    password="pass123!"
                ),
                username="testuser",  # 중복된 사용자명
                role="staff"
            )
            duplicate_user.full_clean()
    
    def test_approval_permissions(self):
        """승인 권한 테스트"""
        # 슈퍼유저는 모든 사용자 승인 가능
        self.assertTrue(
            self.company_user.can_be_approved_by(self.super_company_user)
        )
        
        # 협력사 생성
        agency = Company.objects.create(
            name="테스트 협력사",
            type="agency",
            parent_company=self.company
        )
        
        agency_admin = CompanyUser.objects.create(
            company=agency,
            django_user=User.objects.create_user(
                username="agencyadmin",
                password="pass123!"
            ),
            username="agencyadmin",
            role="admin"
        )
        
        # 판매점 생성
        retail = Company.objects.create(
            name="테스트 판매점",
            type="retail",
            parent_company=agency
        )
        
        retail_user = CompanyUser.objects.create(
            company=retail,
            django_user=User.objects.create_user(
                username="retailuser",
                password="pass123!"
            ),
            username="retailuser",
            role="staff"
        )
        
        # 협력사 관리자는 하위 판매점 사용자 승인 가능
        self.assertTrue(retail_user.can_be_approved_by(agency_admin))
        
        # 협력사 관리자는 본사 사용자 승인 불가
        self.assertFalse(self.company_user.can_be_approved_by(agency_admin))
    
    def test_approve_reject_methods(self):
        """승인/거절 메서드 테스트"""
        # 승인 테스트
        self.company_user.approve(self.super_company_user)
        self.assertTrue(self.company_user.is_approved)
        self.assertEqual(self.company_user.status, "approved")
        
        # 새 사용자 생성 후 거절 테스트
        new_user = CompanyUser.objects.create(
            company=self.company,
            django_user=User.objects.create_user(
                username="newuser",
                password="pass123!"
            ),
            username="newuser",
            role="staff"
        )
        
        new_user.reject(self.super_company_user)
        self.assertFalse(new_user.is_approved)
        self.assertEqual(new_user.status, "rejected")

"""
회사 및 사용자 API 테스트
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import uuid
from companies.models import Company, CompanyUser


class CompanyAPITest(TestCase):
    """회사 API 테스트 클래스"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 슈퍼유저 생성
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123!'
        )
        
        # 본사 생성
        self.headquarters = Company.objects.create(
            name='테스트 본사',
            type='headquarters',
            status=True
        )
        
        # API 클라이언트 설정
        self.client = APIClient()
    
    def test_company_list_unauthenticated(self):
        """인증되지 않은 사용자의 회사 목록 조회 테스트"""
        response = self.client.get('/api/companies/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_company_list_authenticated(self):
        """인증된 사용자의 회사 목록 조회 테스트"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/api/companies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_company_creation(self):
        """회사 생성 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'name': '새로운 협력사',
            'type': 'agency',
            'parent_company': str(self.headquarters.id),
            'status': True,
            'visible': True
        }
        
        response = self.client.post('/api/companies/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 생성된 업체 확인
        company = Company.objects.get(name='새로운 협력사')
        self.assertEqual(company.type, 'agency')
        self.assertEqual(company.parent_company.id, self.headquarters.id)
        self.assertIsNotNone(company.code)
    
    def test_invalid_company_hierarchy(self):
        """잘못된 계층 구조로 회사 생성 시 실패 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        data = {
            'name': '잘못된 본사',
            'type': 'headquarters',
            'parent_company': str(self.headquarters.id),
            'status': True
        }
        
        response = self.client.post('/api/companies/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_company_update(self):
        """회사 수정 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        # 협력사 생성
        agency = Company.objects.create(
            name='수정할 협력사',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        
        data = {
            'name': '수정된 협력사',
            'type': 'agency',
            'parent_company': str(self.headquarters.id),
            'status': True
        }
        
        response = self.client.put(
            f'/api/companies/{agency.id}/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 수정된 업체 확인
        agency.refresh_from_db()
        self.assertEqual(agency.name, '수정된 협력사')
    
    def test_company_delete(self):
        """회사 삭제 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        # 삭제할 협력사 생성
        agency = Company.objects.create(
            name='삭제할 협력사',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        
        response = self.client.delete(f'/api/companies/{agency.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # 삭제 확인
        with self.assertRaises(Company.DoesNotExist):
            Company.objects.get(id=agency.id)
    
    def test_company_filter(self):
        """회사 필터링 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        # 협력사 생성
        Company.objects.create(
            name='협력사1',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        Company.objects.create(
            name='협력사2',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        
        response = self.client.get('/api/companies/?type=agency')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        for company in response.data['results']:
            self.assertEqual(company['type'], 'agency')
    
    def test_company_search(self):
        """회사 검색 테스트"""
        self.client.force_authenticate(user=self.superuser)
        
        # 검색 대상 업체 생성
        Company.objects.create(
            name='ABC 마트',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        Company.objects.create(
            name='XYZ 스토어',
            type='agency',
            parent_company=self.headquarters,
            status=True
        )
        
        response = self.client.get('/api/companies/?search=ABC')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        self.assertTrue(
            any('ABC' in company['name'] for company in results)
        )
        self.assertFalse(
            any('XYZ' in company['name'] for company in results)
        )


class CompanyUserAPITest(TestCase):
    """회사 사용자 API 테스트 클래스"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 슈퍼유저 생성
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123!'
        )
        
        # 본사 생성
        self.headquarters = Company.objects.create(
            name='테스트 본사',
            type='headquarters',
            status=True
        )
        
        # 관리자 생성
        self.admin_user = CompanyUser.objects.create(
            company=self.headquarters,
            django_user=self.superuser,
            username='admin',
            role='admin',
            is_approved=True,
            status='approved'
        )
        
        # API 클라이언트 설정
        self.client = APIClient()
        self.client.force_authenticate(user=self.superuser)
    
    def test_user_creation(self):
        """사용자 생성 테스트"""
        data = {
            'company': str(self.headquarters.id),
            'username': 'newuser',
            'password': 'newpass123!',
            'email': 'newuser@test.com',
            'role': 'staff'
        }
        
        response = self.client.post('/api/companies/users/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 생성된 사용자 확인
        company_user = CompanyUser.objects.get(username='newuser')
        self.assertEqual(company_user.role, 'staff')
        self.assertEqual(company_user.company.id, self.headquarters.id)
    
    def test_user_approval(self):
        """사용자 승인 테스트"""
        # 승인 대기 사용자 생성
        pending_user = CompanyUser.objects.create(
            company=self.headquarters,
            django_user=User.objects.create_user(
                username='pendinguser',
                password='pass123!'
            ),
            username='pendinguser',
            role='staff',
            status='pending'
        )
        
        # 승인 요청
        response = self.client.post(
            f'/api/companies/users/{pending_user.id}/approve/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 승인 확인
        pending_user.refresh_from_db()
        self.assertTrue(pending_user.is_approved)
        self.assertEqual(pending_user.status, 'approved')
    
    def test_pending_users_list(self):
        """승인 대기 사용자 목록 조회 테스트"""
        # 승인 대기 사용자 생성
        for i in range(3):
            CompanyUser.objects.create(
                company=self.headquarters,
                django_user=User.objects.create_user(
                    username=f'pending{i}',
                    password='pass123!'
                ),
                username=f'pending{i}',
                role='staff',
                status='pending'
            )
        
        response = self.client.get('/api/companies/users/pending_approvals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
# companies/tests.py
import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Company, CompanyUser, CompanyMessage


class CompanyModelTest(TestCase):
    """업체 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.company_data = {
            'name': '테스트 대리점',
            'type': 'agency',
            'status': True,
            'visible': True,
            'default_courier': 'CJ대한통운'
        }
    
    def test_company_creation(self):
        """업체 생성 테스트"""
        company = Company.objects.create(**self.company_data)
        
        self.assertEqual(company.name, '테스트 대리점')
        self.assertEqual(company.type, 'agency')
        self.assertTrue(company.status)
        self.assertTrue(isinstance(company.id, uuid.UUID))
    
    def test_company_string_representation(self):
        """업체 문자열 표현 테스트"""
        company = Company.objects.create(**self.company_data)
        expected_str = f"{company.name} ({company.get_type_display()})"
        self.assertEqual(str(company), expected_str)
    
    def test_company_toggle_status(self):
        """업체 상태 전환 테스트"""
        company = Company.objects.create(**self.company_data)
        original_status = company.status
        
        success = company.toggle_status()
        self.assertTrue(success)
        self.assertNotEqual(company.status, original_status)


class CompanyAPITest(APITestCase):
    """업체 API 테스트"""
    
    def setUp(self):
        """테스트 사용자 및 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.company_data = {
            'name': 'API 테스트 업체',
            'type': 'retail',
            'status': True,
            'visible': True
        }
    
    def test_create_company(self):
        """업체 생성 API 테스트"""
        url = '/api/companies/companies/'
        response = self.client.post(url, self.company_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Company.objects.get().name, 'API 테스트 업체')
    
    def test_list_companies(self):
        """업체 목록 조회 API 테스트"""
        Company.objects.create(**self.company_data)
        
        url = '/api/companies/companies/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_company_detail(self):
        """업체 상세 조회 API 테스트"""
        company = Company.objects.create(**self.company_data)
        
        url = f'/api/companies/companies/{company.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], company.name)
    
    def test_update_company(self):
        """업체 수정 API 테스트"""
        company = Company.objects.create(**self.company_data)
        
        url = f'/api/companies/companies/{company.id}/'
        updated_data = {'name': '수정된 업체명', 'type': 'retail'}
        response = self.client.patch(url, updated_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.name, '수정된 업체명')
    
    def test_toggle_company_status(self):
        """업체 상태 전환 API 테스트"""
        company = Company.objects.create(**self.company_data)
        original_status = company.status
        
        url = f'/api/companies/companies/{company.id}/toggle_status/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertNotEqual(company.status, original_status)


# policies/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from companies.models import Company
from .models import Policy, PolicyAssignment


class PolicyModelTest(TestCase):
    """정책 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.policy_data = {
            'title': '테스트 정책',
            'description': '테스트용 정책입니다.',
            'form_type': 'general',
            'rebate_agency': 50000.00,
            'rebate_retail': 30000.00,
            'expose': True,
            'created_by': self.user
        }
    
    def test_policy_creation(self):
        """정책 생성 테스트"""
        policy = Policy.objects.create(**self.policy_data)
        
        self.assertEqual(policy.title, '테스트 정책')
        self.assertEqual(policy.form_type, 'general')
        self.assertTrue(policy.expose)
        self.assertIsNotNone(policy.html_content)  # HTML 자동 생성 확인
    
    def test_policy_html_generation(self):
        """정책 HTML 자동 생성 테스트"""
        policy = Policy.objects.create(**self.policy_data)
        
        self.assertIsNotNone(policy.html_content)
        self.assertIn(policy.title, policy.html_content)
        self.assertIn(policy.description, policy.html_content)
    
    def test_policy_toggle_expose(self):
        """정책 노출 상태 전환 테스트"""
        policy = Policy.objects.create(**self.policy_data)
        original_expose = policy.expose
        
        success = policy.toggle_expose()
        self.assertTrue(success)
        self.assertNotEqual(policy.expose, original_expose)


class PolicyAssignmentTest(TestCase):
    """정책 배정 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='테스트 업체',
            type='agency',
            status=True
        )
        self.policy = Policy.objects.create(
            title='테스트 정책',
            description='테스트 설명',
            form_type='general',
            rebate_agency=50000.00,
            rebate_retail=30000.00,
            created_by=self.user
        )
    
    def test_policy_assignment_creation(self):
        """정책 배정 생성 테스트"""
        assignment = PolicyAssignment.objects.create(
            policy=self.policy,
            company=self.company,
            custom_rebate=40000.00,
            expose_to_child=True
        )
        
        self.assertEqual(assignment.policy, self.policy)
        self.assertEqual(assignment.company, self.company)
        self.assertEqual(assignment.custom_rebate, 40000.00)
    
    def test_effective_rebate_calculation(self):
        """효과적인 리베이트 계산 테스트"""
        # 커스텀 리베이트가 있는 경우
        assignment_with_custom = PolicyAssignment.objects.create(
            policy=self.policy,
            company=self.company,
            custom_rebate=40000.00
        )
        self.assertEqual(assignment_with_custom.get_effective_rebate(), 40000.00)
        
        # 커스텀 리베이트가 없는 경우 (기본값 사용)
        assignment_without_custom = PolicyAssignment.objects.create(
            policy=self.policy,
            company=self.company
        )
        self.assertEqual(assignment_without_custom.get_effective_rebate(), 50000.00)  # agency 기본값


# orders/tests.py
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from companies.models import Company
from policies.models import Policy
from .models import Order, OrderMemo, Invoice


class OrderModelTest(TestCase):
    """주문 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='테스트 업체',
            type='retail',
            status=True
        )
        self.order_data = {
            'customer_name': '홍길동',
            'customer_phone': '010-1234-5678',
            'customer_email': 'test@example.com',
            'model_name': 'Galaxy S23',
            'carrier': 'skt',
            'apply_type': 'new',
            'status': 'reserved',
            'company': self.company,
            'created_by': self.user
        }
    
    def test_order_creation(self):
        """주문 생성 테스트"""
        order = Order.objects.create(**self.order_data)
        
        self.assertEqual(order.customer_name, '홍길동')
        self.assertEqual(order.customer_phone, '010-1234-5678')
        self.assertEqual(order.status, 'reserved')
        self.assertEqual(order.company, self.company)
    
    def test_order_status_update(self):
        """주문 상태 업데이트 테스트"""
        order = Order.objects.create(**self.order_data)
        
        # 유효한 상태 전환 테스트
        success = order.update_status('received', self.user)
        self.assertTrue(success)
        self.assertEqual(order.status, 'received')
        
        # 유효하지 않은 상태 전환 테스트
        success = order.update_status('reserved', self.user)
        self.assertFalse(success)  # completed -> reserved는 불가능
    
    def test_order_memo_creation(self):
        """주문 메모 생성 테스트"""
        order = Order.objects.create(**self.order_data)
        memo = OrderMemo.objects.create(
            order=order,
            memo='테스트 메모입니다.',
            created_by=self.user
        )
        
        self.assertEqual(memo.order, order)
        self.assertEqual(memo.memo, '테스트 메모입니다.')
        self.assertEqual(order.get_memos().count(), 1)
    
    def test_invoice_creation(self):
        """송장 생성 테스트"""
        order = Order.objects.create(**self.order_data)
        invoice = Invoice.objects.create(
            order=order,
            courier='cj',
            invoice_number='1234567890'
        )
        
        self.assertEqual(invoice.order, order)
        self.assertEqual(invoice.courier, 'cj')
        self.assertEqual(invoice.invoice_number, '1234567890')
        self.assertFalse(invoice.is_delivered())
        
        # 송장 생성 시 주문 상태가 자동으로 완료로 변경되는지 확인
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')


class OrderAPITest(APITestCase):
    """주문 API 테스트"""
    
    def setUp(self):
        """테스트 사용자 및 데이터 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.company = Company.objects.create(
            name='테스트 업체',
            type='retail',
            status=True
        )
        
        self.order_data = {
            'customer_name': '김철수',
            'customer_phone': '010-9876-5432',
            'model_name': 'iPhone 15',
            'carrier': 'kt',
            'apply_type': 'new',
            'company': str(self.company.id)
        }
    
    def test_create_order(self):
        """주문 생성 API 테스트"""
        url = '/api/orders/orders/'
        response = self.client.post(url, self.order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        
        order = Order.objects.get()
        self.assertEqual(order.customer_name, '김철수')
        self.assertEqual(order.created_by, self.user)
    
    def test_update_order_status(self):
        """주문 상태 업데이트 API 테스트"""
        order = Order.objects.create(
            customer_name='테스트 고객',
            customer_phone='010-1111-2222',
            model_name='Test Phone',
            carrier='lgu',
            apply_type='new',
            company=self.company,
            status='reserved',
            created_by=self.user
        )
        
        url = f'/api/orders/orders/{order.id}/update_status/'
        data = {'new_status': 'received', 'memo': '접수 완료'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'received')
        
        # 메모가 자동으로 추가되었는지 확인
        self.assertEqual(order.order_memos.count(), 1)
    
    def test_order_statistics(self):
        """주문 통계 API 테스트"""
        # 테스트용 주문들 생성
        for i in range(3):
            Order.objects.create(
                customer_name=f'고객{i}',
                customer_phone=f'010-000-000{i}',
                model_name=f'Phone{i}',
                carrier='skt',
                apply_type='new',
                company=self.company,
                status='completed' if i == 0 else 'processing',
                created_by=self.user
            )
        
        url = '/api/orders/orders/statistics/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_orders'], 3)
        self.assertEqual(response.data['status_statistics']['completed']['count'], 1)
        self.assertEqual(response.data['status_statistics']['processing']['count'], 2)


# 테스트 실행 방법:
# python manage.py test companies.tests
# python manage.py test policies.tests  
# python manage.py test orders.tests
# python manage.py test  # 전체 테스트 실행
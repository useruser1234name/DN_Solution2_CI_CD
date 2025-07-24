# companies/tests.py
import uuid
import logging # Added for logging
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Company, CompanyUser, CompanyMessage

logger = logging.getLogger(__name__) # Initialized logger


class CompanyModelTest(TestCase):
    """
    `Company` 모델의 비즈니스 로직 및 유효성 검증을 테스트하는 클래스입니다.
    주로 모델의 `clean()` 및 `save()` 메서드의 동작을 검증합니다.
    """

    @classmethod
    def setUpTestData(cls):
        """
        테스트 클래스 로드 시 한 번만 실행되는 초기 설정 메서드입니다.
        모든 테스트 메서드에서 공유할 기본 `Company` 인스턴스들을 생성합니다.
        """
        logger.info("[CompanyModelTest.setUpTestData] 테스트 데이터 설정 시작.")
        cls.headquarters = Company.objects.create(
            name='본사',
            type='headquarters',
            status=True,
            visible=True
        )
        logger.info(f"[CompanyModelTest.setUpTestData] 본사 생성: {cls.headquarters.name} (ID: {cls.headquarters.id})")

        cls.agency = Company.objects.create(
            name='테스트 협력사',
            type='agency',
            parent_company=cls.headquarters,
            status=True,
            visible=True,
            default_courier='롯데택배'
        )
        logger.info(f"[CompanyModelTest.setUpTestData] 협력사 생성: {cls.agency.name} (ID: {cls.agency.id})")

        cls.retail = Company.objects.create(
            name='테스트 판매점',
            type='retail',
            parent_company=cls.agency,
            status=True,
            visible=True
        )
        logger.info(f"[CompanyModelTest.setUpTestData] 판매점 생성: {cls.retail.name} (ID: {cls.retail.id})")
        logger.info("[CompanyModelTest.setUpTestData] 테스트 데이터 설정 완료.")

    def test_company_creation(self):
        """
        `Company` 모델 인스턴스가 올바르게 생성되고 필드 값이 설정되는지 테스트합니다.
        특히, `agency` 타입의 업체가 상위 본사를 가지는지 확인합니다.
        """
        logger.info("[CompanyModelTest.test_company_creation] 업체 생성 테스트 시작.")
        company = self.agency # setUpTestData에서 생성된 협력사 인스턴스 사용
        self.assertEqual(company.name, '테스트 협력사', "생성된 업체의 이름이 일치해야 합니다.")
        self.assertEqual(company.type, 'agency', "생성된 업체의 유형이 'agency'여야 합니다.")
        self.assertTrue(company.status, "생성된 업체의 상태는 True여야 합니다.")
        self.assertTrue(isinstance(company.id, uuid.UUID), "업체 ID는 UUID 타입이어야 합니다.")
        self.assertEqual(company.parent_company, self.headquarters, "협력사의 상위 업체는 본사여야 합니다.")
        logger.info("[CompanyModelTest.test_company_creation] 업체 생성 테스트 완료.")

    def test_company_string_representation(self):
        """
        `Company` 모델 인스턴스의 문자열 표현(`__str__` 메서드)이 올바른지 테스트합니다.
        """
        logger.info("[CompanyModelTest.test_company_string_representation] 문자열 표현 테스트 시작.")
        company = self.retail # setUpTestData에서 생성된 판매점 인스턴스 사용
        expected_str = f"{company.name} ({company.get_type_display()})"
        self.assertEqual(str(company), expected_str, "__str__ 메서드의 반환 값이 예상과 일치해야 합니다.")
        logger.info("[CompanyModelTest.test_company_string_representation] 문자열 표현 테스트 완료.")

    def test_company_toggle_status(self):
        """
        `Company.toggle_status()` 메서드가 업체의 운영 상태를 올바르게 변경하는지 테스트합니다.
        """
        logger.info("[CompanyModelTest.test_company_toggle_status] 상태 전환 테스트 시작.")
        company = self.agency # setUpTestData에서 생성된 협력사 인스턴스 사용
        original_status = company.status # 초기 상태 기록
        
        success = company.toggle_status() # 상태 토글 메서드 호출
        self.assertTrue(success, "toggle_status 메서드는 성공 시 True를 반환해야 합니다.")
        company.refresh_from_db() # 데이터베이스에서 최신 상태를 다시 로드
        self.assertNotEqual(company.status, original_status, "업체의 상태가 성공적으로 변경되어야 합니다.")
        logger.info(f"[CompanyModelTest.test_company_toggle_status] 상태 전환 테스트 완료. 이전: {original_status}, 현재: {company.status}")


class CompanyAPITest(APITestCase):
    """
    `Company` 및 `CompanyUser` 관련 API 엔드포인트의 동작과
    사용자 역할에 따른 접근 권한을 테스트하는 클래스입니다.
    """

    @classmethod
    def setUpTestData(cls):
        """
        테스트 클래스 로드 시 한 번만 실행되는 초기 설정 메서드입니다.
        API 테스트를 위한 기본 `Company` 및 `User` 인스턴스들을 생성합니다.
        """
        logger.info("[CompanyAPITest.setUpTestData] API 테스트 데이터 설정 시작.")
        # 기본 업체 생성
        cls.headquarters = Company.objects.create(
            name='API 본사',
            type='headquarters',
            status=True,
            visible=True
        )
        logger.info(f"[CompanyAPITest.setUpTestData] 본사 생성: {cls.headquarters.name}")

        cls.agency = Company.objects.create(
            name='API 협력사',
            type='agency',
            parent_company=cls.headquarters,
            status=True,
            visible=True
        )
        logger.info(f"[CompanyAPITest.setUpTestData] 협력사 생성: {cls.agency.name}")

        cls.retail = Company.objects.create(
            name='API 판매점',
            type='retail',
            parent_company=cls.agency,
            status=True,
            visible=True
        )
        logger.info(f"[CompanyAPITest.setUpTestData] 판매점 생성: {cls.retail.name}")
        
        # Django 기본 User 모델 인스턴스 생성 (API 인증용)
        cls.hq_django_user = User.objects.create_user(username='hq_admin', password='testpass', is_superuser=True)
        logger.info(f"[CompanyAPITest.setUpTestData] Django User 생성: {cls.hq_django_user.username} (Superuser)")
        cls.agency_django_user = User.objects.create_user(username='agency_admin', password='testpass')
        logger.info(f"[CompanyAPITest.setUpTestData] Django User 생성: {cls.agency_django_user.username}")
        cls.retail_django_user = User.objects.create_user(username='retail_staff', password='testpass')
        logger.info(f"[CompanyAPITest.setUpTestData] Django User 생성: {cls.retail_django_user.username}")

        # CompanyUser 모델 인스턴스 생성 (업체 소속 정보용)
        cls.hq_company_user = CompanyUser.objects.create(company=cls.headquarters, username='hq_admin', password='testpass', role='admin')
        logger.info(f"[CompanyAPITest.setUpTestData] CompanyUser 생성: {cls.hq_company_user.username} (소속: {cls.hq_company_user.company.name})")
        cls.agency_company_user = CompanyUser.objects.create(company=cls.agency, username='agency_admin', password='testpass', role='admin')
        logger.info(f"[CompanyAPITest.setUpTestData] CompanyUser 생성: {cls.agency_company_user.username} (소속: {cls.agency_company_user.company.name})")
        cls.retail_company_user = CompanyUser.objects.create(company=cls.retail, username='retail_staff', password='testpass', role='staff')
        logger.info(f"[CompanyAPITest.setUpTestData] CompanyUser 생성: {cls.retail_company_user.username} (소속: {cls.retail_company_user.company.name})")
        logger.info("[CompanyAPITest.setUpTestData] API 테스트 데이터 설정 완료.")

    def setUp(self):
        """
        각 테스트 메서드가 실행되기 전에 호출되는 설정 메서드입니다.
        테스트 클라이언트의 인증 상태를 초기화하고, 공통적으로 사용될 데이터를 설정합니다.
        """
        logger.info("[CompanyAPITest.setUp] 각 테스트 시작 전 설정.")
        # 기본적으로 본사 관리자로 인증하여 대부분의 생성/수정/삭제 테스트를 수행합니다.
        self.client.force_authenticate(user=self.hq_django_user)
        logger.info(f"[CompanyAPITest.setUp] 클라이언트 인증: {self.hq_django_user.username}")
        
        # 새로운 업체 생성을 위한 공통 데이터 정의
        self.company_data_for_retail = {
            'name': '새로운 API 판매점',
            'type': 'retail',
            'parent_company': str(self.agency.id), # 협력사를 상위로 지정
            'status': True,
            'visible': True
        }
        self.company_data_for_agency = {
            'name': '새로운 API 협력사',
            'type': 'agency',
            'parent_company': str(self.headquarters.id), # 본사를 상위로 지정
            'status': True,
            'visible': True
        }
        logger.info("[CompanyAPITest.setUp] 테스트 공통 데이터 설정 완료.")

    def test_create_company_retail(self):
        """
        본사 관리자 권한으로 새로운 판매점 업체를 생성하는 API 테스트입니다.
        판매점이 올바른 상위 업체(협력사) 하위에 생성되는지 확인합니다.
        """
        logger.info("[CompanyAPITest.test_create_company_retail] 판매점 생성 API 테스트 시작.")
        url = '/api/companies/companies/'
        response = self.client.post(url, self.company_data_for_retail, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"판매점 생성 실패: {response.data}")
        self.assertEqual(Company.objects.filter(name='새로운 API 판매점').count(), 1, "새로운 판매점이 하나 생성되어야 합니다.")
        created_company = Company.objects.get(name='새로운 API 판매점')
        self.assertEqual(created_company.parent_company, self.agency, "생성된 판매점의 상위 업체는 지정된 협력사여야 합니다.")
        logger.info("[CompanyAPITest.test_create_company_retail] 판매점 생성 API 테스트 완료.")

    def test_create_company_retail(self):
            """
            협력사 관리자 권한으로 새로운 판매점 업체를 생성하는 API 테스트입니다.
            (본사는 판매점을 직접 생성할 수 없으므로 협력사 권한으로 테스트)
            판매점이 올바른 상위 업체(협력사) 하위에 생성되는지 확인합니다.
            """
            logger.info("[CompanyAPITest.test_create_company_retail] 판매점 생성 API 테스트 시작.")
            
            # 협력사 관리자로 인증 변경 (본사는 판매점을 직접 생성할 수 없음)
            self.client.force_authenticate(user=self.agency_django_user)
            
            url = '/api/companies/companies/'
            response = self.client.post(url, self.company_data_for_retail, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"판매점 생성 실패: {response.data}")
            self.assertEqual(Company.objects.filter(name='새로운 API 판매점').count(), 1, "새로운 판매점이 하나 생성되어야 합니다.")
            created_company = Company.objects.get(name='새로운 API 판매점')
            self.assertEqual(created_company.parent_company, self.agency, "생성된 판매점의 상위 업체는 지정된 협력사여야 합니다.")
            logger.info("[CompanyAPITest.test_create_company_retail] 판매점 생성 API 테스트 완료.")


    def test_list_companies_headquarters_user(self):
        """
        본사 관리자 권한으로 모든 업체 목록을 조회하는 API 테스트입니다.
        시스템 내의 모든 업체가 조회되는지 확인합니다.
        """
        logger.info("[CompanyAPITest.test_list_companies_headquarters_user] 본사 사용자 업체 목록 조회 테스트 시작.")
        self.client.force_authenticate(user=self.hq_django_user)
        url = '/api/companies/companies/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"본사 사용자 업체 목록 조회 실패: {response.data}")
        # 최소한 setUpTestData에서 생성된 본사, 협력사, 판매점 3개는 조회되어야 합니다.
        self.assertGreaterEqual(len(response.data['results']), 3, "본사 사용자는 최소 3개 이상의 업체를 조회해야 합니다.")
        logger.info("[CompanyAPITest.test_list_companies_headquarters_user] 본사 사용자 업체 목록 조회 테스트 완료.")

    def test_list_companies_agency_user(self):
        """
        협력사 관리자 권한으로 자신의 업체와 하위 판매점 목록을 조회하는 API 테스트입니다.
        다른 협력사나 본사는 조회되지 않아야 합니다.
        """
        logger.info("[CompanyAPITest.test_list_companies_agency_user] 협력사 사용자 업체 목록 조회 테스트 시작.")
        self.client.force_authenticate(user=self.agency_django_user)
        url = '/api/companies/companies/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"협력사 사용자 업체 목록 조회 실패: {response.data}")
        # 협력사 본인 + 하위 판매점 = 2개 업체가 조회되어야 합니다.
        self.assertEqual(len(response.data['results']), 2, "협력사 사용자는 자신의 업체와 하위 판매점만 조회해야 합니다.")
        company_ids = [c['id'] for c in response.data['results']]
        self.assertIn(str(self.agency.id), company_ids, "조회된 목록에 자신의 협력사 ID가 포함되어야 합니다.")
        self.assertIn(str(self.retail.id), company_ids, "조회된 목록에 하위 판매점 ID가 포함되어야 합니다.")
        self.assertNotIn(str(self.headquarters.id), company_ids, "조회된 목록에 본사 ID가 포함되지 않아야 합니다.")
        logger.info("[CompanyAPITest.test_list_companies_agency_user] 협력사 사용자 업체 목록 조회 테스트 완료.")

    def test_list_companies_retail_user(self):
        """
        판매점 직원 권한으로 자신의 업체만 조회하는 API 테스트입니다.
        다른 업체(본사, 협력사, 다른 판매점)는 조회되지 않아야 합니다.
        """
        logger.info("[CompanyAPITest.test_list_companies_retail_user] 판매점 사용자 업체 목록 조회 테스트 시작.")
        self.client.force_authenticate(user=self.retail_django_user)
        url = '/api/companies/companies/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"판매점 사용자 업체 목록 조회 실패: {response.data}")
        # 판매점 본인 = 1개 업체가 조회되어야 합니다.
        self.assertEqual(len(response.data['results']), 1, "판매점 사용자는 자신의 업체만 조회해야 합니다.")
        self.assertEqual(response.data['results'][0]['id'], str(self.retail.id), "조회된 업체 ID가 자신의 판매점 ID와 일치해야 합니다.")
        logger.info("[CompanyAPITest.test_list_companies_retail_user] 판매점 사용자 업체 목록 조회 테스트 완료.")

    def test_company_detail(self):
        """
        특정 업체의 상세 정보를 조회하는 API 테스트입니다.
        본사 관리자 권한으로 판매점의 상세 정보를 조회합니다.
        """
        logger.info("[CompanyAPITest.test_company_detail] 업체 상세 조회 API 테스트 시작.")
        company = self.retail # 기존에 생성된 판매점 사용
        url = f'/api/companies/companies/{company.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"업체 상세 조회 실패: {response.data}")
        self.assertEqual(response.data['name'], company.name, "조회된 업체명이 일치해야 합니다.")
        logger.info("[CompanyAPITest.test_company_detail] 업체 상세 조회 API 테스트 완료.")

    def test_update_company(self):
        """
        특정 업체의 정보를 수정하는 API 테스트입니다.
        본사 관리자 권한으로 판매점의 이름을 수정합니다.
        """
        logger.info("[CompanyAPITest.test_update_company] 업체 수정 API 테스트 시작.")
        company = self.retail # 기존에 생성된 판매점 사용
        url = f'/api/companies/companies/{company.id}/'
        updated_name = '수정된 판매점명'
        updated_data = {'name': updated_name, 'type': 'retail', 'parent_company': str(self.agency.id)} # parent_company 유지
        response = self.client.patch(url, updated_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"업체 수정 실패: {response.data}")
        company.refresh_from_db() # 데이터베이스에서 최신 상태를 다시 로드
        self.assertEqual(company.name, updated_name, "업체명이 성공적으로 수정되어야 합니다.")
        logger.info("[CompanyAPITest.test_update_company] 업체 수정 API 테스트 완료.")

    def test_toggle_company_status(self):
        """
        특정 업체의 운영 상태를 토글하는 API 테스트입니다.
        본사 관리자 권한으로 판매점의 상태를 변경합니다.
        """
        logger.info("[CompanyAPITest.test_toggle_company_status] 업체 상태 전환 API 테스트 시작.")
        company = self.retail # 기존에 생성된 판매점 사용
        original_status = company.status # 초기 상태 기록
        
        url = f'/api/companies/companies/{company.id}/toggle_status/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"업체 상태 전환 실패: {response.data}")
        company.refresh_from_db() # 데이터베이스에서 최신 상태를 다시 로드
        self.assertNotEqual(company.status, original_status, "업체의 상태가 성공적으로 변경되어야 합니다.")
        logger.info("[CompanyAPITest.test_toggle_company_status] 업체 상태 전환 API 테스트 완료.")

    def test_create_company_user(self):
        """
        본사 관리자 권한으로 새로운 업체 사용자(직원)를 생성하는 API 테스트입니다.
        """
        logger.info("[CompanyAPITest.test_create_company_user] 회사 사용자 생성 API 테스트 시작.")
        self.client.force_authenticate(user=self.hq_django_user) # 본사 관리자로 인증
        user_data = {
            'company': str(self.agency.id), # 협력사 소속으로 사용자 생성
            'username': 'new_agency_staff',
            'password': 'newpass123',
            'role': 'staff'
        }
        url = '/api/companies/users/'
        response = self.client.post(url, user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"회사 사용자 생성 실패: {response.data}")
        self.assertEqual(CompanyUser.objects.filter(username='new_agency_staff').count(), 1, "새로운 업체 사용자가 하나 생성되어야 합니다.")
        created_user = CompanyUser.objects.get(username='new_agency_staff')
        self.assertEqual(created_user.company, self.agency, "생성된 사용자의 소속 업체가 지정된 협력사여야 합니다.")
        logger.info("[CompanyAPITest.test_create_company_user] 회사 사용자 생성 API 테스트 완료.")

    def test_company_user_visibility_agency_to_retail(self):
        """
        협력사 관리자 권한으로 자신의 업체(협력사)에 속한 사용자와
        자신의 하위 판매점(retail)에 속한 사용자들을 모두 조회하는 API 테스트입니다.
        """
        logger.info("[CompanyAPITest.test_company_user_visibility_agency_to_retail] 협력사 사용자 가시성 테스트 시작.")
        self.client.force_authenticate(user=self.agency_django_user)
        url = f'/api/companies/companies/{self.agency.id}/users/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"사용자 목록 조회 실패: {response.data}")
        user_usernames = [u['username'] for u in response.data['users']]
        
        # 협력사 관리자 본인과 하위 판매점 직원이 목록에 포함되어야 합니다.
        self.assertIn(self.__class__.agency_company_user.username, user_usernames, "협력사 관리자 본인이 목록에 포함되어야 합니다.")
        self.assertIn(self.__class__.retail_company_user.username, user_usernames, "하위 판매점 직원이 목록에 포함되어야 합니다.")
        
        # 본사 관리자는 포함되지 않아야 합니다.
        self.assertNotIn(self.__class__.hq_company_user.username, user_usernames, "본사 관리자는 목록에 포함되지 않아야 합니다.")
        logger.info("[CompanyAPITest.test_company_user_visibility_agency_to_retail] 협력사 사용자 가시성 테스트 완료.")

    def test_company_user_visibility_retail_cannot_see_other_retail(self):
        """
        판매점 직원 권한으로 다른 판매점의 사용자 정보를 조회할 수 없는지 테스트합니다.
        """
        logger.info("[CompanyAPITest.test_company_user_visibility_retail_cannot_see_other_retail] 판매점 사용자 가시성 테스트 시작.")
        # 테스트를 위한 다른 협력사 및 판매점 생성
        other_agency = Company.objects.create(
            name='다른 API 협력사',
            type='agency',
            parent_company=self.headquarters,
            status=True,
            visible=True
        )
        other_retail = Company.objects.create(
            name='다른 API 판매점',
            type='retail',
            parent_company=other_agency,
            status=True,
            visible=True
        )
        # 다른 판매점의 Django User 및 CompanyUser 생성
        other_retail_django_user = User.objects.create_user(username='other_retail_staff', password='testpass')
        other_retail_company_user = CompanyUser.objects.create(company=other_retail, username=other_retail_django_user.username, password='testpass', role='staff')

        self.client.force_authenticate(user=self.retail_django_user) # 현재 판매점 직원으로 인증
        url = f'/api/companies/companies/{other_retail.id}/users/' # 다른 판매점의 사용자 목록 조회 시도
        response = self.client.get(url)
        
        # 접근이 거부되거나 찾을 수 없다는 응답이 와야 합니다.
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN], 
                      f"다른 판매점 사용자 조회 시 접근이 거부되어야 합니다. 현재 상태: {response.status_code}")
        logger.info("[CompanyAPITest.test_company_user_visibility_retail_cannot_see_other_retail] 판매점 사용자 가시성 테스트 완료.")    def test_headquarters_cannot_create_retail_directly(self):
        """
        본사 관리자가 판매점을 직접 생성할 수 없는지 테스트합니다.
        본사는 협력사만 생성할 수 있고, 판매점은 협력사가 생성해야 합니다.
        """
        logger.info("[CompanyAPITest.test_headquarters_cannot_create_retail_directly] 본사 판매점 직접 생성 금지 테스트 시작.")
        self.client.force_authenticate(user=self.hq_django_user) # 본사 관리자로 인증
        
        # 본사가 판매점을 직접 생성하려는 데이터 (상위 업체로 협력사 지정)
        invalid_retail_data = {
            'name': '본사 직접 생성 판매점',
            'type': 'retail',
            'parent_company': str(self.agency.id), # 유효한 협력사를 상위로 지정
            'status': True,
            'visible': True
        }
        url = '/api/companies/companies/'
        response = self.client.post(url, invalid_retail_data, format='json')
        
        # 본사가 판매점을 직접 생성하는 것이 금지되어야 하므로 403 Forbidden이 와야 합니다.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, 
                        f"본사의 판매점 직접 생성은 403 Forbidden으로 거부되어야 합니다. 현재 상태: {response.status_code}, 응답: {response.data}")
        self.assertIn('본사 계정은 판매점을 직접 생성할 수 없습니다', str(response.data), "적절한 에러 메시지가 반환되어야 합니다.")
        self.assertFalse(Company.objects.filter(name='본사 직접 생성 판매점').exists(), "판매점이 생성되지 않아야 합니다.")
        logger.info("[CompanyAPITest.test_headquarters_cannot_create_retail_directly] 본사 판매점 직접 생성 금지 테스트 완료.")


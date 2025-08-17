"""
Company 인증 관련 Views

회원가입, 로그인 등 인증 관련 뷰를 별도로 분리합니다.
"""

import logging
from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer
from .services import CompanyService, CompanyUserService

logger = logging.getLogger('companies')


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    커스텀 JWT 로그인 뷰
    승인된 CompanyUser만 로그인 가능
    """
    serializer_class = CustomTokenObtainPairSerializer


class SignupChoiceView(APIView):
    """회원가입 유형 선택 페이지"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """회원가입 유형 선택 페이지 렌더링"""
        return render(request, 'companies/signup_choice.html')


class AdminSignupView(APIView):
    """관리자 회원가입"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """관리자 회원가입 페이지 렌더링"""
        return render(request, 'companies/admin_signup.html')
    
    def post(self, request):
        """관리자 회원가입 처리"""
        logger.info(f"[AdminSignupView] 관리자 회원가입 요청 - IP: {request.META.get('REMOTE_ADDR')}")
        
        try:
            # 필수 필드 검증
            required_fields = ['username', 'password', 'company_name', 'company_type']
            for field in required_fields:
                if not request.data.get(field):
                    return Response(
                        {'error': f'{field}는 필수 입력 사항입니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 데이터 추출
            username = request.data.get('username')
            password = request.data.get('password')
            company_name = request.data.get('company_name')
            company_type = request.data.get('company_type')
            parent_code = request.data.get('parent_code', '')
            email = request.data.get('email', '')
            
            # 본사가 아닌 경우 부모 코드 필수
            if company_type != 'headquarters' and not parent_code:
                return Response(
                    {'error': '본사가 아닌 경우 상위 업체 코드를 입력해야 합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 회사 데이터 준비
            company_data = {
                'name': company_name,
                'type': company_type,
                'parent_code': parent_code if parent_code else None
            }
            
            # 관리자 데이터 준비
            admin_data = {
                'username': username,
                'password': password,
                'email': email,
                'role': 'admin'
            }
            
            # 서비스를 통한 생성
            result = CompanyService.create_company_with_admin(company_data, admin_data)
            
            logger.info(f"[AdminSignupView] 관리자 회원가입 성공 - 사용자: {username}, 업체: {company_name}")
            
            return Response({
                'success': True,
                'message': result['message'],
                'company_code': result['company'].code
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[AdminSignupView] 관리자 회원가입 실패: {str(e)}")
            return Response(
                {'error': str(e) if 'ValidationError' in str(type(e)) else '회원가입 중 오류가 발생했습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST if 'ValidationError' in str(type(e)) else status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StaffSignupView(APIView):
    """직원 회원가입 (본사 전용)"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """직원 회원가입 페이지 렌더링"""
        return render(request, 'companies/staff_signup.html')
    
    def post(self, request):
        """직원 회원가입 처리"""
        logger.info(f"[StaffSignupView] 직원 회원가입 요청 - IP: {request.META.get('REMOTE_ADDR')}")
        
        try:
            # 필수 필드 검증
            required_fields = ['username', 'password', 'company_code']
            for field in required_fields:
                if not request.data.get(field):
                    return Response(
                        {'error': f'{field}는 필수 입력 사항입니다.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            username = request.data.get('username')
            password = request.data.get('password')
            company_code = request.data.get('company_code')
            email = request.data.get('email', '')
            
            # 추가 데이터 준비
            additional_data = {'email': email} if email else None
            
            # 서비스를 통한 생성
            result = CompanyUserService.create_staff_user(
                username=username,
                password=password,
                company_code=company_code,
                additional_data=additional_data
            )
            
            logger.info(f"[StaffSignupView] 직원 회원가입 성공 - 사용자: {username}")
            
            return Response({
                'success': True,
                'message': result['message'],
                'company_name': result['company_user'].company.name
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"[StaffSignupView] 직원 회원가입 실패: {str(e)}")
            return Response(
                {'error': str(e) if 'ValidationError' in str(type(e)) else '회원가입 중 오류가 발생했습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST if 'ValidationError' in str(type(e)) else status.HTTP_500_INTERNAL_SERVER_ERROR
            )

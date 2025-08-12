# -*- coding: utf-8 -*-
"""
Authentication Views - DN_SOLUTION2 리모델링
개선된 JWT 인증 뷰들
"""

import logging
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from companies.models import CompanyUser
from dn_solution.jwt_auth import (
    EnhancedJWTAuthentication, CustomTokenGenerator, 
    TokenManager, TokenPermissionValidator
)
# from dn_solution.cache_manager import cache_manager, CacheManager - removed
from django.core.cache import cache

logger = logging.getLogger('auth')


class EnhancedTokenObtainPairView(TokenObtainPairView):
    """개선된 JWT 토큰 발급 뷰"""
    
    def post(self, request, *args, **kwargs):
        """로그인 및 토큰 발급"""
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            
            if not username or not password:
                return Response({
                    'error': '사용자명과 비밀번호를 입력해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 로그인 시도 기록 (보안)
            self._log_login_attempt(username, request)
            
            # 사용자 인증
            user = authenticate(username=username, password=password)
            if not user:
                self._log_failed_login(username, request, '인증 실패')
                return Response({
                    'error': '사용자명 또는 비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 계정 상태 확인
            validation_result = self._validate_user_account(user)
            if not validation_result['valid']:
                self._log_failed_login(username, request, validation_result['reason'])
                return Response({
                    'error': validation_result['message']
                }, status=status.HTTP_403_FORBIDDEN)
            
            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # 사용자 데이터 캐싱
            user_data = cache_user_data(user.id, data_type='profile')
            
            # 로그인 성공 기록
            self._log_successful_login(user, request)
            
            # 최종 로그인 시간 업데이트
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            response_data = {
                'access': access_token,
                'refresh': refresh_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'expires_in': 3600,  # 1시간
                'token_type': 'Bearer'
            }
            
            # 회사 정보 추가
            if hasattr(user, 'companyuser'):
                company_user = user.companyuser
                response_data['company'] = {
                    'id': company_user.company.id,
                    'code': company_user.company.code,
                    'name': company_user.company.name,
                    'type': company_user.company.type,
                }
                response_data['role'] = company_user.role
                response_data['permissions'] = self._get_user_permissions(user)
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"토큰 발급 실패: {e}")
            return Response({
                'error': '로그인 처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_user_account(self, user) -> dict:
        """사용자 계정 상태 검증"""
        if not user.is_active:
            return {
                'valid': False,
                'reason': '비활성 계정',
                'message': '계정이 비활성화되었습니다. 관리자에게 문의하세요.'
            }
        
        # CompanyUser 상태 확인
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            
            if company_user.status == 'pending':
                return {
                    'valid': False,
                    'reason': '승인 대기',
                    'message': '계정 승인이 완료되지 않았습니다. 관리자의 승인을 기다려주세요.'
                }
            elif company_user.status == 'rejected':
                return {
                    'valid': False,
                    'reason': '승인 거부',
                    'message': '계정 승인이 거부되었습니다. 관리자에게 문의하세요.'
                }
            elif company_user.status != 'approved':
                return {
                    'valid': False,
                    'reason': '비정상 상태',
                    'message': f'계정 상태가 올바르지 않습니다: {company_user.status}'
                }
            
            # 회사 상태 확인
            if not company_user.company.status:
                return {
                    'valid': False,
                    'reason': '회사 비활성',
                    'message': '소속 회사가 비활성화되었습니다.'
                }
        
        return {'valid': True}
    
    def _get_user_permissions(self, user) -> list:
        """사용자 권한 목록 조회"""
        permissions = []
        
        if user.is_superuser:
            permissions.append('superuser')
        
        if hasattr(user, 'companyuser'):
            company_user = user.companyuser
            company_type = company_user.company.type
            
            # 회사 타입별 기본 권한
            if company_type == 'headquarters':
                permissions.extend(['view_all_companies', 'manage_agencies', 'view_all_reports'])
            elif company_type == 'agency':
                permissions.extend(['manage_retailers', 'view_subordinate_reports'])
            elif company_type == 'retail':
                permissions.extend(['manage_orders', 'view_own_reports'])
            
            # 역할별 권한
            if company_user.role == 'admin':
                permissions.extend(['manage_users', 'approve_users'])
            elif company_user.role == 'manager':
                permissions.extend(['view_reports', 'manage_orders'])
            
            # 주 관리자 권한
            if getattr(company_user, 'is_primary_admin', False):
                permissions.append('primary_admin')
        
        return list(set(permissions))  # 중복 제거
    
    def _log_login_attempt(self, username: str, request):
        """로그인 시도 기록"""
        logger.info(f"로그인 시도: {username} (IP: {self._get_client_ip(request)})")
    
    def _log_successful_login(self, user, request):
        """성공한 로그인 기록"""
        logger.info(f"로그인 성공: {user.username} (IP: {self._get_client_ip(request)})")
        
        # 최근 로그인 IP를 캐시에 저장
        cache_key = f"recent_login_ip:{user.id}"
        recent_ips = cache_manager.get(cache_key, [])
        
        current_ip = self._get_client_ip(request)
        if current_ip not in recent_ips:
            recent_ips.append(current_ip)
            # 최근 5개 IP만 유지
            recent_ips = recent_ips[-5:]
            cache_manager.set(cache_key, recent_ips, CacheManager.CACHE_TIMEOUTS['daily'])
    
    def _log_failed_login(self, username: str, request, reason: str):
        """실패한 로그인 기록"""
        ip = self._get_client_ip(request)
        logger.warning(f"로그인 실패: {username} (IP: {ip}, 사유: {reason})")
        
        # 실패 횟수 추적 (IP별)
        cache_key = f"failed_login:{ip}"
        failed_count = cache_manager.get(cache_key, 0)
        failed_count += 1
        
        # 5분간 실패 횟수 저장
        cache_manager.set(cache_key, failed_count, 300)
        
        if failed_count >= 5:
            logger.error(f"IP {ip}에서 5회 이상 로그인 실패")
    
    def _get_client_ip(self, request) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'


class EnhancedTokenRefreshView(TokenRefreshView):
    """개선된 JWT 토큰 갱신 뷰"""
    
    def post(self, request, *args, **kwargs):
        """토큰 갱신"""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'error': 'refresh 토큰이 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 토큰 정보 조회
            try:
                token_info = TokenManager.get_token_info(refresh_token)
            except TokenError as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 사용자 조회
            try:
                user = User.objects.get(id=token_info['user_id'])
            except User.DoesNotExist:
                return Response({
                    'error': '사용자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 사용자 상태 재확인
            if not user.is_active:
                return Response({
                    'error': '비활성화된 계정입니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 새 토큰 생성
            access_token, new_refresh_token = CustomTokenGenerator.generate_tokens(user)
            
            # 기존 refresh 토큰 블랙리스트 추가
            TokenManager.blacklist_token(refresh_token)
            
            logger.info(f"토큰 갱신: {user.username}")
            
            return Response({
                'access': access_token,
                'refresh': new_refresh_token,
                'expires_in': 3600,
            })
            
        except Exception as e:
            logger.error(f"토큰 갱신 실패: {e}")
            return Response({
                'error': '토큰 갱신 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """로그아웃 뷰"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """로그아웃 및 토큰 무효화"""
        try:
            refresh_token = request.data.get('refresh')
            
            # Refresh 토큰이 제공된 경우 블랙리스트 추가
            if refresh_token:
                TokenManager.blacklist_token(refresh_token)
            
            # 현재 사용자의 모든 토큰 무효화 (선택적)
            revoke_all = request.data.get('revoke_all_tokens', False)
            if revoke_all:
                revoked_count = TokenManager.revoke_user_tokens(request.user)
                logger.info(f"사용자 {request.user.username}의 모든 토큰 무효화: {revoked_count}개")
            
            # 사용자 관련 캐시 삭제
            cache_manager.delete_pattern(f'user:{request.user.id}:*')
            cache_manager.delete_pattern(f'token_usage:{request.user.id}:*')
            
            logger.info(f"로그아웃: {request.user.username}")
            
            return Response({
                'message': '성공적으로 로그아웃되었습니다.'
            })
            
        except Exception as e:
            logger.error(f"로그아웃 실패: {e}")
            return Response({
                'error': '로그아웃 처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenInfoView(APIView):
    """토큰 정보 조회 뷰"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """현재 토큰 정보 조회"""
        try:
            # Authorization 헤더에서 토큰 추출
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return Response({
                    'error': '유효한 Bearer 토큰이 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            token = auth_header.split(' ')[1]
            token_info = TokenManager.get_token_info(token)
            
            # 추가 정보 포함
            response_data = token_info.copy()
            response_data.update({
                'is_valid': True,
                'user_active': request.user.is_active,
                'permissions': self._get_user_permissions(request.user),
            })
            
            # 시간 정보를 ISO 형식으로 변환
            if 'issued_at' in response_data and isinstance(response_data['issued_at'], datetime):
                response_data['issued_at'] = response_data['issued_at'].isoformat()
            if 'expires_at' in response_data and isinstance(response_data['expires_at'], datetime):
                response_data['expires_at'] = response_data['expires_at'].isoformat()
            
            return Response(response_data)
            
        except TokenError as e:
            return Response({
                'error': str(e),
                'is_valid': False
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"토큰 정보 조회 실패: {e}")
            return Response({
                'error': '토큰 정보 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_user_permissions(self, user) -> list:
        """사용자 권한 목록 조회 (캐시 활용)"""
        cache_key = f"user_permissions:{user.id}"
        permissions = cache_manager.get(cache_key)
        
        if permissions is None:
            permissions = []
            
            if user.is_superuser:
                permissions.append('superuser')
            
            if hasattr(user, 'companyuser'):
                company_user = user.companyuser
                company_type = company_user.company.type
                
                # 회사 타입별 기본 권한
                if company_type == 'headquarters':
                    permissions.extend(['view_all_companies', 'manage_agencies', 'view_all_reports'])
                elif company_type == 'agency':
                    permissions.extend(['manage_retailers', 'view_subordinate_reports'])
                elif company_type == 'retail':
                    permissions.extend(['manage_orders', 'view_own_reports'])
                
                # 역할별 권한
                if company_user.role == 'admin':
                    permissions.extend(['manage_users', 'approve_users'])
                elif company_user.role == 'manager':
                    permissions.extend(['view_reports', 'manage_orders'])
                
                # 주 관리자 권한
                if getattr(company_user, 'is_primary_admin', False):
                    permissions.append('primary_admin')
            
            permissions = list(set(permissions))  # 중복 제거
            cache_manager.set(cache_key, permissions, CacheManager.CACHE_TIMEOUTS['long'])
        
        return permissions


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_api_token(request):
    """API 전용 토큰 생성"""
    try:
        scopes = request.data.get('scopes', ['read'])
        expires_in = request.data.get('expires_in', 86400)  # 기본 24시간
        
        # 권한 검증 (API 토큰 생성 권한이 있는지 확인)
        if not request.user.is_staff and not hasattr(request.user, 'companyuser'):
            return Response({
                'error': 'API 토큰 생성 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 만료 시간 제한 (최대 30일)
        max_expires_in = 30 * 24 * 3600  # 30일
        if expires_in > max_expires_in:
            expires_in = max_expires_in
        
        api_token = CustomTokenGenerator.generate_api_token(
            request.user, scopes=scopes, expires_in=expires_in
        )
        
        logger.info(f"API 토큰 생성: 사용자 {request.user.username}, 스코프: {scopes}")
        
        return Response({
            'api_token': api_token,
            'scopes': scopes,
            'expires_in': expires_in,
            'expires_at': (timezone.now() + timedelta(seconds=expires_in)).isoformat(),
        })
        
    except TokenError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"API 토큰 생성 실패: {e}")
        return Response({
            'error': 'API 토큰 생성 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_tokens(request):
    """사용자 토큰 전체 무효화"""
    try:
        # 관리자만 다른 사용자의 토큰을 무효화할 수 있음
        target_user_id = request.data.get('user_id')
        if target_user_id and target_user_id != request.user.id:
            if not request.user.is_staff:
                return Response({
                    'error': '다른 사용자의 토큰을 무효화할 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            try:
                target_user = User.objects.get(id=target_user_id)
            except User.DoesNotExist:
                return Response({
                    'error': '대상 사용자를 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = request.user
        
        # 모든 토큰 무효화
        revoked_count = TokenManager.revoke_user_tokens(target_user)
        
        logger.info(f"토큰 무효화 완료: 사용자 {target_user.username} ({revoked_count}개)")
        
        return Response({
            'message': f'사용자 {target_user.username}의 토큰 {revoked_count}개가 무효화되었습니다.',
            'revoked_count': revoked_count,
        })
        
    except Exception as e:
        logger.error(f"토큰 무효화 실패: {e}")
        return Response({
            'error': '토큰 무효화 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
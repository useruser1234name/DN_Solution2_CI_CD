# -*- coding: utf-8 -*-
"""
Cached Views for Companies App - DN_SOLUTION2 리모델링
캐시가 적용된 회사 관리 뷰들
"""

import logging
import json
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Company, CompanyUser
from .serializers import CompanySerializer, CompanyUserSerializer
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.http import JsonResponse
from .utils import get_visible_companies, get_visible_users

# 캐시 관련 import
from dn_solution.cache_manager import cached_api_response, cache_manager, CacheManager
from dn_solution.cache_utils import (
    cache_user_data, cache_company_hierarchy, 
    CacheUtils, invalidate_on_save
)

logger = logging.getLogger('companies')


class CachedCompanyViewSet(viewsets.ModelViewSet):
    """캐시가 적용된 회사 ViewSet"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """캐시된 회사 목록 반환"""
        user = self.request.user
        cache_key = f"company_list:user_{user.id if user.is_authenticated else 'anon'}"
        
        # 캐시에서 조회
        cached_companies = cache_manager.get(cache_key)
        if cached_companies is not None:
            logger.debug(f"회사 목록 캐시 HIT: {cache_key}")
            # 캐시된 데이터를 QuerySet으로 변환 (또는 직접 사용)
            company_ids = [c['id'] for c in cached_companies]
            return Company.objects.filter(id__in=company_ids)
        
        # 캐시 미스 - DB에서 조회
        companies = get_visible_companies(user)
        
        # 캐시에 저장
        companies_data = CacheUtils.serialize_for_cache(companies)
        cache_manager.set(cache_key, companies_data, CacheManager.CACHE_TIMEOUTS['medium'])
        logger.debug(f"회사 목록 캐시 SET: {cache_key}")
        
        return companies

    @cached_api_response(timeout=CacheManager.CACHE_TIMEOUTS['medium'], key_prefix='company_detail')
    def retrieve(self, request, *args, **kwargs):
        """회사 상세 조회 (캐시 적용)"""
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """회사 생성 후 관련 캐시 무효화"""
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            # 관련 캐시 무효화
            cache_manager.delete_pattern('company_list:*')
            cache_manager.delete_pattern('company_hierarchy:*')
            logger.info("회사 생성 후 캐시 무효화 완료")
        
        return response

    def update(self, request, *args, **kwargs):
        """회사 업데이트 후 관련 캐시 무효화"""
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK:
            company_id = kwargs.get('pk')
            # 특정 회사 및 관련 캐시 무효화
            cache_manager.delete_pattern(f'company_detail:*:{company_id}')
            cache_manager.delete_pattern('company_list:*')
            cache_manager.delete_pattern(f'company_hierarchy:{company_id}')
            cache_manager.delete_pattern('api:*companies*')
            logger.info(f"회사 {company_id} 업데이트 후 캐시 무효화 완료")
        
        return response


class CachedCompanyUserViewSet(viewsets.ModelViewSet):
    """캐시가 적용된 회사 사용자 ViewSet"""
    queryset = CompanyUser.objects.all()
    serializer_class = CompanyUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """캐시된 사용자 목록 반환"""
        user = self.request.user
        cache_key = f"company_users:user_{user.id}"
        
        # 캐시에서 조회
        cached_users = cache_manager.get(cache_key)
        if cached_users is not None:
            logger.debug(f"사용자 목록 캐시 HIT: {cache_key}")
            user_ids = [u['id'] for u in cached_users]
            return CompanyUser.objects.filter(id__in=user_ids)
        
        # 캐시 미스 - DB에서 조회
        users = get_visible_users(user)
        
        # 캐시에 저장
        users_data = CacheUtils.serialize_for_cache(users)
        cache_manager.set(cache_key, users_data, CacheManager.CACHE_TIMEOUTS['medium'])
        logger.debug(f"사용자 목록 캐시 SET: {cache_key}")
        
        return users

    def create(self, request, *args, **kwargs):
        """사용자 생성 후 관련 캐시 무효화"""
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            # 사용자 관련 캐시 무효화
            cache_manager.delete_pattern('company_users:*')
            cache_manager.delete_pattern('user:*')
            cache_manager.delete_pattern('user_permissions:*')
            logger.info("사용자 생성 후 캐시 무효화 완료")
        
        return response


class CachedUserApprovalView(APIView):
    """캐시가 적용된 사용자 승인 뷰"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """사용자 승인/거부 API - 캐시 무효화 포함"""
        approver_user = request.user
        action = request.data.get('action')

        try:
            target_user = CompanyUser.objects.get(id=user_id)
            
            # 권한 확인 (기존 로직)
            if not self._can_approve_user(approver_user, target_user):
                return Response({
                    'error': '해당 사용자를 승인할 권한이 없습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 승인/거부 처리
            if action == 'approve':
                target_user.status = 'approved'
                target_user.is_approved = True
                target_user.approved_by = approver_user.companyuser
                target_user.approved_at = timezone.now()
                message = f'{target_user.username}님이 승인되었습니다.'
            elif action == 'reject':
                target_user.status = 'rejected'
                target_user.is_approved = False
                message = f'{target_user.username}님이 거부되었습니다.'
            else:
                return Response({
                    'error': 'action은 approve 또는 reject만 가능합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            target_user.save()
            
            # 관련 캐시 무효화
            self._invalidate_user_cache(target_user)
            
            logger.info(f"사용자 승인/거부: {message} (승인자: {approver_user.username})")
            
            return Response({
                'message': message,
                'user_status': target_user.status
            })
            
        except CompanyUser.DoesNotExist:
            return Response({
                'error': '사용자를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"사용자 승인 처리 중 오류: {e}")
            return Response({
                'error': '처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _can_approve_user(self, approver, target_user):
        """승인 권한 확인 (기존 로직)"""
        # 실제 권한 로직 구현 필요
        return True
    
    def _invalidate_user_cache(self, target_user):
        """사용자 관련 캐시 무효화"""
        patterns = [
            f'user:{target_user.django_user.id}:*',
            f'user_permissions:{target_user.django_user.id}',
            'company_users:*',
            f'company_hierarchy:{target_user.company.id}',
            'api:*users*',
        ]
        
        for pattern in patterns:
            count = cache_manager.delete_pattern(pattern)
            if count > 0:
                logger.debug(f"캐시 무효화: {pattern} ({count}개)")


class CachedDashboardStatsView(APIView):
    """캐시가 적용된 대시보드 통계 뷰"""
    permission_classes = [IsAuthenticated]

    @cached_api_response(timeout=CacheManager.CACHE_TIMEOUTS['short'], key_prefix='dashboard_stats')
    def get(self, request):
        """대시보드 통계 데이터 (캐시 적용)"""
        user = request.user
        
        try:
            # 사용자가 볼 수 있는 회사들
            visible_companies = get_visible_companies(user)
            
            # 통계 계산
            stats = {
                'total_companies': visible_companies.count(),
                'active_companies': visible_companies.filter(status=True).count(),
                'total_users': get_visible_users(user).count(),
                'pending_approvals': get_visible_users(user).filter(status='pending').count(),
                'timestamp': timezone.now().isoformat(),
            }
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"대시보드 통계 조회 실패: {e}")
            return Response({
                'error': '통계 데이터 조회에 실패했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CachedDashboardActivitiesView(APIView):
    """캐시가 적용된 대시보드 활동 뷰"""
    permission_classes = [IsAuthenticated]

    @cached_api_response(timeout=CacheManager.CACHE_TIMEOUTS['short'], key_prefix='dashboard_activities')
    def get(self, request):
        """최근 활동 내역 (캐시 적용)"""
        user = request.user
        
        try:
            # 최근 생성된 회사들
            recent_companies = get_visible_companies(user).filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-created_at')[:5]
            
            # 최근 사용자 등록
            recent_users = get_visible_users(user).filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-created_at')[:5]
            
            activities = {
                'recent_companies': [
                    {
                        'id': company.id,
                        'name': company.name,
                        'type': company.type,
                        'created_at': company.created_at.isoformat(),
                    }
                    for company in recent_companies
                ],
                'recent_users': [
                    {
                        'id': user.id,
                        'username': user.username,
                        'company': user.company.name,
                        'status': user.status,
                        'created_at': user.created_at.isoformat(),
                    }
                    for user in recent_users
                ],
                'timestamp': timezone.now().isoformat(),
            }
            
            return Response(activities)
            
        except Exception as e:
            logger.error(f"활동 내역 조회 실패: {e}")
            return Response({
                'error': '활동 내역 조회에 실패했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 유틸리티 함수들 (캐시 적용)
def get_cached_company_hierarchy(company_id):
    """회사 계층 구조 캐시 조회"""
    return cache_company_hierarchy(company_id)


def get_cached_user_permissions(user_id):
    """사용자 권한 정보 캐시 조회"""
    return cache_user_data(user_id, data_type='permissions')


# 캐시 워밍업 함수
def warm_up_companies_cache():
    """회사 관련 캐시 워밍업"""
    try:
        # 활성 회사들 캐시
        active_companies = Company.objects.filter(status=True)[:50]
        for company in active_companies:
            cache_key = f"company_detail:{company.id}"
            company_data = CacheUtils.serialize_for_cache(company)
            cache_manager.set(cache_key, company_data, CacheManager.CACHE_TIMEOUTS['long'])
        
        # 회사 계층 구조 캐시
        for company in active_companies:
            cache_company_hierarchy(company.id)
        
        logger.info(f"회사 캐시 워밍업 완료: {len(active_companies)}개")
        return len(active_companies)
        
    except Exception as e:
        logger.error(f"회사 캐시 워밍업 실패: {e}")
        return 0


def warm_up_users_cache():
    """사용자 관련 캐시 워밍업"""
    try:
        # 활성 사용자들 캐시
        active_users = User.objects.filter(is_active=True)[:100]
        for user in active_users:
            cache_user_data(user.id, data_type='profile')
            cache_user_data(user.id, data_type='permissions')
        
        logger.info(f"사용자 캐시 워밍업 완료: {len(active_users)}개")
        return len(active_users)
        
    except Exception as e:
        logger.error(f"사용자 캐시 워밍업 실패: {e}")
        return 0
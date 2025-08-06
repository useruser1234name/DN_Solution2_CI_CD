from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
import json
import logging
from functools import wraps
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Policy, PolicyNotice, PolicyAssignment
from .serializers import PolicySerializer, PolicyNoticeSerializer
from companies.models import Company

logger = logging.getLogger('policies')

def simple_auth_required(view_func):
    """
    간단한 인증 데코레이터 (임시)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 임시로 인증을 건너뛰고 진행
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


from .utils import get_visible_policies

class PolicyListView(ListView):
    """
    정책 목록 조회 View
    """
    model = Policy
    template_name = 'policies/policy_list.html'
    context_object_name = 'policies'
    paginate_by = 20
    
    def get_queryset(self):
        """사용자 계층에 따라 필터링된 정책 목록을 반환합니다."""
        # 기본 쿼리셋을 계층 필터링된 결과로 설정
        queryset = get_visible_policies(self.request.user)
        queryset = queryset.select_related('created_by').prefetch_related('notices')
        
        
        # 검색 필터
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 신청서 타입 필터
        form_type = self.request.GET.get('form_type', '')
        if form_type:
            queryset = queryset.filter(form_type=form_type)
        
        # 통신사 필터
        carrier = self.request.GET.get('carrier', '')
        if carrier:
            queryset = queryset.filter(carrier=carrier)
        
        # 가입기간 필터
        contract_period = self.request.GET.get('contract_period', '')
        if contract_period:
            queryset = queryset.filter(contract_period=contract_period)
        
        # 노출 상태 필터
        expose = self.request.GET.get('expose', '')
        if expose in ['true', 'false']:
            queryset = queryset.filter(expose=(expose == 'true'))
        
        # 프리미엄 마켓 노출 필터
        premium_expose = self.request.GET.get('premium_expose', '')
        if premium_expose in ['true', 'false']:
            queryset = queryset.filter(premium_market_expose=(premium_expose == 'true'))
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """추가 컨텍스트 데이터"""
        context = super().get_context_data(**kwargs)
        
        # 필터 옵션들
        context['form_types'] = Policy.FORM_TYPE_CHOICES
        context['carriers'] = Policy.CARRIER_CHOICES
        context['contract_periods'] = Policy.CONTRACT_PERIOD_CHOICES
        
        # 현재 필터 상태
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'form_type': self.request.GET.get('form_type', ''),
            'carrier': self.request.GET.get('carrier', ''),
            'contract_period': self.request.GET.get('contract_period', ''),
            'expose': self.request.GET.get('expose', ''),
            'premium_expose': self.request.GET.get('premium_expose', ''),
        }
        
        # 사용자 업체 정보 (권한 제어용)
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(user=self.request.user)
            context['user_company'] = company_user.company
        except CompanyUser.DoesNotExist:
            context['user_company'] = None
        
        return context


class PolicyDetailView(LoginRequiredMixin, DetailView):
    """
    정책 상세 조회 View
    """
    model = Policy
    template_name = 'policies/policy_detail.html'
    context_object_name = 'policy'
    
    def get_context_data(self, **kwargs):
        """추가 컨텍스트 데이터"""
        context = super().get_context_data(**kwargs)
        
        # 정책 안내사항들
        context['notices'] = self.object.notices.order_by('order', '-is_important', '-created_at')
        
        # 배정된 업체들
        context['assignments'] = self.object.assignments.select_related('company').order_by('-assigned_at')
        
        return context


class PolicyCreateView(LoginRequiredMixin, CreateView):
    """
    정책 생성 View
    본사와 협력사만 정책 생성 가능
    """
    model = Policy
    template_name = 'policies/policy_form.html'
    fields = [
        'title', 'description', 'form_type', 'carrier', 'contract_period',
        'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose'
    ]
    success_url = reverse_lazy('policies:policy_list')
    
    def dispatch(self, request, *args, **kwargs):
        """권한 검증: 본사와 협력사만 정책 생성 가능"""
        # 슈퍼유저는 모든 권한
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # CompanyUser 권한 확인
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            # 본사(headquarters) 또는 협력사(agency)만 정책 생성 가능
            if company.type not in ['headquarters', 'agency']:
                messages.error(request, '정책 생성 권한이 없습니다. 본사와 협력사만 정책을 생성할 수 있습니다.')
                return redirect('policies:policy_list')
                
        except CompanyUser.DoesNotExist:
            messages.error(request, '업체 정보를 찾을 수 없습니다.')
            return redirect('policies:policy_list')
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """폼 유효성 검증 및 저장"""
        form.instance.created_by = self.request.user
        
        # 정책 생성 로깅
        logger.info(f"새 정책 생성 시도: {form.instance.title} - 생성자: {self.request.user.username}")
        
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'정책 "{form.instance.title}"이 성공적으로 생성되었습니다.')
            logger.info(f"정책 생성 완료: {form.instance.title} (ID: {form.instance.id})")
            return response
        except Exception as e:
            logger.error(f"정책 생성 실패: {str(e)} - {form.instance.title}")
            messages.error(self.request, '정책 생성 중 오류가 발생했습니다.')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        """추가 컨텍스트 데이터"""
        context = super().get_context_data(**kwargs)
        
        # 필터 옵션들
        context['form_types'] = Policy.FORM_TYPE_CHOICES
        context['carriers'] = Policy.CARRIER_CHOICES
        context['contract_periods'] = Policy.CONTRACT_PERIOD_CHOICES
        
        # 현재 사용자의 업체 정보
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(user=self.request.user)
            context['user_company'] = company_user.company
        except CompanyUser.DoesNotExist:
            context['user_company'] = None
        
        return context


class PolicyUpdateView(LoginRequiredMixin, UpdateView):
    """
    정책 수정 View
    """
    model = Policy
    template_name = 'policies/policy_form.html'
    fields = [
        'title', 'description', 'form_type', 'carrier', 'contract_period',
        'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose'
    ]
    
    def get_success_url(self):
        return reverse_lazy('policies:policy_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """폼 유효성 검증 성공 시 처리"""
        response = super().form_valid(form)
        
        messages.success(self.request, f'정책 "{self.object.title}"이 성공적으로 수정되었습니다.')
        logger.info(f"정책 수정: {self.object.title} (사용자: {self.request.user.username})")
        
        return response
    
    def get_context_data(self, **kwargs):
        """추가 컨텍스트 데이터"""
        context = super().get_context_data(**kwargs)
        context['form_types'] = Policy.FORM_TYPE_CHOICES
        context['carriers'] = Policy.CARRIER_CHOICES
        context['contract_periods'] = Policy.CONTRACT_PERIOD_CHOICES
        context['is_create'] = False
        return context


class PolicyDeleteView(LoginRequiredMixin, DeleteView):
    """
    정책 삭제 View
    """
    model = Policy
    template_name = 'policies/policy_confirm_delete.html'
    success_url = reverse_lazy('policies:policy_list')
    
    def delete(self, request, *args, **kwargs):
        """삭제 처리"""
        policy = self.get_object()
        title = policy.title
        
        response = super().delete(request, *args, **kwargs)
        
        messages.success(request, f'정책 "{title}"이 성공적으로 삭제되었습니다.')
        logger.info(f"정책 삭제: {title} (사용자: {request.user.username})")
        
        return response


@login_required
@require_http_methods(["POST"])
def toggle_policy_expose(request, pk):
    """
    정책 노출 상태 토글 API
    """
    try:
        policy = get_object_or_404(Policy, pk=pk)
        success = policy.toggle_expose()
        
        if success:
            return JsonResponse({
                'success': True,
                'expose': policy.expose,
                'message': f'정책 노출 상태가 {"노출" if policy.expose else "비노출"}로 변경되었습니다.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '정책 노출 상태 변경에 실패했습니다.'
            })
    
    except Exception as e:
        logger.error(f"정책 노출 상태 토글 실패: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '오류가 발생했습니다.'
        })


@login_required
@require_http_methods(["POST"])
def toggle_premium_market_expose(request, pk):
    """
    프리미엄 마켓 노출 상태 토글 API
    """
    try:
        policy = get_object_or_404(Policy, pk=pk)
        success = policy.toggle_premium_market_expose()
        
        if success:
            return JsonResponse({
                'success': True,
                'premium_expose': policy.premium_market_expose,
                'message': f'프리미엄 마켓 노출 상태가 {"노출" if policy.premium_market_expose else "비노출"}로 변경되었습니다.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '프리미엄 마켓 노출 상태 변경에 실패했습니다.'
            })
    
    except Exception as e:
        logger.error(f"프리미엄 마켓 노출 상태 토글 실패: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '오류가 발생했습니다.'
        })


@login_required
@require_http_methods(["POST"])
def regenerate_html(request, pk):
    """
    HTML 내용 재생성 API
    """
    try:
        policy = get_object_or_404(Policy, pk=pk)
        policy.generate_html_content()
        policy.save()
        
        return JsonResponse({
            'success': True,
            'message': 'HTML 내용이 성공적으로 재생성되었습니다.'
        })
    
    except Exception as e:
        logger.error(f"HTML 재생성 실패: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'HTML 재생성에 실패했습니다.'
        })


@login_required
def policy_notice_list(request, policy_pk):
    """
    정책별 안내사항 목록
    """
    policy = get_object_or_404(Policy, pk=policy_pk)
    notices = policy.notices.order_by('order', '-is_important', '-created_at')
    
    return render(request, 'policies/notice_list.html', {
        'policy': policy,
        'notices': notices
    })


@login_required
def policy_assignment_list(request, policy_pk):
    """
    정책별 배정 업체 목록
    """
    policy = get_object_or_404(Policy, pk=policy_pk)
    assignments = policy.assignments.select_related('company').order_by('-assigned_at')
    
    return render(request, 'policies/assignment_list.html', {
        'policy': policy,
        'assignments': assignments
    })


@login_required
@require_http_methods(["GET", "POST"])
def policy_deploy(request, pk):
    """
    정책 배포 뷰
    선택한 하위 업체들에 정책을 배포
    """
    policy = get_object_or_404(Policy, pk=pk)
    
    # 권한 확인: 본사와 협력사만 배포 가능
    if not request.user.is_superuser:
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            if company.type not in ['headquarters', 'agency']:
                messages.error(request, '정책 배포 권한이 없습니다.')
                return redirect('policies:policy_list')
                
        except CompanyUser.DoesNotExist:
            messages.error(request, '업체 정보를 찾을 수 없습니다.')
            return redirect('policies:policy_list')
    
    if request.method == 'POST':
        # 배포 처리
        company_ids = request.POST.getlist('companies')
        custom_rebate = request.POST.get('custom_rebate')
        expose_to_child = request.POST.get('expose_to_child') == 'on'
        
        if company_ids:
            try:
                # 커스텀 리베이트 처리
                if custom_rebate:
                    custom_rebate = float(custom_rebate)
                else:
                    custom_rebate = None
                
                # 선택된 업체들에 배정
                assignments = policy.assign_to_selected_companies(
                    company_ids, 
                    custom_rebate, 
                    expose_to_child
                )
                
                messages.success(request, f'정책이 {len(assignments)}개 업체에 성공적으로 배포되었습니다.')
                logger.info(f"정책 배포 완료: {policy.title} → {len(assignments)}개 업체")
                
            except ValueError:
                messages.error(request, '리베이트 금액이 올바르지 않습니다.')
            except Exception as e:
                messages.error(request, f'정책 배포 중 오류가 발생했습니다: {str(e)}')
                logger.error(f"정책 배포 실패: {str(e)} - {policy.title}")
        else:
            messages.warning(request, '배포할 업체를 선택해주세요.')
    
    # 배포 가능한 업체 목록 조회
    try:
        from companies.models import CompanyUser, Company
        company_user = CompanyUser.objects.get(django_user=request.user)
        user_company = company_user.company
        
        if request.user.is_superuser or user_company.type == 'headquarters':
            # 본사: 모든 업체 표시
            available_companies = Company.objects.filter(status=True).exclude(type='headquarters')
        elif user_company.type == 'agency':
            # 협력사: 자신의 하위 업체들만 표시
            available_companies = Company.objects.filter(
                parent_company=user_company,
                status=True
            )
        else:
            available_companies = Company.objects.none()
            
    except CompanyUser.DoesNotExist:
        available_companies = Company.objects.none()
    
    # 이미 배정된 업체들
    assigned_companies = policy.get_assigned_companies()
    
    context = {
        'policy': policy,
        'available_companies': available_companies,
        'assigned_companies': assigned_companies,
        'user_company': getattr(company_user, 'company', None) if 'company_user' in locals() else None,
    }
    
    return render(request, 'policies/policy_deploy.html', context)


@login_required
@require_http_methods(["POST"])
def policy_bulk_deploy(request, pk):
    """
    정책 일괄 배포 API
    AJAX 요청으로 처리
    """
    policy = get_object_or_404(Policy, pk=pk)
    
    try:
        data = json.loads(request.body)
        company_ids = data.get('company_ids', [])
        custom_rebate = data.get('custom_rebate')
        expose_to_child = data.get('expose_to_child', True)
        
        if not company_ids:
            return JsonResponse({'success': False, 'message': '배포할 업체를 선택해주세요.'})
        
        # 커스텀 리베이트 처리
        if custom_rebate:
            custom_rebate = float(custom_rebate)
        
        # 배정 처리
        assignments = policy.assign_to_selected_companies(
            company_ids, 
            custom_rebate, 
            expose_to_child
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'{len(assignments)}개 업체에 성공적으로 배포되었습니다.',
            'deployed_count': len(assignments)
        })
        
    except ValueError:
        return JsonResponse({'success': False, 'message': '리베이트 금액이 올바르지 않습니다.'})
    except Exception as e:
        logger.error(f"정책 일괄 배포 실패: {str(e)} - {policy.title}")
        return JsonResponse({'success': False, 'message': f'배포 중 오류가 발생했습니다: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def policy_bulk_remove(request, pk):
    """
    정책 일괄 제거 API
    AJAX 요청으로 처리
    """
    policy = get_object_or_404(Policy, pk=pk)
    
    try:
        data = json.loads(request.body)
        company_ids = data.get('company_ids', [])
        
        if not company_ids:
            return JsonResponse({'success': False, 'message': '제거할 업체를 선택해주세요.'})
        
        # 제거 처리
        companies = Company.objects.filter(id__in=company_ids)
        removed_count = policy.remove_from_companies(companies)
        
        return JsonResponse({
            'success': True, 
            'message': f'{removed_count}개 업체에서 성공적으로 제거되었습니다.',
            'removed_count': removed_count
        })
        
    except Exception as e:
        logger.error(f"정책 일괄 제거 실패: {str(e)} - {policy.title}")
        return JsonResponse({'success': False, 'message': f'제거 중 오류가 발생했습니다: {str(e)}'})


@login_required
def get_available_companies(request):
    """
    배포 가능한 업체 목록 조회 API
    AJAX 요청으로 처리
    """
    try:
        from companies.models import CompanyUser, Company
        
        if request.user.is_superuser:
            # 슈퍼유저: 모든 업체
            companies = Company.objects.filter(status=True).exclude(type='headquarters')
        else:
            company_user = CompanyUser.objects.get(user=request.user)
            user_company = company_user.company
            
            if user_company.type == 'headquarters':
                # 본사: 모든 업체
                companies = Company.objects.filter(status=True).exclude(type='headquarters')
            elif user_company.type == 'agency':
                # 협력사: 자신의 하위 업체들
                companies = Company.objects.filter(
                    parent_company=user_company,
                    status=True
                )
            else:
                companies = Company.objects.none()
        
        company_data = [{
            'id': str(company.id),
            'name': company.name,
            'type': company.type,
            'type_display': company.get_type_display()
        } for company in companies]
        
        return JsonResponse({'success': True, 'companies': company_data})
        
    except CompanyUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': '업체 정보를 찾을 수 없습니다.'})
    except Exception as e:
        logger.error(f"배포 가능 업체 목록 조회 실패: {str(e)}")
        return JsonResponse({'success': False, 'message': f'업체 목록 조회 중 오류가 발생했습니다: {str(e)}'})


class PolicyApiCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            title = data.get('title', '').strip()
            if not title:
                return Response({'success': False, 'message': '정책명은 필수입니다.'}, status=status.HTTP_400_BAD_REQUEST)

            # 본사와 협력사만 정책 생성 가능
            from companies.models import CompanyUser, Company
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                company = company_user.company
                if company.type not in ['headquarters', 'agency']:
                    return Response({'success': False, 'message': '정책 생성 권한이 없습니다. 본사와 협력사만 정책을 생성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
            except CompanyUser.DoesNotExist:
                return Response({'success': False, 'message': '업체 정보를 찾을 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            from decimal import Decimal
            policy = Policy(
                title=title,
                description=data.get('description', ''),
                form_type=data.get('form_type', 'general'),
                carrier=data.get('carrier', 'skt'),
                contract_period=data.get('contract_period', '24'),
                rebate_agency=Decimal(str(data.get('rebate_agency', 0))),
                rebate_retail=Decimal(str(data.get('rebate_retail', 0))),
                expose=bool(data.get('expose', True)),
                premium_market_expose=bool(data.get('premium_market_expose', False)),
                created_by=request.user,
                html_content=''
            )
            policy.save(skip_html_generation=True)

            # 자식 회사에 할당 (assigned_to 파라미터가 있는 경우)
            assigned_to = data.get('assigned_to')
            if assigned_to:
                try:
                    target_company = Company.objects.get(id=assigned_to)
                    # 해당 회사가 현재 사용자의 자식 회사인지 확인
                    if target_company.parent_company == company:
                        from .models import PolicyAssignment
                        PolicyAssignment.objects.create(
                            policy=policy,
                            company=target_company,
                            expose_to_child=True
                        )
                        logger.info(f"정책 '{policy.title}'을 {target_company.name}에 할당했습니다.")
                    else:
                        logger.warning(f"권한 없는 회사에 정책 할당 시도: {target_company.name}")
                except Company.DoesNotExist:
                    logger.warning(f"존재하지 않는 회사에 정책 할당 시도: {assigned_to}")

            logger.info(f"새 정책 생성: {policy.title}")

            return Response({
                'success': True,
                'message': '정책이 성공적으로 생성되었습니다.',
                'policy': {
                    'id': str(policy.id),
                    'title': policy.title,
                    'description': policy.description,
                    'form_type': policy.form_type,
                    'carrier': policy.carrier,
                    'contract_period': policy.contract_period,
                    'rebate_agency': float(policy.rebate_agency),
                    'rebate_retail': float(policy.rebate_retail),
                    'expose': policy.expose,
                    'premium_market_expose': policy.premium_market_expose,
                    'created_at': policy.created_at.isoformat() if policy.created_at else None,
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"정책 API 생성 실패: {str(e)}")
            import traceback
            logger.error(f"정책 API 생성 실패 상세: {traceback.format_exc()}")
            return Response({'success': False, 'message': f'정책 생성에 실패했습니다: {str(e)}', 'error_details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 기존 함수형 뷰는 제거 또는 주석 처리
# @csrf_exempt
def policy_api_create(request):
    return Response({'success': False, 'message': '이 API는 더 이상 사용되지 않습니다. (DRF APIView로 대체됨)'}, status=405)


@csrf_exempt
def policy_api_list(request):
    """
    정책 목록 API (AJAX)
    - received_policies: 상위에서 받은 정책(기존 get_visible_policies)
    - assigned_policies: 내가 하위에 할당한 정책(내 회사가 parent_company인 하위 업체에 배정된 정책)
    """
    if request.method == 'GET':
        try:
            from .utils import get_received_policies, get_assigned_policies
            user = request.user
            # 1. 상위에서 받은 정책
            received_policies = get_received_policies(user)

            # 2. 내가 하위에 할당한 정책
            assigned_policies = get_assigned_policies(user)

            # 필터링(공통)
            def apply_filters(qs):
                form_type = request.GET.get('form_type')
                if form_type:
                    qs = qs.filter(form_type=form_type)
                carrier = request.GET.get('carrier')
                if carrier:
                    qs = qs.filter(carrier=carrier)
                contract_period = request.GET.get('contract_period')
                if contract_period:
                    qs = qs.filter(contract_period=contract_period)
                expose = request.GET.get('expose')
                if expose in ['true', 'false']:
                    qs = qs.filter(expose=(expose == 'true'))
                search = request.GET.get('search', '')
                if search:
                    qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
                return qs

            received_policies = apply_filters(received_policies)
            assigned_policies = apply_filters(assigned_policies)

            # 페이지네이션(각각)
            page = int(request.GET.get('page', 1))
            paginator1 = Paginator(received_policies, 20)
            received_page = paginator1.get_page(page)
            paginator2 = Paginator(assigned_policies, 20)
            assigned_page = paginator2.get_page(page)

            serializer1 = PolicySerializer(received_page, many=True)
            serializer2 = PolicySerializer(assigned_page, many=True)

            return JsonResponse({
                'success': True,
                'received_policies': serializer1.data,
                'assigned_policies': serializer2.data,
                'received_total_pages': paginator1.num_pages,
                'assigned_total_pages': paginator2.num_pages,
                'current_page': page,
                'received_total_count': paginator1.count,
                'assigned_total_count': paginator2.count
            })
        except Exception as e:
            logger.error(f"정책 API 목록 조회 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '정책 목록 조회에 실패했습니다.'
            })
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@login_required
def check_duplicate_policy(request):
    """
    정책 중복 체크 API
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', '').strip()
            policy_id = data.get('policy_id')  # 수정 시 기존 정책 ID
            
            if not title:
                return JsonResponse({
                    'success': False,
                    'message': '정책 제목을 입력해주세요.'
                })
            
            # 중복 체크
            existing_policies = Policy.objects.filter(title=title)
            if policy_id:
                existing_policies = existing_policies.exclude(id=policy_id)
            
            if existing_policies.exists():
                return JsonResponse({
                    'success': True,
                    'is_duplicate': True,
                    'message': '동일한 제목의 정책이 이미 존재합니다.'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'is_duplicate': False,
                    'message': '사용 가능한 제목입니다.'
                })
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 JSON 형식입니다.'
            })
        except Exception as e:
            logger.error(f"정책 중복 체크 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '중복 체크에 실패했습니다.'
            })
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@login_required
def policy_statistics(request):
    """
    정책 통계 정보
    """
    try:
        # 사용자 계층에 따라 볼 수 있는 정책만 필터링
        visible_policies = get_visible_policies(request.user)

        # 전체 정책 수
        total_policies = visible_policies.count()
        
        # 노출 중인 정책 수
        exposed_policies = visible_policies.filter(expose=True).count()
        
        # 프리미엄 마켓 노출 정책 수
        premium_policies = visible_policies.filter(premium_market_expose=True).count()
        
        # 신청서 타입별 정책 수
        form_type_stats = visible_policies.values('form_type').annotate(
            count=Count('id')
        ).order_by('form_type')
        
        # 통신사별 정책 수
        carrier_stats = visible_policies.values('carrier').annotate(
            count=Count('id')
        ).order_by('carrier')
        
        # 가입기간별 정책 수
        contract_stats = visible_policies.values('contract_period').annotate(
            count=Count('id')
        ).order_by('contract_period')
        
        # 배정된 정책 수
        assigned_policies = visible_policies.filter(assignments__isnull=False).distinct().count()
        
        context = {
            'total_policies': total_policies,
            'exposed_policies': exposed_policies,
            'premium_policies': premium_policies,
            'form_type_stats': form_type_stats,
            'carrier_stats': carrier_stats,
            'contract_stats': contract_stats,
            'assigned_policies': assigned_policies,
        }
        
        return render(request, 'policies/statistics.html', context)
    
    except Exception as e:
        logger.error(f"정책 통계 조회 실패: {str(e)}")
        messages.error(request, '통계 정보 조회에 실패했습니다.')
        return redirect('policies:policy_list')

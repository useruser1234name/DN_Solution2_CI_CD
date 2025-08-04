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


class PolicyListView(ListView):
    """
    정책 목록 조회 View
    """
    model = Policy
    template_name = 'policies/policy_list.html'
    context_object_name = 'policies'
    paginate_by = 20
    
    def get_queryset(self):
        """필터링 및 검색 기능"""
        queryset = Policy.objects.select_related('created_by').prefetch_related('notices')
        
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
    """
    model = Policy
    template_name = 'policies/policy_form.html'
    fields = [
        'title', 'description', 'form_type', 'carrier', 'contract_period',
        'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose'
    ]
    success_url = reverse_lazy('policies:policy_list')
    
    def form_valid(self, form):
        """폼 유효성 검증 성공 시 처리"""
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        messages.success(self.request, f'정책 "{self.object.title}"이 성공적으로 생성되었습니다.')
        logger.info(f"새 정책 생성: {self.object.title} (사용자: {self.request.user.username})")
        
        return response
    
    def get_context_data(self, **kwargs):
        """추가 컨텍스트 데이터"""
        context = super().get_context_data(**kwargs)
        context['form_types'] = Policy.FORM_TYPE_CHOICES
        context['carriers'] = Policy.CARRIER_CHOICES
        context['contract_periods'] = Policy.CONTRACT_PERIOD_CHOICES
        context['is_create'] = True
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


@csrf_exempt
def policy_api_create(request):
    """
    정책 생성 API (AJAX) - 테스트용 (인증 완전 제거)
    """
    # 인증 완전 제거 - 모든 요청 허용
    # Django 기본 인증 시스템 비활성화
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.auth import get_user_model
    
    # 인증 완전 우회
    request.user = AnonymousUser()
    
    # CSRF 검증 완전 비활성화
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 필수 필드 검증
            title = data.get('title', '').strip()
            if not title:
                return JsonResponse({
                    'success': False,
                    'message': '정책명은 필수입니다.'
                })
            
            # 정책 생성 (인증 완전 제거)
            policy = Policy.objects.create(
                title=title,
                description=data.get('description', ''),
                form_type=data.get('form_type', 'individual'),
                carrier=data.get('carrier', 'skt'),
                contract_period=data.get('contract_period', '24'),
                rebate_agency=data.get('rebate_agency', 0),
                rebate_retail=data.get('rebate_retail', 0),
                expose=data.get('expose', True),
                premium_market_expose=data.get('premium_market_expose', False),
                created_by=None,  # 인증 완전 제거
                html_content=''  # HTML 생성 건너뛰기
            )
            
            logger.info(f"새 정책 생성: {policy.title}")
            
            return JsonResponse({
                'success': True,
                'message': '정책이 성공적으로 생성되었습니다.',
                'policy': PolicySerializer(policy).data
            })
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 JSON 형식입니다.'
            })
        except Exception as e:
            logger.error(f"정책 API 생성 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'정책 생성에 실패했습니다: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@csrf_exempt
def policy_api_list(request):
    """
    정책 목록 API (AJAX)
    """
    if request.method == 'GET':
        try:
            policies = Policy.objects.all()
            
            # 필터링
            form_type = request.GET.get('form_type')
            if form_type:
                policies = policies.filter(form_type=form_type)
            
            carrier = request.GET.get('carrier')
            if carrier:
                policies = policies.filter(carrier=carrier)
            
            contract_period = request.GET.get('contract_period')
            if contract_period:
                policies = policies.filter(contract_period=contract_period)
            
            expose = request.GET.get('expose')
            if expose in ['true', 'false']:
                policies = policies.filter(expose=(expose == 'true'))
            
            # 검색
            search = request.GET.get('search', '')
            if search:
                policies = policies.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search)
                )
            
            # 페이지네이션
            page = request.GET.get('page', 1)
            paginator = Paginator(policies, 20)
            policies_page = paginator.get_page(page)
            
            serializer = PolicySerializer(policies_page, many=True)
            
            return JsonResponse({
                'success': True,
                'policies': serializer.data,
                'total_pages': paginator.num_pages,
                'current_page': int(page),
                'total_count': paginator.count
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
        # 전체 정책 수
        total_policies = Policy.objects.count()
        
        # 노출 중인 정책 수
        exposed_policies = Policy.objects.filter(expose=True).count()
        
        # 프리미엄 마켓 노출 정책 수
        premium_policies = Policy.objects.filter(premium_market_expose=True).count()
        
        # 신청서 타입별 정책 수
        form_type_stats = Policy.objects.values('form_type').annotate(
            count=Count('id')
        ).order_by('form_type')
        
        # 통신사별 정책 수
        carrier_stats = Policy.objects.values('carrier').annotate(
            count=Count('id')
        ).order_by('carrier')
        
        # 가입기간별 정책 수
        contract_stats = Policy.objects.values('contract_period').annotate(
            count=Count('id')
        ).order_by('contract_period')
        
        # 배정된 정책 수
        assigned_policies = Policy.objects.filter(assignments__isnull=False).distinct().count()
        
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

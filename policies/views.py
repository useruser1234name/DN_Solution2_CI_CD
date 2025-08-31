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
from django.views import View
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

from .models import (
    Policy, PolicyNotice, PolicyAssignment, CommissionMatrix,
    CarrierPlan, DeviceModel, DeviceColor
)
from .serializers import (
    PolicySerializer, PolicyNoticeSerializer, CarrierPlanSerializer,
    DeviceModelSerializer, DeviceColorSerializer, CommissionMatrixSerializer
)
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
from rest_framework import viewsets
from core.filters import PolicyFilter

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
        # N+1 쿼리 방지를 위한 최적화
        queryset = queryset.select_related('created_by').prefetch_related(
            'notices',
            'assignments',
            'assignments__company',
            'rebate_matrix'
        )
        
        
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
        if self.request.user.is_authenticated:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=self.request.user)
                context['user_company'] = company_user.company
            except CompanyUser.DoesNotExist:
                context['user_company'] = None
        else:
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
    본사만 정책 생성 가능
    """
    model = Policy
    template_name = 'policies/policy_form.html'
    fields = [
        'title', 'description', 'form_type', 'carrier', 'contract_period',
        'rebate_agency', 'rebate_retail', 'expose', 'premium_market_expose'
    ]
    success_url = reverse_lazy('policies:policy_list')
    
    def dispatch(self, request, *args, **kwargs):
        """권한 검증: 본사만 정책 생성 가능"""
        # 슈퍼유저는 모든 권한
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # CompanyUser 권한 확인
        try:
            from companies.models import CompanyUser
            company_user = CompanyUser.objects.get(django_user=request.user)
            company = company_user.company
            
            # 본사(headquarters)만 정책 생성 가능
            if company.type != 'headquarters':
                messages.error(request, '정책 생성 권한이 없습니다. 본사 관리자만 정책을 생성할 수 있습니다.')
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
            company_user = CompanyUser.objects.get(django_user=self.request.user)
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
    
    except Policy.DoesNotExist:
        logger.warning(f"정책을 찾을 수 없음: policy_id={policy_id}")
        return JsonResponse({
            'success': False,
            'message': '정책을 찾을 수 없습니다.'
        }, status=404)
    except ValidationError as e:
        logger.warning(f"정책 노출 상태 토글 유효성 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
    except DatabaseError as e:
        logger.error(f"정책 노출 상태 토글 DB 오류: {str(e)}", exc_info=True)
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
            company_user = CompanyUser.objects.get(django_user=request.user)
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

    def create_default_order_form(self, policy, user):
        """정책 생성 시 기본 주문서 양식 자동 생성"""
        try:
            from .utils.order_form_manager import OrderFormManager
            
            # OrderFormManager를 사용하여 주문서 양식 생성
            template = OrderFormManager.create_order_form(policy, user)
            
            logger.info(f"기본 주문서 양식 생성 완료: {policy.title}")
            return template
            
        except Exception as e:
            logger.error(f"기본 주문서 양식 생성 실패: {policy.title} - {str(e)}")

    def post(self, request):
        try:
            data = request.data
            title = data.get('title', '').strip()
            if not title:
                return Response({'success': False, 'message': '정책명은 필수입니다.'}, status=status.HTTP_400_BAD_REQUEST)

            # 본사만 정책 생성 가능
            from companies.models import CompanyUser, Company
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                company = company_user.company
                if company.type != 'headquarters':
                    return Response({'success': False, 'message': '정책 생성 권한이 없습니다. 본사 관리자만 정책을 생성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
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

                expose=True,  # 기본값으로 설정
                premium_market_expose=False,  # 기본값으로 설정
                is_active=data.get('is_active', True),
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

            # 기본 주문서 양식 자동 생성
            self.create_default_order_form(policy, request.user)

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
                    'is_active': policy.is_active,
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


class PolicyExposureView(LoginRequiredMixin, View):
    """
    정책 노출 관리 뷰
    본사가 협력사에 정책을 노출하는 것을 관리
    """
    
    def dispatch(self, request, *args, **kwargs):
        """권한 검증: 본사만 접근 가능"""
        if not request.user.is_superuser:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=request.user)
                if company_user.company.type != 'headquarters':
                    messages.error(request, '본사 관리자만 정책 노출을 관리할 수 있습니다.')
                    return redirect('policies:policy_list')
            except CompanyUser.DoesNotExist:
                messages.error(request, '업체 정보를 찾을 수 없습니다.')
                return redirect('policies:policy_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, policy_id):
        """협력사 선택 화면 표시"""
        from .models import Policy, PolicyExposure
        from companies.models import Company
        
        policy = get_object_or_404(Policy, id=policy_id)
        
        # 협력사 목록 조회
        agencies = Company.objects.filter(type='agency', status=True).order_by('name')
        
        # 이미 노출된 협력사 조회
        exposed_agencies = PolicyExposure.objects.filter(
            policy=policy, is_active=True
        ).values_list('agency_id', flat=True)
        
        context = {
            'policy': policy,
            'agencies': agencies,
            'exposed_agencies': list(exposed_agencies)
        }
        
        # AJAX 요청인 경우 JSON 응답
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            agencies_data = [{
                'id': str(agency.id),
                'name': agency.name,
                'code': agency.code,
                'is_exposed': str(agency.id) in exposed_agencies
            } for agency in agencies]
            
            return JsonResponse({
                'policy': {
                    'id': str(policy.id),
                    'title': policy.title
                },
                'agencies': agencies_data
            })
        
        return render(request, 'policies/policy_exposure.html', context)
    
    def post(self, request, policy_id):
        """선택된 협력사에 정책 노출"""
        from .models import Policy, PolicyExposure
        from companies.models import Company
        
        policy = get_object_or_404(Policy, id=policy_id)
        selected_agencies = request.POST.getlist('agencies')
        
        try:
            # 기존 노출 비활성화
            PolicyExposure.objects.filter(policy=policy).update(is_active=False)
            
            # 새로운 노출 생성
            for agency_id in selected_agencies:
                agency = Company.objects.get(id=agency_id, type='agency', status=True)
                PolicyExposure.objects.update_or_create(
                    policy=policy,
                    agency=agency,
                    defaults={
                        'is_active': True,
                        'exposed_by': request.user
                    }
                )
            
            messages.success(request, f'정책 "{policy.title}"이 선택된 협력사에 노출되었습니다.')
            logger.info(f"정책 노출 설정 완료: {policy.title} - {len(selected_agencies)}개 협력사")
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'정책이 {len(selected_agencies)}개 협력사에 노출되었습니다.'
                })
            
            return redirect('policies:policy_detail', pk=policy_id)
            
        except Exception as e:
            logger.error(f"정책 노출 설정 실패: {str(e)}")
            messages.error(request, '정책 노출 설정 중 오류가 발생했습니다.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            
            return redirect('policies:policy_detail', pk=policy_id)


class AgencyRebateView(LoginRequiredMixin, View):
    """
    협력사 리베이트 설정 뷰
    협력사가 판매점에 제공할 리베이트를 설정
    """
    
    def dispatch(self, request, *args, **kwargs):
        """권한 검증: 협력사만 접근 가능"""
        # 인증 확인
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': '인증이 필요합니다.'
            }, status=401)
        
        if not request.user.is_superuser:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=request.user)
                if company_user.company.type != 'agency':
                    return JsonResponse({
                        'success': False,
                        'error': '협력사 관리자만 리베이트를 설정할 수 있습니다.'
                    }, status=403)
            except CompanyUser.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': '업체 정보를 찾을 수 없습니다.'
                }, status=403)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """리베이트 설정 화면 표시"""
        from .models import PolicyExposure, AgencyRebate
        from companies.models import Company, CompanyUser
        
        try:
            company_user = CompanyUser.objects.get(django_user=request.user)
            agency = company_user.company
            
            # 노출된 정책 조회
            exposed_policies = PolicyExposure.objects.filter(
                agency=agency,
                is_active=True
            ).select_related('policy')
            
            # 판매점 목록 조회 (협력사 하위)
            retail_companies = Company.objects.filter(
                parent_company=agency,
                type='retail',
                status=True
            ).order_by('name')
            
            # 기존 리베이트 설정 조회
            existing_rebates = AgencyRebate.objects.filter(
                policy_exposure__agency=agency,
                is_active=True
            ).select_related('policy_exposure__policy', 'retail_company')
            
            context = {
                'exposed_policies': exposed_policies,
                'retail_companies': retail_companies,
                'existing_rebates': existing_rebates
            }
            
            return render(request, 'policies/agency_rebate.html', context)
            
        except CompanyUser.DoesNotExist:
            messages.error(request, '업체 정보를 찾을 수 없습니다.')
            return redirect('policies:policy_list')
    
    def post(self, request):
        """리베이트 설정 저장"""
        from .models import PolicyExposure, AgencyRebate
        from companies.models import Company, CompanyUser
        from decimal import Decimal
        
        try:
            company_user = CompanyUser.objects.get(django_user=request.user)
            agency = company_user.company
            
            policy_exposure_id = request.POST.get('policy_exposure')
            retail_company_id = request.POST.get('retail_company')
            rebate_amount = request.POST.get('rebate_amount')
            
            # 유효성 검증
            policy_exposure = get_object_or_404(
                PolicyExposure,
                id=policy_exposure_id,
                agency=agency,
                is_active=True
            )
            
            retail_company = get_object_or_404(
                Company,
                id=retail_company_id,
                parent_company=agency,
                type='retail',
                status=True
            )
            
            # 리베이트 설정 저장/수정
            rebate, created = AgencyRebate.objects.update_or_create(
                policy_exposure=policy_exposure,
                retail_company=retail_company,
                defaults={
                    'rebate_amount': Decimal(rebate_amount),
                    'is_active': True
                }
            )
            
            action = "설정" if created else "수정"
            messages.success(
                request,
                f'리베이트가 {action}되었습니다: {policy_exposure.policy.title} → {retail_company.name}: {rebate_amount}원'
            )
            logger.info(f"리베이트 {action}: {policy_exposure.policy.title} → {retail_company.name}: {rebate_amount}원")
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'리베이트가 {action}되었습니다.',
                    'rebate': {
                        'id': str(rebate.id),
                        'amount': float(rebate.rebate_amount),
                        'policy': policy_exposure.policy.title,
                        'retail': retail_company.name
                    }
                })
            
            return redirect('policies:agency_rebate')
            
        except Exception as e:
            logger.error(f"리베이트 설정 실패: {str(e)}")
            messages.error(request, '리베이트 설정 중 오류가 발생했습니다.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            
            return redirect('policies:agency_rebate')


class OrderFormBuilderView(LoginRequiredMixin, View):
    """
    주문서 양식 설계 뷰
    본사가 정책별 주문서 양식을 설계
    """
    
    def dispatch(self, request, *args, **kwargs):
        """권한 검증: 본사만 접근 가능"""
        if not request.user.is_superuser:
            try:
                from companies.models import CompanyUser
                company_user = CompanyUser.objects.get(django_user=request.user)
                if company_user.company.type != 'headquarters':
                    messages.error(request, '본사 관리자만 주문서 양식을 설계할 수 있습니다.')
                    return redirect('policies:policy_list')
            except CompanyUser.DoesNotExist:
                messages.error(request, '업체 정보를 찾을 수 없습니다.')
                return redirect('policies:policy_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, policy_id):
        """양식 설계 화면 표시"""
        from .models import Policy, OrderFormTemplate, OrderFormField
        
        policy = get_object_or_404(Policy, id=policy_id)
        
        # 기존 양식 조회
        try:
            template = OrderFormTemplate.objects.get(policy=policy)
            fields = template.fields.all().order_by('order')
        except OrderFormTemplate.DoesNotExist:
            template = None
            fields = []
        
        context = {
            'policy': policy,
            'template': template,
            'fields': fields,
            'field_types': OrderFormField.FIELD_TYPE_CHOICES
        }
        
        return render(request, 'policies/order_form_builder.html', context)
    
    def post(self, request, policy_id):
        """양식 저장"""
        from .models import Policy, OrderFormTemplate, OrderFormField
        
        policy = get_object_or_404(Policy, id=policy_id)
        
        try:
            # 기존 양식 삭제
            OrderFormTemplate.objects.filter(policy=policy).delete()
            
            # 새 양식 생성
            template = OrderFormTemplate.objects.create(
                policy=policy,
                title=request.POST.get('title', f'{policy.title} 주문서'),
                description=request.POST.get('description', ''),
                created_by=request.user
            )
            
            # 필드들 생성
            fields_data = request.POST.get('fields', '[]')
            fields = json.loads(fields_data)
            
            for i, field_data in enumerate(fields):
                OrderFormField.objects.create(
                    template=template,
                    field_name=field_data.get('name'),
                    field_label=field_data.get('label'),
                    field_type=field_data.get('type'),
                    is_required=field_data.get('required', False),
                    field_options=field_data.get('options'),
                    placeholder=field_data.get('placeholder', ''),
                    help_text=field_data.get('help_text', ''),
                    order=i
                )
            
            messages.success(request, '주문서 양식이 생성되었습니다.')
            logger.info(f"주문서 양식 생성: {policy.title}")
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': '주문서 양식이 생성되었습니다.',
                    'template_id': str(template.id)
                })
            
            return redirect('policies:policy_detail', pk=policy_id)
            
        except Exception as e:
            logger.error(f"주문서 양식 생성 실패: {str(e)}")
            messages.error(request, '주문서 양식 생성 중 오류가 발생했습니다.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=500)
            
            return redirect('policies:policy_detail', pk=policy_id)


# 구식 OrderFormTemplateView 제거됨 - PolicyFormTemplateView 사용


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rebate_summary(request):
    """리베이트 요약 정보 API"""
    from .models import PolicyExposure, AgencyRebate
    from companies.models import CompanyUser
    
    try:
        # 사용자 회사 정보 확인
        company_user = CompanyUser.objects.get(django_user=request.user)
        user_company = company_user.company
        
        rebate_data = []
        total_receivable = 0
        total_payable = 0
        participating_stores = 0
        
        if user_company.type == 'headquarters':
            # 본사: 협력사에 지급할 리베이트 현황
            exposures = PolicyExposure.objects.filter(
                policy__created_by=request.user,
                is_active=True
            ).select_related('policy', 'agency')
            
            for exposure in exposures:
                rebate_amount = exposure.policy.rebate_agency
                total_payable += rebate_amount
                rebate_data.append({
                    'policy_id': str(exposure.policy.id),
                    'policy_title': exposure.policy.title,
                    'company_name': exposure.agency.name,
                    'company_type': 'agency',
                    'rebate_amount': rebate_amount,
                    'rebate_type': '지급할 리베이트',
                    'status': 'active'
                })
        
        elif user_company.type == 'agency':
            # 협력사: 본사에서 받을 리베이트 + 판매점에게 줄 리베이트
            
            # 1. 본사에서 받을 리베이트
            exposures = PolicyExposure.objects.filter(
                agency=user_company,
                is_active=True
            ).select_related('policy')
            
            for exposure in exposures:
                rebate_amount = exposure.policy.rebate_agency
                total_receivable += rebate_amount
                rebate_data.append({
                    'policy_id': str(exposure.policy.id),
                    'policy_title': exposure.policy.title,
                    'company_name': '본사',
                    'company_type': 'headquarters',
                    'rebate_amount': rebate_amount,
                    'rebate_type': '받을 리베이트',
                    'status': 'active'
                })
            
            # 2. 판매점에게 줄 리베이트
            agency_rebates = AgencyRebate.objects.filter(
                policy_exposure__agency=user_company,
                is_active=True
            ).select_related('policy_exposure__policy', 'retail_company')
            
            for rebate in agency_rebates:
                total_payable += rebate.rebate_amount
                participating_stores += 1
                rebate_data.append({
                    'policy_id': str(rebate.policy_exposure.policy.id),
                    'policy_title': rebate.policy_exposure.policy.title,
                    'company_name': rebate.retail_company.name,
                    'company_type': 'retail',
                    'rebate_amount': rebate.rebate_amount,
                    'rebate_type': '지급할 리베이트',
                    'status': 'active'
                })
        
        elif user_company.type == 'retail':
            # 판매점: 협력사에서 받을 리베이트
            agency_rebates = AgencyRebate.objects.filter(
                retail_company=user_company,
                is_active=True
            ).select_related('policy_exposure__policy', 'policy_exposure__agency')
            
            for rebate in agency_rebates:
                total_receivable += rebate.rebate_amount
                rebate_data.append({
                    'policy_id': str(rebate.policy_exposure.policy.id),
                    'policy_title': rebate.policy_exposure.policy.title,
                    'company_name': rebate.policy_exposure.agency.name,
                    'company_type': 'agency',
                    'rebate_amount': rebate.rebate_amount,
                    'rebate_type': '받을 리베이트',
                    'status': 'active'
                })
        
        return Response({
            'success': True,
            'data': {
                'rebates': rebate_data,
                'summary': {
                    'total_receivable': total_receivable,
                    'total_payable': total_payable,
                    'participating_stores': participating_stores,
                    'total_policies': len(set(r['policy_id'] for r in rebate_data))
                }
            }
        })
        
    except CompanyUser.DoesNotExist:
        return Response({
            'success': False,
            'message': '업체 정보를 찾을 수 없습니다.'
        }, status=403)
    
    except Exception as e:
        logger.error(f"리베이트 요약 조회 실패: {str(e)}")
        return Response({
            'success': False,
            'message': '리베이트 정보를 불러오는 중 오류가 발생했습니다.'
        }, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def agency_rebate_api(request):
    """협력사 리베이트 관리 API"""
    from .models import PolicyExposure, AgencyRebate
    from companies.models import CompanyUser, Company
    from decimal import Decimal
    
    try:
        # 사용자 회사 정보 확인
        company_user = CompanyUser.objects.get(django_user=request.user)
        agency = company_user.company
        
        # 협력사만 접근 가능
        if agency.type != 'agency':
            return Response({
                'success': False,
                'message': '협력사만 접근할 수 있습니다.'
            }, status=403)
        
        if request.method == 'GET':
            # 협력사의 정책 노출 목록과 리베이트 설정 조회
            exposures = PolicyExposure.objects.filter(
                agency=agency,
                is_active=True
            ).select_related('policy').prefetch_related('rebates')
            
            data = []
            for exposure in exposures:
                # 해당 협력사의 하위 판매점 목록
                retail_stores = Company.objects.filter(
                    parent_company=agency,
                    type='retail',
                    status=True
                )
                
                rebate_settings = []
                for store in retail_stores:
                    try:
                        rebate = AgencyRebate.objects.get(
                            policy_exposure=exposure,
                            retail_company=store,
                            is_active=True
                        )
                        rebate_amount = rebate.rebate_amount
                    except AgencyRebate.DoesNotExist:
                        rebate_amount = None
                    
                    rebate_settings.append({
                        'store_id': str(store.id),
                        'store_name': store.name,
                        'rebate_amount': rebate_amount
                    })
                
                data.append({
                    'policy_id': str(exposure.policy.id),
                    'policy_title': exposure.policy.title,
                    'policy_exposure_id': str(exposure.id),
                    'default_rebate': exposure.policy.rebate_retail,
                    'retail_stores': rebate_settings
                })
            
            return Response({
                'success': True,
                'data': data
            })
        
        elif request.method == 'POST':
            # 리베이트 설정 저장
            import json
            data = json.loads(request.body)
            
            policy_exposure_id = data.get('policy_exposure_id')
            retail_company_id = data.get('retail_company_id')
            rebate_amount = data.get('rebate_amount')
            
            # 유효성 검증
            policy_exposure = get_object_or_404(
                PolicyExposure,
                id=policy_exposure_id,
                agency=agency,
                is_active=True
            )
            
            retail_company = get_object_or_404(
                Company,
                id=retail_company_id,
                parent_company=agency,
                type='retail',
                status=True
            )
            
            # 리베이트 설정 저장/수정
            rebate, created = AgencyRebate.objects.update_or_create(
                policy_exposure=policy_exposure,
                retail_company=retail_company,
                defaults={
                    'rebate_amount': Decimal(str(rebate_amount)),
                    'is_active': True
                }
            )
            
            action = "설정" if created else "수정"
            logger.info(f"리베이트 {action}: {policy_exposure.policy.title} → {retail_company.name}: {rebate_amount}원")
            
            return Response({
                'success': True,
                'message': f'리베이트가 {action}되었습니다.',
                'data': {
                    'rebate_id': str(rebate.id),
                    'rebate_amount': float(rebate.rebate_amount)
                }
            })
        
        else:
            return Response({
                'success': False,
                'message': '지원하지 않는 요청 방법입니다.'
            }, status=405)
        
    except CompanyUser.DoesNotExist:
        return Response({
            'success': False,
            'message': '업체 정보를 찾을 수 없습니다.'
        }, status=403)
    
    except Exception as e:
        logger.error(f"협력사 리베이트 API 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '요청 처리 중 오류가 발생했습니다.'
        }, status=500)


class CarrierPlanAPIView(APIView):
    """통신사 요금제 API"""
    
    def get(self, request):
        """통신사 요금제 목록 조회"""
        try:
            carrier = request.GET.get('carrier')
            is_active = request.GET.get('is_active', 'true').lower() == 'true'
            
            queryset = CarrierPlan.objects.all()
            
            if carrier:
                queryset = queryset.filter(carrier=carrier)
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            queryset = queryset.order_by('carrier', 'plan_price', 'plan_name')
            
            serializer = CarrierPlanSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        except Exception as e:
            logger.error(f"통신사 요금제 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '요금제 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request):
        """통신사 요금제 생성"""
        try:
            serializer = CarrierPlanSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'success': True,
                    'message': '요금제가 성공적으로 생성되었습니다.',
                    'data': serializer.data
                }, status=201)
            else:
                return Response({
                    'success': False,
                    'message': '입력 데이터가 올바르지 않습니다.',
                    'errors': serializer.errors
                }, status=400)
        
        except Exception as e:
            logger.error(f"통신사 요금제 생성 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '요금제 생성 중 오류가 발생했습니다.'
            }, status=500)


class DeviceModelAPIView(APIView):
    """기기 모델 API"""
    
    def get(self, request):
        """기기 모델 목록 조회"""
        try:
            is_active = request.GET.get('is_active', 'true').lower() == 'true'
            manufacturer = request.GET.get('manufacturer')
            
            queryset = DeviceModel.objects.all()
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            if manufacturer:
                queryset = queryset.filter(manufacturer__icontains=manufacturer)
            
            queryset = queryset.order_by('manufacturer', 'model_name')
            
            serializer = DeviceModelSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        except Exception as e:
            logger.error(f"기기 모델 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '기기 모델 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request):
        """기기 모델 생성"""
        try:
            serializer = DeviceModelSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(created_by=request.user)
                return Response({
                    'success': True,
                    'message': '기기 모델이 성공적으로 생성되었습니다.',
                    'data': serializer.data
                }, status=201)
            else:
                return Response({
                    'success': False,
                    'message': '입력 데이터가 올바르지 않습니다.',
                    'errors': serializer.errors
                }, status=400)
        
        except Exception as e:
            logger.error(f"기기 모델 생성 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '기기 모델 생성 중 오류가 발생했습니다.'
            }, status=500)


class DeviceColorAPIView(APIView):
    """기기 색상 API"""
    
    def get(self, request):
        """기기 색상 목록 조회"""
        try:
            device_model = request.GET.get('device_model')
            is_active = request.GET.get('is_active', 'true').lower() == 'true'
            
            queryset = DeviceColor.objects.all()
            
            if device_model:
                queryset = queryset.filter(device_model_id=device_model)
            
            if is_active:
                queryset = queryset.filter(is_active=True)
            
            queryset = queryset.order_by('device_model', 'color_name')
            
            serializer = DeviceColorSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        except Exception as e:
            logger.error(f"기기 색상 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '기기 색상 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request):
        """기기 색상 생성"""
        try:
            serializer = DeviceColorSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': '기기 색상이 성공적으로 생성되었습니다.',
                    'data': serializer.data
                }, status=201)
            else:
                return Response({
                    'success': False,
                    'message': '입력 데이터가 올바르지 않습니다.',
                    'errors': serializer.errors
                }, status=400)
        
        except Exception as e:
            logger.error(f"기기 색상 생성 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '기기 색상 생성 중 오류가 발생했습니다.'
            }, status=500)


class RebateCalculationAPIView(APIView):
    """리베이트 계산 API"""
    
    def get(self, request):
        """리베이트 계산"""
        try:
            policy_id = request.GET.get('policy_id')
            carrier = request.GET.get('carrier')
            plan_id = request.GET.get('plan_id')
            contract_period = request.GET.get('contract_period')
            sim_type = request.GET.get('sim_type')
            
            if not all([policy_id, carrier, plan_id, contract_period]):
                return Response({
                    'success': False,
                    'message': '필수 파라미터가 누락되었습니다.'
                }, status=400)
            
            # 정책 조회
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 요금제 조회
            plan = get_object_or_404(CarrierPlan, id=plan_id, carrier=carrier)
            
            # 리베이트 매트릭스에서 금액 조회
            rebate_amount = CommissionMatrix.get_commission_amount(
                policy=policy,
                carrier=carrier,
                plan_amount=plan.plan_price,
                contract_period=int(contract_period)
            )
            
            if rebate_amount is None:
                return Response({
                    'success': False,
                    'message': '해당 조건에 대한 리베이트 정보가 설정되지 않았습니다.'
                }, status=404)
            
            # 유심비 계산
            sim_cost = 0
            if sim_type == 'prepaid':
                sim_cost = 7700  # 선불: 본사에서 지급
            elif sim_type == 'postpaid':
                sim_cost = -7700  # 후불: 본사에서 차감
            
            # 업체 타입에 따른 리베이트 계산
            agency_rebate = float(rebate_amount) + sim_cost
            retail_rebate = float(policy.rebate_retail)  # 판매점 리베이트는 정책에서
            
            return Response({
                'success': True,
                'data': {
                    'policy_id': policy_id,
                    'policy_title': policy.title,
                    'carrier': carrier,
                    'plan_name': plan.plan_name,
                    'plan_price': plan.plan_price,
                    'contract_period': int(contract_period),
                    'sim_type': sim_type,
                    'sim_cost': sim_cost,
                    'agency_rebate': agency_rebate,
                    'retail_rebate': retail_rebate,
                    'base_rebate_amount': float(rebate_amount)
                }
            })
        
        except Exception as e:
            logger.error(f"리베이트 계산 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '리베이트 계산 중 오류가 발생했습니다.'
            }, status=500)


class PolicyFormTemplateView(APIView):
    """정책별 주문서 템플릿 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """정책의 주문서 템플릿 조회"""
        try:
            from .models import OrderFormTemplate
            from .form_builder import FormBuilder
            from companies.models import CompanyUser
            
            policy = get_object_or_404(Policy, id=policy_id)
            # 배정 컨텍스트 수집 (현재 사용자 기준)
            assignment_context = None
            try:
                company_user = CompanyUser.objects.select_related('company').get(django_user=request.user)
                assignment = policy.assignments.filter(company=company_user.company).first()
                assignment_context = {
                    'assigned': assignment is not None,
                    'assigned_to_name': assignment.assigned_to_name if assignment else None,
                    'custom_rebate': float(assignment.custom_rebate) if getattr(assignment, 'custom_rebate', None) is not None else None,
                    'expose_to_child': getattr(assignment, 'expose_to_child', None)
                }
            except CompanyUser.DoesNotExist:
                assignment_context = None
            
            # 주문서 템플릿 조회
            try:
                template = OrderFormTemplate.objects.get(policy=policy, is_active=True)
                fields = template.fields.all().order_by('order')
                # 비어있는 템플릿이면 최신 기본 필드로 업데이트
                if fields.count() == 0:
                    template = FormBuilder.update_template(template)
                    fields = template.fields.all().order_by('order')
                # 정상 경로: 기존 템플릿 직렬화 후 반환
                fields_data = []
                for field in fields:
                    fields_data.append({
                        'id': str(field.id),
                        'field_name': field.field_name,
                        'field_label': field.field_label,
                        'field_type': field.field_type,
                        'is_required': field.is_required,
                        'placeholder': field.placeholder,
                        'help_text': field.help_text,
                        'order': field.order,
                        'field_options': field.field_options or field.get_default_options(),
                        # 확장 메타
                        'is_readonly': getattr(field, 'is_readonly', False),
                        'is_masked': getattr(field, 'is_masked', False),
                        'auto_fill': getattr(field, 'auto_fill', ''),
                        'auto_generate': getattr(field, 'auto_generate', False),
                        'allow_manual': getattr(field, 'allow_manual', True),
                        'data_source': getattr(field, 'data_source', ''),
                        'rows': getattr(field, 'rows', 3),
                        'multiple': getattr(field, 'multiple', False),
                        'max_files': getattr(field, 'max_files', 4),
                        'accept': getattr(field, 'accept', 'image/*,.pdf,.doc,.docx'),
                    })
                return Response({
                    'success': True,
                    'data': {
                        'id': str(template.id),
                        'title': template.title,
                        'description': template.description,
                        'fields': fields_data,
                        'assignment_context': assignment_context
                    }
                })
            except OrderFormTemplate.DoesNotExist:
                logger.info(f"주문서 템플릿이 존재하지 않음: 정책 {policy.title}")
                # 정책에 최신 기본 템플릿 생성 후 반환
                template = FormBuilder.create_template(policy)
                fields = template.fields.all().order_by('order')
                fields_data = []
                for field in fields:
                    fields_data.append({
                        'id': str(field.id),
                        'field_name': field.field_name,
                        'field_label': field.field_label,
                        'field_type': field.field_type,
                        'is_required': field.is_required,
                        'placeholder': field.placeholder,
                        'help_text': field.help_text,
                        'order': field.order,
                        'field_options': field.field_options or field.get_default_options(),
                        # 확장 메타
                        'is_readonly': getattr(field, 'is_readonly', False),
                        'is_masked': getattr(field, 'is_masked', False),
                        'auto_fill': getattr(field, 'auto_fill', ''),
                        'auto_generate': getattr(field, 'auto_generate', False),
                        'allow_manual': getattr(field, 'allow_manual', True),
                        'data_source': getattr(field, 'data_source', ''),
                        'rows': getattr(field, 'rows', 3),
                        'multiple': getattr(field, 'multiple', False),
                        'max_files': getattr(field, 'max_files', 4),
                        'accept': getattr(field, 'accept', 'image/*,.pdf,.doc,.docx'),
                    })
                return Response({
                    'success': True,
                    'data': {
                        'id': str(template.id),
                        'title': template.title,
                        'description': template.description,
                        'fields': fields_data,
                        'assignment_context': assignment_context
                    }
                })
                
        except Exception as e:
            logger.error(f"주문서 템플릿 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '주문서 템플릿을 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request, policy_id):
        """주문서 템플릿 생성/수정"""
        try:
            from .models import OrderFormTemplate, OrderFormField
            
            policy = get_object_or_404(Policy, id=policy_id)
            data = request.data
            
            # 기존 템플릿 삭제 후 새로 생성
            OrderFormTemplate.objects.filter(policy=policy).delete()
            
            # 새 템플릿 생성
            template = OrderFormTemplate.objects.create(
                policy=policy,
                title=data.get('title', f'{policy.title} 주문서'),
                description=data.get('description', ''),
                created_by=request.user
            )
            
            # 필드들 생성
            fields_data = data.get('fields', [])
            logger.info(f"주문서 템플릿 저장: {template.title}, 필드 개수: {len(fields_data)}")
            
            for field_data in fields_data:
                field = OrderFormField.objects.create(
                    template=template,
                    field_name=field_data.get('field_name'),
                    field_label=field_data.get('field_label'),
                    field_type=field_data.get('field_type'),
                    is_required=field_data.get('is_required', False),
                    placeholder=field_data.get('placeholder', ''),
                    help_text=field_data.get('help_text', ''),
                    order=field_data.get('order', 0),
                    field_options=field_data.get('field_options'),
                    # 확장 메타 보존
                    is_readonly=field_data.get('is_readonly', False),
                    is_masked=field_data.get('is_masked', False),
                    auto_fill=field_data.get('auto_fill', ''),
                    auto_generate=field_data.get('auto_generate', False),
                    allow_manual=field_data.get('allow_manual', True),
                    data_source=field_data.get('data_source', ''),
                    rows=field_data.get('rows', 3),
                    multiple=field_data.get('multiple', False),
                    max_files=field_data.get('max_files', 4),
                    accept=field_data.get('accept', 'image/*,.pdf,.doc,.docx')
                )
                logger.info(f"  필드 생성: {field.field_label} ({field.field_type}) - ID: {field.id}")
            
            return Response({
                'success': True,
                'message': '주문서 템플릿이 저장되었습니다.',
                'data': {
                    'id': str(template.id),
                    'title': template.title
                }
            })
            
        except Exception as e:
            logger.error(f"주문서 템플릿 저장 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '주문서 템플릿 저장 중 오류가 발생했습니다.'
            }, status=500)


class PolicyRebateMatrixView(APIView):  # 이름은 유지하고 내부에서 CommissionMatrix 사용
    """정책별 리베이트 매트릭스 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """정책의 리베이트 매트릭스 조회"""
        try:
            from .models import CommissionMatrix
            
            logger.info(f"리베이트 매트릭스 조회 요청 - 정책 ID: {policy_id}")
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책 찾음: {policy.title}")
            
            # 해당 정책의 리베이트 매트릭스 조회
            matrix_queryset = CommissionMatrix.objects.filter(policy=policy).order_by('plan_range', 'contract_period')
            logger.info(f"리베이트 매트릭스 개수: {matrix_queryset.count()}")
            
            if not matrix_queryset.exists():
                # 매트릭스가 없으면 빈 매트릭스 반환 (기본 9x2 구조)
                logger.info("리베이트 매트릭스가 없음, 빈 매트릭스 반환")
                return Response({
                    'success': True,
                    'data': {
                        'policy_id': str(policy.id),
                        'policy_title': policy.title,
                        'matrix': []
                    }
                })
            
            # 매트릭스 데이터 직렬화
            matrix_data = []
            for matrix_item in matrix_queryset:
                matrix_data.append({
                    'id': str(matrix_item.id),
                    'plan_range': matrix_item.plan_range,  # 숫자 값으로 전송
                    'plan_range_display': matrix_item.get_plan_range_display(),  # 표시용
                    'contract_period': matrix_item.contract_period,
                    'rebate_amount': float(matrix_item.rebate_amount),
                    'carrier': matrix_item.carrier,
                    'row': list(dict(CommissionMatrix.PLAN_RANGE_CHOICES).keys()).index(matrix_item.plan_range),
                    'col': 0 if matrix_item.contract_period == 12 else 1  # 12개월=0, 24개월=1
                })
            
            logger.info(f"리베이트 매트릭스 직렬화 완료: {len(matrix_data)}개 항목")
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'policy_title': policy.title,
                    'matrix': matrix_data
                }
            })
            
        except Exception as e:
            logger.error(f"리베이트 매트릭스 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '리베이트 매트릭스를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request, policy_id):
        """리베이트 매트릭스 생성/수정"""
        return self._save_matrix(request, policy_id)
    
    def put(self, request, policy_id):
        """리베이트 매트릭스 수정 (POST와 동일)"""
        return self._save_matrix(request, policy_id)
    
    def _save_matrix(self, request, policy_id):
        """리베이트 매트릭스 저장 공통 로직"""
        try:
            from .models import CommissionMatrix
            
            policy = get_object_or_404(Policy, id=policy_id)
            data = request.data
            
            # 기존 매트릭스 삭제 후 새로 생성
            CommissionMatrix.objects.filter(policy=policy).delete()
            
            # 새 매트릭스 생성
            matrix_data = data.get('matrix', [])
            created_count = 0
            
            for item in matrix_data:
                # plan_range 값 처리 (숫자 또는 문자열 모두 지원)
                plan_range_raw = item.get('plan_range', 11000)
                if isinstance(plan_range_raw, str):
                    # 문자열인 경우 (예: "11K")
                    plan_range_value = int(plan_range_raw.replace('K', '')) * 1000
                else:
                    # 숫자인 경우 (예: 11000)
                    plan_range_value = int(plan_range_raw)
                
                rebate_amount = item.get('rebate_amount', 0)
                contract_period = item.get('contract_period', 12)
                
                logger.info(f"매트릭스 항목 처리: plan_range={plan_range_value}, period={contract_period}, amount={rebate_amount}")
                
                # 0이 아닌 리베이트만 저장
                if rebate_amount > 0:
                    CommissionMatrix.objects.create(
                        policy=policy,
                        carrier=policy.carrier,  # 정책의 통신사 사용
                        plan_range=plan_range_value,
                        contract_period=contract_period,
                        rebate_amount=rebate_amount
                    )
                    created_count += 1
            
            logger.info(f"리베이트 매트릭스 저장 완료: 정책 {policy.title}, {created_count}개 항목")
            
            return Response({
                'success': True,
                'message': f'리베이트 매트릭스가 저장되었습니다. ({created_count}개 항목)',
                'data': {
                    'policy_id': str(policy.id),
                    'matrix_count': created_count
                }
            })
            
        except Exception as e:
            logger.error(f"리베이트 매트릭스 저장 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '리베이트 매트릭스 저장 중 오류가 발생했습니다.'
            }, status=500)


class AgencyRebateMatrixView(APIView):
    """협력사 리베이트 설정 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """협력사 리베이트 설정 조회 (본사 매트릭스 + 협력사 매트릭스)"""
        try:
            from .models import AgencyRebateMatrix, RebateMatrix
            from companies.models import CompanyUser
            
            logger.info(f"협력사 리베이트 매트릭스 조회 요청 - 정책 ID: {policy_id}")
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책 찾음: {policy.title}")
            
            # 현재 사용자의 협력사 정보 확인
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                agency = company_user.company
                logger.info(f"협력사 정보: {agency.name} ({agency.type})")
                
                if agency.type != 'agency':
                    return Response({
                        'success': False,
                        'message': '협력사만 접근 가능합니다.'
                    }, status=403)
            except CompanyUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '업체 정보를 찾을 수 없습니다.'
                }, status=400)
            
            # 1. 본사 리베이트 매트릭스 조회 (참고용)
            hq_rebates = RebateMatrix.objects.filter(policy=policy).order_by('plan_range', 'contract_period')
            logger.info(f"본사 리베이트 매트릭스 개수: {hq_rebates.count()}")
            
            hq_matrix_data = []
            for rebate in hq_rebates:
                hq_matrix_data.append({
                    'id': f"hq-{rebate.id}",
                    'plan_range': rebate.plan_range,  # 숫자 값
                    'plan_range_display': rebate.get_plan_range_display(),  # 표시용
                    'contract_period': rebate.contract_period,
                    'rebate_amount': float(rebate.rebate_amount),
                    'carrier': rebate.carrier,
                    'row': list(dict(RebateMatrix.PLAN_RANGE_CHOICES).keys()).index(rebate.plan_range),
                    'col': list(dict(RebateMatrix.CONTRACT_PERIOD_CHOICES).keys()).index(rebate.contract_period)
                })
            
            # 2. 협력사 리베이트 매트릭스 조회 (편집용)
            agency_rebates = AgencyRebateMatrix.objects.filter(
                policy=policy,
                agency=agency
            ).order_by('plan_range', 'contract_period')
            logger.info(f"협력사 리베이트 매트릭스 개수: {agency_rebates.count()}")
            
            agency_matrix_data = []
            for rebate in agency_rebates:
                agency_matrix_data.append({
                    'id': f"agency-{rebate.id}",
                    'plan_range': rebate.plan_range,  # 숫자 값
                    'plan_range_display': rebate.get_plan_range_display(),  # 표시용
                    'contract_period': rebate.contract_period,
                    'rebate_amount': float(rebate.rebate_amount),
                    'carrier': rebate.carrier,
                    'row': list(dict(AgencyRebateMatrix.PLAN_RANGE_CHOICES).keys()).index(rebate.plan_range),
                    'col': list(dict(AgencyRebateMatrix.CONTRACT_PERIOD_CHOICES).keys()).index(rebate.contract_period)
                })
            
            logger.info(f"응답 데이터 준비 완료 - 본사: {len(hq_matrix_data)}개, 협력사: {len(agency_matrix_data)}개")
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'policy_title': policy.title,
                    'agency_id': str(agency.id),
                    'agency_name': agency.name,
                    'hq_matrix': hq_matrix_data,  # 본사 매트릭스 (참고용)
                    'agency_matrix': agency_matrix_data  # 협력사 매트릭스 (편집용)
                }
            })
            
        except Exception as e:
            logger.error(f"협력사 리베이트 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '협력사 리베이트를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request, policy_id):
        """협력사 리베이트 설정 저장"""
        try:
            from .models import AgencyRebateMatrix
            from companies.models import CompanyUser
            
            policy = get_object_or_404(Policy, id=policy_id)
            data = request.data
            
            # 현재 사용자의 협력사 정보 확인
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                agency = company_user.company
                
                if agency.type != 'agency':
                    return Response({
                        'success': False,
                        'message': '협력사만 접근 가능합니다.'
                    }, status=403)
            except CompanyUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '업체 정보를 찾을 수 없습니다.'
                }, status=400)
            
            # 기존 협력사 리베이트 매트릭스 삭제 후 새로 생성
            AgencyRebateMatrix.objects.filter(policy=policy, agency=agency).delete()
            
            # 새 협력사 리베이트 매트릭스 생성
            matrix_data = data.get('matrix', [])
            for item in matrix_data:
                # plan_range 값 처리 (숫자 또는 문자열)
                plan_range_raw = item.get('plan_range', 11000)
                
                if isinstance(plan_range_raw, str):
                    # 문자열인 경우 (예: "11K")
                    plan_range_value = int(plan_range_raw.replace('K', '')) * 1000
                else:
                    # 이미 숫자인 경우 (예: 11000)
                    plan_range_value = int(plan_range_raw)
                
                AgencyRebateMatrix.objects.create(
                    policy=policy,
                    agency=agency,
                    carrier=policy.carrier,
                    plan_range=plan_range_value,
                    contract_period=item.get('contract_period', 12),
                    rebate_amount=item.get('rebate_amount', 0)
                )
            
            return Response({
                'success': True,
                'message': '협력사 리베이트가 저장되었습니다.',
                'data': {
                    'policy_id': str(policy.id),
                    'agency_id': str(agency.id),
                    'matrix_count': len(matrix_data)
                }
            })
            
        except Exception as e:
            logger.error(f"협력사 리베이트 저장 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '협력사 리베이트 저장 중 오류가 발생했습니다.'
            }, status=500)


class RetailRebateView(APIView):
    """판매점 리베이트 조회 API"""
    permission_classes = [IsAuthenticated]

    def get(self, request, policy_id):
        """판매점이 협력사로부터 받을 수 있는 리베이트 조회"""
        try:
            from .models import AgencyRebateMatrix
            from companies.models import CompanyUser
            
            logger.info(f"판매점 리베이트 조회 요청 - 정책 ID: {policy_id}")
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책 찾음: {policy.title}")
            
            # 현재 사용자의 판매점 정보 확인
            try:
                company_user = CompanyUser.objects.get(django_user=request.user)
                retail = company_user.company
                logger.info(f"판매점 정보: {retail.name} ({retail.type})")
                
                if retail.type != 'retail':
                    return Response({
                        'success': False,
                        'message': '판매점만 접근 가능합니다.'
                    }, status=403)
                
                # 상위 협력사 확인
                agency = retail.parent_company
                if not agency or agency.type != 'agency':
                    return Response({
                        'success': False,
                        'message': '상위 협력사 정보를 찾을 수 없습니다.'
                    }, status=400)
                
                logger.info(f"상위 협력사: {agency.name}")
                
            except CompanyUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '업체 정보를 찾을 수 없습니다.'
                }, status=400)
            
            # 협력사가 설정한 리베이트 매트릭스 조회
            agency_rebates = AgencyRebateMatrix.objects.filter(
                policy=policy,
                agency=agency
            ).order_by('plan_range', 'contract_period')
            
            logger.info(f"협력사 리베이트 매트릭스 개수: {agency_rebates.count()}")
            
            if agency_rebates.count() == 0:
                return Response({
                    'success': True,
                    'message': '협력사에서 설정한 리베이트가 없습니다.',
                    'data': {
                        'policy_id': str(policy.id),
                        'policy_title': policy.title,
                        'retail_id': str(retail.id),
                        'retail_name': retail.name,
                        'agency_id': str(agency.id),
                        'agency_name': agency.name,
                        'rebate_matrix': []
                    }
                })
            
            # 리베이트 매트릭스 데이터 구성
            rebate_matrix_data = []
            for rebate in agency_rebates:
                rebate_matrix_data.append({
                    'id': f"retail-{rebate.id}",
                    'plan_range': rebate.plan_range,  # 숫자 값
                    'plan_range_display': rebate.get_plan_range_display(),  # 표시용
                    'contract_period': rebate.contract_period,
                    'rebate_amount': float(rebate.rebate_amount),
                    'carrier': rebate.carrier,
                    'row': list(dict(AgencyRebateMatrix.PLAN_RANGE_CHOICES).keys()).index(rebate.plan_range),
                    'col': list(dict(AgencyRebateMatrix.CONTRACT_PERIOD_CHOICES).keys()).index(rebate.contract_period)
                })
            
            logger.info(f"응답 데이터 준비 완료 - 리베이트: {len(rebate_matrix_data)}개")
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'policy_title': policy.title,
                    'retail_id': str(retail.id),
                    'retail_name': retail.name,
                    'agency_id': str(agency.id),
                    'agency_name': agency.name,
                    'rebate_matrix': rebate_matrix_data
                }
            })
            
        except Exception as e:
            logger.error(f"판매점 리베이트 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '리베이트 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)


# 그레이드 관련 API 추가
@csrf_exempt
def policy_api_detail(request, policy_id):
    """정책 상세 조회 API (AJAX용)"""
    if request.method == 'GET':
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 정책 시리얼라이저로 변환
            serializer = PolicySerializer(policy)
            
            return JsonResponse({
                'success': True,
                'data': serializer.data
            })
        
        except Policy.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '정책을 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            logger.error(f"정책 상세 조회 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '정책 정보를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'}, status=405)


@csrf_exempt
def policy_api_update(request, policy_id):
    """정책 수정 API (AJAX용)"""
    if request.method in ['PUT', 'PATCH']:
        try:
            policy = get_object_or_404(Policy, id=policy_id)
            
            # 권한 확인: 본사만 정책 수정 가능
            if not request.user.is_superuser:
                try:
                    from companies.models import CompanyUser
                    company_user = CompanyUser.objects.get(django_user=request.user)
                    if company_user.company.type != 'headquarters':
                        return JsonResponse({
                            'success': False,
                            'message': '본사 관리자만 정책을 수정할 수 있습니다.'
                        }, status=403)
                except CompanyUser.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '업체 정보를 찾을 수 없습니다.'
                    }, status=400)
            
            # JSON 데이터 파싱
            import json
            data = json.loads(request.body)
            
            # 기본 필드 업데이트
            policy.title = data.get('title', policy.title)
            policy.description = data.get('description', policy.description)
            policy.carrier = data.get('carrier', policy.carrier)
            policy.rebate_agency = data.get('rebate_agency', policy.rebate_agency)
            policy.rebate_retail = data.get('rebate_retail', policy.rebate_retail)
            policy.is_active = data.get('is_active', policy.is_active)
            
            policy.save()
            
            logger.info(f"정책 수정 완료: {policy.title} (사용자: {request.user.username})")
            
            # 수정된 정책 데이터 반환
            serializer = PolicySerializer(policy)
            
            return JsonResponse({
                'success': True,
                'message': '정책이 성공적으로 수정되었습니다.',
                'data': serializer.data
            })
            
        except Policy.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '정책을 찾을 수 없습니다.'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 JSON 형식입니다.'
            }, status=400)
        except Exception as e:
            logger.error(f"정책 수정 실패: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '정책 수정 중 오류가 발생했습니다.'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'}, status=405)


# Commission Matrix API
class PolicyCommissionMatrixView(APIView):
    """정책별 수수료 매트릭스 API (기존 RebateMatrix → CommissionMatrix)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, policy_id):
        """정책의 수수료 매트릭스 조회"""
        try:
            from .models import CommissionMatrix
            
            logger.info(f"수수료 매트릭스 조회 요청 - 정책 ID: {policy_id}")
            policy = get_object_or_404(Policy, id=policy_id)
            logger.info(f"정책 찾음: {policy.title}")
            
            # 해당 정책의 수수료 매트릭스 조회
            matrix_queryset = CommissionMatrix.objects.filter(policy=policy).order_by('plan_range', 'contract_period')
            logger.info(f"수수료 매트릭스 개수: {matrix_queryset.count()}")
            
            if not matrix_queryset.exists():
                # 매트릭스가 없으면 빈 매트릭스 반환
                logger.info("수수료 매트릭스가 없음, 빈 매트릭스 반환")
                return Response({
                    'success': True,
                    'data': {
                        'policy_id': str(policy.id),
                        'policy_title': policy.title,
                        'matrix': []
                    }
                })
            
            # 매트릭스 데이터 직렬화
            matrix_data = []
            for matrix_item in matrix_queryset:
                matrix_data.append({
                    'id': str(matrix_item.id),
                    'plan_range': matrix_item.plan_range,
                    'plan_range_display': matrix_item.get_plan_range_display(),
                    'contract_period': matrix_item.contract_period,
                    'rebate_amount': float(matrix_item.rebate_amount),
                    'carrier': matrix_item.carrier,
                    'row': list(dict(CommissionMatrix.PLAN_RANGE_CHOICES).keys()).index(matrix_item.plan_range),
                    'col': 0 if matrix_item.contract_period == 12 else (1 if matrix_item.contract_period == 24 else 2)
                })
            
            logger.info(f"수수료 매트릭스 직렬화 완료: {len(matrix_data)}개 항목")
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'policy_title': policy.title,
                    'matrix': matrix_data
                }
            })
            
        except Exception as e:
            logger.error(f"수수료 매트릭스 조회 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '수수료 매트릭스를 불러오는 중 오류가 발생했습니다.'
            }, status=500)
    
    def post(self, request, policy_id):
        """수수료 매트릭스 생성/수정"""
        return self._save_matrix(request, policy_id)
    
    def put(self, request, policy_id):
        """수수료 매트릭스 수정 (POST와 동일)"""
        return self._save_matrix(request, policy_id)
    
    def _save_matrix(self, request, policy_id):
        """수수료 매트릭스 저장 공통 로직"""
        try:
            from .models import CommissionMatrix
            
            policy = get_object_or_404(Policy, id=policy_id)
            data = request.data
            
            # 기존 매트릭스 삭제 후 새로 생성
            CommissionMatrix.objects.filter(policy=policy).delete()
            
            # 새 매트릭스 생성
            matrix_data = data.get('matrix', [])
            created_count = 0
            
            for item in matrix_data:
                # plan_range 값 처리
                plan_range_raw = item.get('plan_range', 11000)
                if isinstance(plan_range_raw, str):
                    plan_range_value = int(plan_range_raw.replace('K', '')) * 1000
                else:
                    plan_range_value = int(plan_range_raw)
                
                rebate_amount = item.get('rebate_amount', 0)
                contract_period = item.get('contract_period', 12)
                
                # 필수 필드 검증
                if not plan_range_value or not contract_period:
                    logger.warning(f"필수 필드 누락: {item}")
                    continue

                # 0이 아닌 수수료만 저장
                if rebate_amount > 0:
                    CommissionMatrix.objects.create(
                        policy=policy,
                        carrier=policy.carrier,
                        plan_range=plan_range_value,
                        contract_period=contract_period,
                        rebate_amount=rebate_amount
                    )
                    created_count += 1
            
            logger.info(f"수수료 매트릭스 저장 완료: 정책 {policy.title}, {created_count}개 항목")
            
            return Response({
                'success': True,
                'message': f'수수료 매트릭스가 저장되었습니다. ({created_count}개 항목)',
                'data': {
                    'policy_id': str(policy.id),
                    'matrix_count': created_count
                }
            })
            
        except Exception as e:
            logger.error(f"수수료 매트릭스 저장 오류: {str(e)}")
            return Response({
                'success': False,
                'message': '수수료 매트릭스 저장 중 오류가 발생했습니다.'
            }, status=500)


# Commission Grade API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def policy_commission_grades(request, policy_id):
    """정책별 수수료 그레이드 조회 API"""
    try:
        policy = get_object_or_404(Policy, id=policy_id)
        
        # 수수료 그레이드 반환
        commission_grades = policy.commission_grades or []
        
        return Response({
            'success': True,
            'data': {
                'policy_id': str(policy.id),
                'policy_title': policy.title,
                'grade_period_type': policy.grade_period_type,
                'grade_period_type_display': policy.get_grade_period_type_display(),
                'commission_grades': commission_grades,
                'grade_summary': policy.get_grade_summary()
            }
        })
        
    except Exception as e:
        logger.error(f"수수료 그레이드 조회 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '수수료 그레이드를 불러오는 중 오류가 발생했습니다.'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_grade_bonus(request):
    """그레이드 보너스 계산 API"""
    try:
        data = request.data
        policy_id = data.get('policy_id')
        company_id = data.get('company_id')
        order_count = data.get('order_count', 0)
        
        if not all([policy_id, company_id]):
            return Response({
                'success': False,
                'message': '필수 파라미터가 누락되었습니다.'
            }, status=400)
        
        policy = get_object_or_404(Policy, id=policy_id)
        company = get_object_or_404(Company, id=company_id)
        
        # 적용 가능한 그레이드 찾기
        applicable_grade = policy.get_applicable_grade(order_count)
        
        if applicable_grade:
            bonus_per_order = float(applicable_grade['bonus_per_order'])
            total_bonus = order_count * bonus_per_order
            
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'company_id': str(company.id),
                    'order_count': order_count,
                    'applicable_grade': applicable_grade,
                    'bonus_per_order': bonus_per_order,
                    'total_bonus': total_bonus,
                    'grade_period_type': policy.grade_period_type
                }
            })
        else:
            return Response({
                'success': True,
                'data': {
                    'policy_id': str(policy.id),
                    'company_id': str(company.id),
                    'order_count': order_count,
                    'applicable_grade': None,
                    'bonus_per_order': 0,
                    'total_bonus': 0,
                    'grade_period_type': policy.grade_period_type,
                    'message': '적용 가능한 그레이드가 없습니다.'
                }
            })
        
    except Exception as e:
        logger.error(f"그레이드 보너스 계산 오류: {str(e)}")
        return Response({
            'success': False,
            'message': '그레이드 보너스 계산 중 오류가 발생했습니다.'
        }, status=500)
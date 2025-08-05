from django.db.models import Q
from .models import Policy
from companies.models import CompanyUser

def get_visible_policies(user):
    """
    사용자의 계층에 따라 볼 수 있는 정책들을 반환합니다.
    - 슈퍼유저: 모든 정책
    - 본사/협력사/대리점/판매점:
        1. 자신이 속한 회사가 생성한 정책
        2. 상위 회사가 생성한 정책
        3. 자신에게 직접 배정된 정책
    """
    if not user.is_authenticated:
        return Policy.objects.none()

    if user.is_superuser:
        return Policy.objects.all()

    try:
        company_user = CompanyUser.objects.get(django_user=user)
        user_company = company_user.company
    except CompanyUser.DoesNotExist:
        return Policy.objects.none()

    # 1. 자신이 속한 회사 및 상위 회사들의 ID 목록
    company_ids = [user_company.id]
    parent = user_company.parent_company
    while parent:
        company_ids.append(parent.id)
        parent = parent.parent_company

    # 2. 자신이 속한 회사가 생성했거나 상위 회사가 생성한 정책
    created_by_companies_q = Q(created_by__companyuser__company__id__in=company_ids)

    # 3. 자신에게 직접 배정된 정책
    assigned_to_me_q = Q(assignments__company=user_company)

    # 두 조건을 OR로 결합하여 중복 없이 모든 관련 정책을 가져옴
    return Policy.objects.filter(created_by_companies_q | assigned_to_me_q).distinct()

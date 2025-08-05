from django.db.models import Q
from .models import Company, CompanyUser

def get_all_child_company_ids(company):
    """
    재귀적으로 모든 하위 회사의 ID 목록을 가져옵니다.
    """
    children = company.child_companies.all()
    ids = {child.id for child in children}
    for child in children:
        ids.update(get_all_child_company_ids(child))
    return ids

def get_visible_companies(user):
    """
    사용자의 계층에 따라 볼 수 있는 회사들을 반환합니다.
    """
    if not user.is_authenticated:
        return Company.objects.none()

    if user.is_superuser:
        return Company.objects.all()

    try:
        company_user = CompanyUser.objects.get(django_user=user)
        user_company = company_user.company
    except CompanyUser.DoesNotExist:
        return Company.objects.none()

    # 자신과 모든 하위 회사를 포함
    company_ids = get_all_child_company_ids(user_company)
    company_ids.add(user_company.id)

    return Company.objects.filter(id__in=company_ids)

def get_visible_users(user):
    """
    사용자의 계층에 따라 볼 수 있는 사용자들을 반환합니다.
    """
    visible_companies = get_visible_companies(user)
    return CompanyUser.objects.filter(company__in=visible_companies)

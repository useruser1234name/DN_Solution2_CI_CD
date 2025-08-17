from django.db.models import Q
from .models import Company, CompanyUser
from django.db import models

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
    사용자 계층에 따라 볼 수 있는 회사들을 반환합니다.
    """
    if not user.is_authenticated:
        return Company.objects.none()
    accessible_ids = get_accessible_company_ids(user)
    return Company.objects.filter(id__in=accessible_ids)

def get_visible_users(user):
    """
    사용자 계층에 따라 볼 수 있는 사용자들을 반환합니다.
    """
    accessible_ids = get_accessible_company_ids(user)
    return CompanyUser.objects.filter(company__id__in=accessible_ids)

def get_accessible_company_ids(user):
    """
    로그인한 사용자가 접근 가능한 업체 id 리스트 반환
    """
    if user.is_superuser:
        return Company.objects.values_list('id', flat=True)
    try:
        company_user = CompanyUser.objects.get(django_user=user)
    except CompanyUser.DoesNotExist:
        return Company.objects.none()
    company = company_user.company

    if company.is_headquarters:
        # 본사는 자기 자신 + 직접 하위 협력사들 + 그 하위 판매점들만 접근 가능
        def get_all_descendants(parent_company):
            """재귀적으로 모든 하위 업체 ID를 가져오는 함수"""
            descendants = []
            direct_children = Company.objects.filter(parent_company=parent_company)
            for child in direct_children:
                descendants.append(child.id)
                descendants.extend(get_all_descendants(child))
            return descendants
        
        # 자기 자신 + 모든 하위 업체들
        accessible_ids = [company.id]
        accessible_ids.extend(get_all_descendants(company))
        return accessible_ids
    elif company.is_agency:
        # 협력사는 자기 자신 + 하위 판매점들만 접근 가능
        return Company.objects.filter(
            models.Q(id=company.id) |                    # 자기 자신
            models.Q(parent_company=company)             # 하위 판매점들만
        ).values_list('id', flat=True)
    elif company.is_dealer:
        # 대리점은 자기 자신 + 하위(판매점) 접근 가능
        return Company.objects.filter(
            models.Q(id=company.id) |
            models.Q(parent_company=company)
        ).values_list('id', flat=True)
    elif company.is_retail:
        # 판매점은 자기 자신만
        return Company.objects.filter(id=company.id).values_list('id', flat=True)
    else:
        return Company.objects.none()

from django.db.models import Q
from .models import Order
from companies.models import CompanyUser

def get_visible_orders(user):
    """
    사용자의 계층에 따라 볼 수 있는 주문들을 반환합니다.
    - 슈퍼유저: 모든 주문
    - 본사: 자신의 하위 업체(협력사, 대리점, 판매점)의 모든 주문
    - 협력사/대리점: 자신 및 자신의 하위 업체의 모든 주문
    - 판매점: 자신의 주문
    """
    if not user.is_authenticated:
        return Order.objects.none()

    if user.is_superuser:
        return Order.objects.all()

    try:
        company_user = CompanyUser.objects.get(django_user=user)
        user_company = company_user.company
    except CompanyUser.DoesNotExist:
        return Order.objects.none()

    # 재귀적으로 모든 하위 회사 ID를 가져오는 함수
    def get_all_child_company_ids(company):
        children = company.child_companies.all()
        ids = {child.id for child in children}
        for child in children:
            ids.update(get_all_child_company_ids(child))
        return ids

    child_company_ids = get_all_child_company_ids(user_company)
    child_company_ids.add(user_company.id)  # 자기 자신도 포함

    return Order.objects.filter(company__id__in=child_company_ids)

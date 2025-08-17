from django.contrib.auth.models import User
from companies.models import Company, CompanyUser

# h_admin 사용자 확인
users = User.objects.filter(username='h_admin')
print(f'Found {users.count()} users with username h_admin')
for u in users:
    print(f'  - ID: {u.id}, Username: {u.username}, Date joined: {u.date_joined}')
    try:
        company_user = CompanyUser.objects.get(django_user=u)
        print(f'    Company: {company_user.company.name} ({company_user.company.code})')
    except CompanyUser.DoesNotExist:
        print(f'    No company associated')

# 테스트를 위해 h_admin 사용자 삭제
if users.exists():
    print("\nDeleting h_admin user(s) for testing...")
    users.delete()
    print("Deleted successfully")

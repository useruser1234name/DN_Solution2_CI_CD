import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dn_solution.settings')
django.setup()

from django.contrib.auth.models import User

def check_user(username, password):
    print(f"\n🔍 사용자 '{username}' 체크:")
    try:
        user = User.objects.get(username=username)
        print(f"   ✅ 존재함")
        print(f"   - ID: {user.id}")
        print(f"   - 이메일: {user.email}")
        print(f"   - 활성화: {user.is_active}")
        print(f"   - 스태프: {user.is_staff}")
        print(f"   - 슈퍼유저: {user.is_superuser}")
        print(f"   - 마지막 로그인: {user.last_login}")
        print(f"   - 등록일: {user.date_joined}")
        
        # 비밀번호 확인
        if user.check_password(password):
            print(f"   ✅ 비밀번호 '{password}' 일치함")
            return True
        else:
            print(f"   ❌ 비밀번호 '{password}' 불일치")
            print(f"   🔧 비밀번호를 '{password}'로 재설정...")
            user.set_password(password)
            user.save()
            print(f"   ✅ 비밀번호 재설정 완료")
            return True
            
    except User.DoesNotExist:
        print(f"   ❌ 존재하지 않음")
        return False

# 두 계정 모두 체크
users_to_check = [
    ('hyeob_admin', 'papyrus03'),
    ('hyeob_admin2', 'papyrus03')
]

print("=" * 50)
print("📋 사용자 계정 비교 분석")
print("=" * 50)

for username, password in users_to_check:
    check_user(username, password)

print("\n🔐 JWT 로그인 테스트...")
import requests

for username, password in users_to_check:
    url = "http://localhost:8001/api/companies/auth/jwt/login/"
    data = {"username": username, "password": password}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"✅ {username}: JWT 로그인 성공!")
        else:
            print(f"❌ {username}: JWT 로그인 실패 ({response.status_code})")
            print(f"   응답: {response.text}")
    except Exception as e:
        print(f"❌ {username}: 요청 오류 - {e}")

print("\n📊 전체 사용자 목록:")
users = User.objects.all()
for user in users:
    print(f"   - {user.username} (활성: {user.is_active}, 스태프: {user.is_staff})")
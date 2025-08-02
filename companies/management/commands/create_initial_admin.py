"""
초기 관리자 계정 생성 명령어

이 명령어는 시스템 초기 설정을 위한 관리자 계정을 생성합니다.
본사 업체와 승인된 관리자 계정을 자동으로 생성합니다.
"""

import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from companies.models import Company, CompanyUser


class Command(BaseCommand):
    help = '초기 관리자 계정을 생성합니다.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='관리자 사용자명 (기본값: admin)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin1234',
            help='관리자 비밀번호 (기본값: admin1234)'
        )
        parser.add_argument(
            '--company-name',
            type=str,
            default='메인 본사',
            help='본사 업체명 (기본값: 메인 본사)'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            default='HQ_MAIN',
            help='본사 업체 코드 (기본값: HQ_MAIN)'
        )
    
    def handle(self, *args, **options):
        try:
            # 1. Django 슈퍼유저 생성
            username = options['username']
            password = options['password']
            
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'사용자 "{username}"이 이미 존재합니다.')
                )
                django_user = User.objects.get(username=username)
            else:
                django_user = User.objects.create_superuser(
                    username=username,
                    email=f'{username}@example.com',
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Django 슈퍼유저 "{username}"이 생성되었습니다.')
                )
            
            # 2. 본사 업체 생성
            company_name = options['company_name']
            company_code = options['company_code']
            
            if Company.objects.filter(code=company_code).exists():
                self.stdout.write(
                    self.style.WARNING(f'업체 코드 "{company_code}"이 이미 존재합니다.')
                )
                company = Company.objects.get(code=company_code)
            else:
                company = Company.objects.create(
                    code=company_code,
                    name=company_name,
                    type='headquarters',
                    status=True,
                    visible=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'본사 업체 "{company_name}"이 생성되었습니다.')
                )
            
            # 3. CompanyUser 생성
            if CompanyUser.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'CompanyUser "{username}"이 이미 존재합니다.')
                )
                company_user = CompanyUser.objects.get(username=username)
            else:
                company_user = CompanyUser.objects.create(
                    company=company,
                    django_user=django_user,
                    username=username,
                    role='admin',
                    is_approved=True,
                    status='approved'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'CompanyUser "{username}"이 생성되었습니다.')
                )
            
            # 4. 결과 출력
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n초기 관리자 계정이 성공적으로 생성되었습니다!\n'
                    f'사용자명: {username}\n'
                    f'비밀번호: {password}\n'
                    f'업체명: {company_name}\n'
                    f'업체 코드: {company_code}\n'
                    f'Django Admin URL: http://localhost:8000/admin/\n'
                )
            )
            
        except Exception as e:
            raise CommandError(f'초기 관리자 계정 생성 중 오류가 발생했습니다: {str(e)}') 
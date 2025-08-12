# -*- coding: utf-8 -*-
"""
Cache Management Command - DN_SOLUTION2 리모델링
캐시 관리 명령어
"""

import json
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.cache import cache
from dn_solution.cache_utils import CacheUtils


class Command(BaseCommand):
    """캐시 관리 명령어"""
    
    help = 'DN_SOLUTION2 캐시 시스템 관리 도구'
    
    def add_arguments(self, parser):
        """명령어 인자 추가"""
        parser.add_argument(
            'action',
            choices=[
                'status', 'clear', 'warm_up', 'health_check', 
                'stats', 'test_performance', 'invalidate'
            ],
            help='실행할 작업 선택'
        )
        
        parser.add_argument(
            '--pattern',
            type=str,
            help='캐시 키 패턴 (invalidate, clear에서 사용)'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='테스트 타임아웃 (초)'
        )
        
        parser.add_argument(
            '--iterations',
            type=int,
            default=100,
            help='성능 테스트 반복 횟수'
        )
        
        parser.add_argument(
            '--json',
            action='store_true',
            help='JSON 형태로 결과 출력'
        )
    
    def handle(self, *args, **options):
        """명령어 처리"""
        action = options['action']
        
        try:
            if action == 'status':
                self.show_cache_status(options)
            elif action == 'clear':
                self.clear_cache(options)
            elif action == 'warm_up':
                self.warm_up_cache(options)
            elif action == 'health_check':
                self.health_check(options)
            elif action == 'stats':
                self.show_cache_stats(options)
            elif action == 'test_performance':
                self.test_performance(options)
            elif action == 'invalidate':
                self.invalidate_cache(options)
            else:
                raise CommandError(f"알 수 없는 작업: {action}")
                
        except Exception as e:
            raise CommandError(f"작업 실행 실패: {e}")
    
    def show_cache_status(self, options):
        """캐시 상태 표시"""
        self.stdout.write(self.style.SUCCESS("=== 캐시 시스템 상태 ==="))
        
        # 기본 정보
        self.stdout.write(f"캐시 백엔드: {cache_manager.cache.__class__.__name__}")
        self.stdout.write(f"캐시 레벨: {cache_manager.cache_level}")
        
        # 헬스체크
        health_status = CacheMonitor.health_check()
        status_color = self.style.SUCCESS if health_status['status'] == 'healthy' else self.style.ERROR
        self.stdout.write(f"상태: {status_color(health_status['status'])}")
        
        # 상세 정보
        if not options.get('json'):
            self.stdout.write("\n=== 테스트 결과 ===")
            self.stdout.write(f"쓰기 테스트: {'✅' if health_status.get('write_test') else '❌'}")
            self.stdout.write(f"읽기 테스트: {'✅' if health_status.get('read_test') else '❌'}")
            self.stdout.write(f"삭제 테스트: {'✅' if health_status.get('delete_test') else '❌'}")
        else:
            self.stdout.write(json.dumps(health_status, indent=2))
    
    def clear_cache(self, options):
        """캐시 삭제"""
        pattern = options.get('pattern')
        
        if pattern:
            # 패턴 매칭 삭제
            count = cache_manager.delete_pattern(pattern)
            self.stdout.write(
                self.style.SUCCESS(f"패턴 '{pattern}'에 매치되는 {count}개 캐시 키 삭제 완료")
            )
        else:
            # 전체 캐시 삭제
            self.stdout.write("전체 캐시를 삭제하시겠습니까? [y/N]: ", ending='')
            confirm = input().lower()
            
            if confirm in ['y', 'yes']:
                success = cache_manager.clear()
                if success:
                    self.stdout.write(self.style.SUCCESS("전체 캐시 삭제 완료"))
                else:
                    self.stdout.write(self.style.ERROR("캐시 삭제 실패"))
            else:
                self.stdout.write("작업이 취소되었습니다.")
    
    def warm_up_cache(self, options):
        """캐시 워밍업"""
        self.stdout.write("캐시 워밍업을 시작합니다...")
        
        start_time = time.time()
        warmed_keys = 0
        
        try:
            # 자주 사용되는 데이터 미리 캐싱
            
            # 1. 사용자 데이터
            self._warm_up_user_data()
            warmed_keys += 1
            
            # 2. 회사 데이터
            self._warm_up_company_data()
            warmed_keys += 1
            
            # 3. 정책 데이터
            self._warm_up_policy_data()
            warmed_keys += 1
            
            # 4. 시스템 설정
            self._warm_up_system_settings()
            warmed_keys += 1
            
            elapsed_time = time.time() - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"캐시 워밍업 완료: {warmed_keys}개 그룹, {elapsed_time:.2f}초 소요"
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"캐시 워밍업 실패: {e}"))
    
    def health_check(self, options):
        """헬스체크"""
        self.stdout.write("캐시 시스템 헬스체크를 실행합니다...")
        
        health_status = CacheMonitor.health_check()
        
        if options.get('json'):
            self.stdout.write(json.dumps(health_status, indent=2))
        else:
            status = health_status['status']
            if status == 'healthy':
                self.stdout.write(self.style.SUCCESS("✅ 캐시 시스템이 정상 작동중입니다"))
            else:
                self.stdout.write(self.style.ERROR("❌ 캐시 시스템에 문제가 있습니다"))
                if 'error' in health_status:
                    self.stdout.write(f"오류: {health_status['error']}")
    
    def show_cache_stats(self, options):
        """캐시 통계 표시"""
        stats = CacheMonitor.get_cache_stats()
        
        if options.get('json'):
            self.stdout.write(json.dumps(stats, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("=== Redis 캐시 통계 ==="))
            
            if stats:
                self.stdout.write(f"Redis 버전: {stats.get('redis_version', 'N/A')}")
                self.stdout.write(f"사용 메모리: {stats.get('used_memory', 'N/A')}")
                self.stdout.write(f"연결된 클라이언트: {stats.get('connected_clients', 'N/A')}")
                self.stdout.write(f"처리된 명령: {stats.get('total_commands_processed', 'N/A')}")
                self.stdout.write(f"키스페이스 히트: {stats.get('keyspace_hits', 'N/A')}")
                self.stdout.write(f"키스페이스 미스: {stats.get('keyspace_misses', 'N/A')}")
                self.stdout.write(f"히트율: {stats.get('hit_rate', 'N/A')}%")
            else:
                self.stdout.write("통계 정보를 가져올 수 없습니다.")
    
    def test_performance(self, options):
        """성능 테스트"""
        iterations = options.get('iterations', 100)
        self.stdout.write(f"캐시 성능 테스트를 시작합니다... ({iterations}회 반복)")
        
        # 쓰기 성능 테스트
        write_times = []
        for i in range(iterations):
            start_time = time.time()
            key = f"perf_test_write_{i}"
            value = {'test_data': i, 'timestamp': timezone.now().isoformat()}
            cache_manager.set(key, value, 60)
            write_times.append(time.time() - start_time)
        
        # 읽기 성능 테스트
        read_times = []
        for i in range(iterations):
            start_time = time.time()
            key = f"perf_test_write_{i}"
            cache_manager.get(key)
            read_times.append(time.time() - start_time)
        
        # 결과 계산
        avg_write_time = sum(write_times) / len(write_times) * 1000  # ms
        avg_read_time = sum(read_times) / len(read_times) * 1000  # ms
        
        # 정리
        for i in range(iterations):
            cache_manager.delete(f"perf_test_write_{i}")
        
        results = {
            'iterations': iterations,
            'average_write_time_ms': round(avg_write_time, 3),
            'average_read_time_ms': round(avg_read_time, 3),
            'total_time_ms': round(sum(write_times + read_times) * 1000, 3),
        }
        
        if options.get('json'):
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("=== 성능 테스트 결과 ==="))
            self.stdout.write(f"반복 횟수: {results['iterations']}")
            self.stdout.write(f"평균 쓰기 시간: {results['average_write_time_ms']}ms")
            self.stdout.write(f"평균 읽기 시간: {results['average_read_time_ms']}ms")
            self.stdout.write(f"총 소요 시간: {results['total_time_ms']}ms")
    
    def invalidate_cache(self, options):
        """캐시 무효화"""
        pattern = options.get('pattern')
        
        if not pattern:
            raise CommandError("--pattern 인자가 필요합니다")
        
        count = cache_manager.delete_pattern(pattern)
        self.stdout.write(
            self.style.SUCCESS(f"패턴 '{pattern}'에 매치되는 {count}개 캐시 키 무효화 완료")
        )
    
    # 워밍업 헬퍼 메소드들
    def _warm_up_user_data(self):
        """사용자 데이터 워밍업"""
        from django.contrib.auth import get_user_model
        from dn_solution.cache_utils import cache_user_data
        
        User = get_user_model()
        active_users = User.objects.filter(is_active=True)[:50]  # 최근 50명
        
        for user in active_users:
            cache_user_data(user.id)
        
        self.stdout.write(f"사용자 데이터 {len(active_users)}개 워밍업 완료")
    
    def _warm_up_company_data(self):
        """회사 데이터 워밍업"""
        try:
            from companies.models import Company
            from dn_solution.cache_utils import cache_company_hierarchy
            
            active_companies = Company.objects.filter(status=True)[:20]
            
            for company in active_companies:
                cache_company_hierarchy(company.id)
            
            self.stdout.write(f"회사 데이터 {len(active_companies)}개 워밍업 완료")
        except ImportError:
            self.stdout.write("회사 모델을 찾을 수 없어 건너뜁니다.")
    
    def _warm_up_policy_data(self):
        """정책 데이터 워밍업"""
        try:
            from dn_solution.cache_utils import cache_policy_rules
            
            # 모든 활성 정책 규칙 캐싱
            cache_policy_rules()
            
            self.stdout.write("정책 데이터 워밍업 완료")
        except ImportError:
            self.stdout.write("정책 모델을 찾을 수 없어 건너뜁니다.")
    
    def _warm_up_system_settings(self):
        """시스템 설정 워밍업"""
        # 자주 사용되는 시스템 설정들을 캐시
        system_settings = {
            'app_version': '2.0.0',
            'maintenance_mode': False,
            'max_upload_size': 10 * 1024 * 1024,  # 10MB
            'session_timeout': 3600,
        }
        
        for key, value in system_settings.items():
            cache_key = f"system_setting:{key}"
            cache_manager.set(cache_key, value, 3600)  # 1시간
        
        self.stdout.write(f"시스템 설정 {len(system_settings)}개 워밍업 완료")
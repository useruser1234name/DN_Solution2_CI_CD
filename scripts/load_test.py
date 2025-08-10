#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load Test Script - DN_SOLUTION2 리모델링
성능 테스트 및 부하 테스트 스크립트
"""

import asyncio
import aiohttp
import time
import json
import argparse
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """테스트 결과 데이터 클래스"""
    url: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: str = None


class LoadTester:
    """부하 테스트 클래스"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def login(self, username: str = "admin", password: str = "admin123") -> bool:
        """로그인 및 토큰 획득"""
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            async with self.session.post(
                f"{self.base_url}/api/auth/login/",
                json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get('access')
                    logger.info(f"로그인 성공: {username}")
                    return True
                else:
                    logger.error(f"로그인 실패: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            return False
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, use_auth: bool = True) -> TestResult:
        """HTTP 요청 실행"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if use_auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        start_time = time.time()
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                
                return TestResult(
                    url=url,
                    method=method,
                    status_code=response.status,
                    response_time=response_time,
                    success=200 <= response.status < 400
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                url=url,
                method=method,
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e)
            )
    
    async def test_endpoints(self, endpoints: List[Dict], concurrent_users: int = 10, requests_per_user: int = 10) -> List[TestResult]:
        """엔드포인트 부하 테스트"""
        logger.info(f"부하 테스트 시작: {concurrent_users}명 동시 사용자, 사용자당 {requests_per_user}개 요청")
        
        tasks = []
        
        for user_id in range(concurrent_users):
            for request_id in range(requests_per_user):
                for endpoint_config in endpoints:
                    task = self.make_request(
                        method=endpoint_config['method'],
                        endpoint=endpoint_config['url'],
                        data=endpoint_config.get('data'),
                        use_auth=endpoint_config.get('auth', True)
                    )
                    tasks.append(task)
        
        # 모든 요청을 동시에 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리된 결과들을 TestResult로 변환
        processed_results = []
        for result in results:
            if isinstance(result, TestResult):
                processed_results.append(result)
            elif isinstance(result, Exception):
                processed_results.append(TestResult(
                    url="error",
                    method="error", 
                    status_code=0,
                    response_time=0,
                    success=False,
                    error=str(result)
                ))
        
        return processed_results
    
    def analyze_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """테스트 결과 분석"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        response_times = [r.response_time for r in successful_results]
        
        total_requests = len(results)
        successful_requests = len(successful_results)
        failed_requests = len(failed_results)
        
        analysis = {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'response_times': {
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'mean': statistics.mean(response_times) if response_times else 0,
                'median': statistics.median(response_times) if response_times else 0,
                'p95': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
                'p99': statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0,
            },
            'status_codes': {},
            'errors': []
        }
        
        # 상태 코드별 집계
        for result in results:
            status = result.status_code
            if status not in analysis['status_codes']:
                analysis['status_codes'][status] = 0
            analysis['status_codes'][status] += 1
        
        # 오류 집계 (최대 10개만)
        for result in failed_results[:10]:
            analysis['errors'].append({
                'url': result.url,
                'method': result.method,
                'status_code': result.status_code,
                'error': result.error
            })
        
        return analysis


def print_results(analysis: Dict[str, Any]):
    """테스트 결과 출력"""
    print("\n" + "="*60)
    print("부하 테스트 결과")
    print("="*60)
    
    print(f"총 요청 수: {analysis['total_requests']}")
    print(f"성공한 요청: {analysis['successful_requests']}")
    print(f"실패한 요청: {analysis['failed_requests']}")
    print(f"성공률: {analysis['success_rate']:.2f}%")
    
    print("\n응답 시간 통계 (초):")
    rt = analysis['response_times']
    print(f"  최소: {rt['min']:.4f}")
    print(f"  최대: {rt['max']:.4f}")
    print(f"  평균: {rt['mean']:.4f}")
    print(f"  중간값: {rt['median']:.4f}")
    print(f"  95 퍼센타일: {rt['p95']:.4f}")
    print(f"  99 퍼센타일: {rt['p99']:.4f}")
    
    print("\n상태 코드별 집계:")
    for status_code, count in sorted(analysis['status_codes'].items()):
        print(f"  {status_code}: {count}개")
    
    if analysis['errors']:
        print("\n오류 샘플:")
        for error in analysis['errors']:
            print(f"  {error['method']} {error['url']}: {error['status_code']} - {error['error']}")


async def run_cache_test():
    """캐시 성능 테스트"""
    print("\n캐시 성능 테스트 실행 중...")
    
    cache_endpoints = [
        {'method': 'GET', 'url': '/api/health/cache/', 'auth': False},
        {'method': 'GET', 'url': '/api/admin/cache/status/', 'auth': True},
        {'method': 'GET', 'url': '/api/admin/cache/performance/?iterations=10', 'auth': True},
    ]
    
    async with LoadTester() as tester:
        if await tester.login():
            results = await tester.test_endpoints(
                endpoints=cache_endpoints,
                concurrent_users=5,
                requests_per_user=5
            )
            
            analysis = tester.analyze_results(results)
            print_results(analysis)


async def run_auth_test():
    """인증 성능 테스트"""
    print("\n인증 시스템 테스트 실행 중...")
    
    auth_endpoints = [
        {
            'method': 'POST', 
            'url': '/api/auth/login/', 
            'auth': False,
            'data': {'username': 'admin', 'password': 'admin123'}
        },
        {'method': 'GET', 'url': '/api/auth/token-info/', 'auth': True},
    ]
    
    async with LoadTester() as tester:
        if await tester.login():
            results = await tester.test_endpoints(
                endpoints=auth_endpoints,
                concurrent_users=10,
                requests_per_user=3
            )
            
            analysis = tester.analyze_results(results)
            print_results(analysis)


async def run_full_test(concurrent_users: int = 50, requests_per_user: int = 10):
    """전체 시스템 부하 테스트"""
    print(f"\n전체 시스템 부하 테스트 실행 중... ({concurrent_users}명 동시 사용자)")
    
    endpoints = [
        # 헬스체크
        {'method': 'GET', 'url': '/api/health/cache/', 'auth': False},
        
        # 인증
        {'method': 'GET', 'url': '/api/auth/token-info/', 'auth': True},
        
        # 대시보드 (캐시된 데이터)
        {'method': 'GET', 'url': '/api/dashboard/stats/', 'auth': True},
        {'method': 'GET', 'url': '/api/dashboard/activities/', 'auth': True},
        
        # 캐시 관리 (관리자 전용)
        {'method': 'GET', 'url': '/api/admin/cache/status/', 'auth': True},
    ]
    
    async with LoadTester() as tester:
        if await tester.login():
            start_time = time.time()
            
            results = await tester.test_endpoints(
                endpoints=endpoints,
                concurrent_users=concurrent_users,
                requests_per_user=requests_per_user
            )
            
            total_time = time.time() - start_time
            analysis = tester.analyze_results(results)
            
            # RPS 계산
            rps = analysis['total_requests'] / total_time if total_time > 0 else 0
            
            print_results(analysis)
            print(f"\n전체 테스트 시간: {total_time:.2f}초")
            print(f"평균 RPS (초당 요청 수): {rps:.2f}")
            
            # 목표 달성 여부
            print(f"\n목표 달성 여부:")
            print(f"  목표 RPS (1,000): {'✅ 달성' if rps >= 1000 else '❌ 미달성'}")
            print(f"  목표 성공률 (95%): {'✅ 달성' if analysis['success_rate'] >= 95 else '❌ 미달성'}")
            print(f"  목표 응답시간 (<100ms): {'✅ 달성' if analysis['response_times']['mean'] < 0.1 else '❌ 미달성'}")


async def run_stress_test():
    """스트레스 테스트 (점진적 부하 증가)"""
    print("\n스트레스 테스트 실행 중...")
    
    user_levels = [10, 25, 50, 100, 200]
    
    for users in user_levels:
        print(f"\n--- {users}명 동시 사용자 테스트 ---")
        
        async with LoadTester() as tester:
            if await tester.login():
                endpoints = [
                    {'method': 'GET', 'url': '/api/health/cache/', 'auth': False},
                    {'method': 'GET', 'url': '/api/dashboard/stats/', 'auth': True},
                ]
                
                start_time = time.time()
                results = await tester.test_endpoints(
                    endpoints=endpoints,
                    concurrent_users=users,
                    requests_per_user=5
                )
                
                total_time = time.time() - start_time
                analysis = tester.analyze_results(results)
                rps = analysis['total_requests'] / total_time if total_time > 0 else 0
                
                print(f"RPS: {rps:.2f}, 성공률: {analysis['success_rate']:.1f}%, "
                      f"평균 응답시간: {analysis['response_times']['mean']*1000:.1f}ms")
                
                # 성능 임계점 확인
                if analysis['success_rate'] < 95 or analysis['response_times']['mean'] > 1.0:
                    print(f"⚠️  성능 임계점 도달: {users}명에서 성능 저하 감지")
                    break


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='DN_SOLUTION2 부하 테스트')
    parser.add_argument('--test-type', choices=['cache', 'auth', 'full', 'stress'], 
                       default='full', help='테스트 유형 선택')
    parser.add_argument('--users', type=int, default=50, help='동시 사용자 수')
    parser.add_argument('--requests', type=int, default=10, help='사용자당 요청 수')
    parser.add_argument('--base-url', default='http://localhost:8000', help='테스트 대상 URL')
    
    args = parser.parse_args()
    
    print(f"DN_SOLUTION2 부하 테스트 도구")
    print(f"테스트 대상: {args.base_url}")
    print(f"테스트 유형: {args.test_type}")
    
    # 비동기 테스트 실행
    if args.test_type == 'cache':
        asyncio.run(run_cache_test())
    elif args.test_type == 'auth':
        asyncio.run(run_auth_test())
    elif args.test_type == 'full':
        asyncio.run(run_full_test(args.users, args.requests))
    elif args.test_type == 'stress':
        asyncio.run(run_stress_test())


if __name__ == '__main__':
    main()
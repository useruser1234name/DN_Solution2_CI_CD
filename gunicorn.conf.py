# Gunicorn 설정 파일
# HB Admin - B2B 플랫폼 백엔드

import multiprocessing
import os

# =============================================================================
# 서버 설정
# =============================================================================

# 바인딩할 주소와 포트
bind = os.getenv('GUNICORN_BIND', '127.0.0.1:8000')

# 워커 프로세스 수 (CPU 코어 수 * 2 + 1)
workers = os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)

# 워커 클래스
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')

# 워커당 최대 연결 수
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', 1000))

# =============================================================================
# 타임아웃 설정
# =============================================================================

# 요청 타임아웃 (초)
timeout = int(os.getenv('GUNICORN_TIMEOUT', 30))

# 워커 부팅 타임아웃 (초)
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', 30))

# keep-alive 연결 타임아웃 (초)
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 2))

# =============================================================================
# 성능 최적화
# =============================================================================

# 워커당 최대 요청 수 (메모리 누수 방지)
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))

# 워커 재시작 시 랜덤 지터 (동시 재시작 방지)
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 100))

# 애플리케이션 사전 로드 (성능 향상)
preload_app = os.getenv('GUNICORN_PRELOAD_APP', 'true').lower() == 'true'

# =============================================================================
# 로깅 설정
# =============================================================================

# 로그 레벨
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')

# 액세스 로그 파일
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')  # '-'는 stdout

# 에러 로그 파일
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')  # '-'는 stdout

# 로그 포맷
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# =============================================================================
# 보안 설정
# =============================================================================

# 사용자 (root가 아닌 사용자로 실행)
user = os.getenv('GUNICORN_USER', None)
group = os.getenv('GUNICORN_GROUP', None)

# 임시 디렉토리
tmp_upload_dir = os.getenv('GUNICORN_TMP_UPLOAD_DIR', None)

# =============================================================================
# 프로세스 관리
# =============================================================================

# 데몬 모드 (백그라운드 실행)
daemon = os.getenv('GUNICORN_DAEMON', 'false').lower() == 'true'

# PID 파일
pidfile = os.getenv('GUNICORN_PIDFILE', None)

# 워커 재시작 시 지연 시간 (초)
worker_tmp_dir = os.getenv('GUNICORN_WORKER_TMP_DIR', '/dev/shm')

# =============================================================================
# SSL 설정 (필요시)
# =============================================================================

# SSL 인증서 파일
keyfile = os.getenv('GUNICORN_KEYFILE', None)
certfile = os.getenv('GUNICORN_CERTFILE', None)

# =============================================================================
# 환경별 설정
# =============================================================================

# 개발 환경 설정
if os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('settings'):
    # 개발 환경에서는 단일 워커 사용
    workers = 1
    reload = True
    reload_extra_files = [
        'dn_solution/settings.py',
        'companies/',
        'policies/',
        'orders/',
        'inventory/',
        'messaging/',
    ]

# 운영 환경 설정
if os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('settings_production'):
    # 운영 환경에서는 보안 강화
    limit_request_line = 4094
    limit_request_fields = 100
    limit_request_field_size = 8190

# =============================================================================
# 모니터링 및 디버깅
# =============================================================================

# 상태 체크 엔드포인트
def when_ready(server):
    server.log.info("Gunicorn 서버가 준비되었습니다.")

def worker_int(worker):
    worker.log.info("워커가 인터럽트를 받았습니다.")

def pre_fork(server, worker):
    server.log.info("워커 포크 전")

def post_fork(server, worker):
    server.log.info("워커 포크 후")

def post_worker_init(worker):
    worker.log.info("워커 초기화 완료")

def worker_abort(worker):
    worker.log.info("워커가 비정상 종료되었습니다.")

# =============================================================================
# 설정 검증
# =============================================================================

def validate_config():
    """설정 유효성 검사"""
    if workers < 1:
        raise ValueError("workers는 1 이상이어야 합니다.")
    
    if timeout < 1:
        raise ValueError("timeout은 1초 이상이어야 합니다.")
    
    if max_requests < 1:
        raise ValueError("max_requests는 1 이상이어야 합니다.")

# 설정 검증 실행
validate_config() 
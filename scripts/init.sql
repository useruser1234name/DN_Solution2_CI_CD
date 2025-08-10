-- PostgreSQL 초기화 스크립트 - DN_SOLUTION2
-- 데이터베이스 초기 설정 및 최적화

-- 확장 프로그램 설치
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 성능 최적화 설정
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- 로깅 설정
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1초 이상 쿼리 로깅
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- 한국 시간대 설정
ALTER SYSTEM SET timezone = 'Asia/Seoul';

-- 연결 설정
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET max_prepared_transactions = 0;

-- 스키마별 권한 설정 (향후 확장용)
-- CREATE SCHEMA IF NOT EXISTS policy;
-- CREATE SCHEMA IF NOT EXISTS orders; 
-- CREATE SCHEMA IF NOT EXISTS rebates;
-- CREATE SCHEMA IF NOT EXISTS reports;

-- 인덱스 최적화를 위한 통계 수집
-- ANALYZE;

SELECT 'PostgreSQL 초기화 완료' as status;
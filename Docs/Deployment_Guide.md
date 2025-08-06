# 배포 가이드 (Deployment Guide)

HB Admin - B2B 플랫폼 백엔드 배포 가이드

## 📋 목차

1. [환경별 요구사항](#환경별-요구사항)
2. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
3. [운영 환경 배포](#운영-환경-배포)
4. [클라우드 배포](#클라우드-배포)
5. [보안 설정](#보안-설정)
6. [모니터링 및 로깅](#모니터링-및-로깅)
7. [문제 해결](#문제-해결)

## 🎯 환경별 요구사항

### 개발 환경
- **Python**: 3.11+
- **데이터베이스**: SQLite (기본)
- **캐시**: 메모리 캐시
- **웹 서버**: Django 개발 서버
- **정적 파일**: Django 개발 서버

### 운영 환경
- **Python**: 3.11+
- **데이터베이스**: PostgreSQL (권장)
- **캐시**: Redis
- **웹 서버**: Gunicorn + Nginx
- **정적 파일**: WhiteNoise 또는 CDN

## 🛠️ 로컬 개발 환경 설정

### 1. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate
```

### 2. 개발 패키지 설치

```bash
# 개발 환경 패키지 설치
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```env
# Django 설정
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스 설정 (개발용 SQLite)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# CORS 설정
CORS_ALLOW_ALL_ORIGINS=True

# 로깅 설정
LOG_LEVEL=DEBUG
```

### 4. 데이터베이스 초기화

```bash
# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser

# 초기 데이터 생성 (선택사항)
python manage.py create_initial_admin
```

### 5. 개발 서버 실행

```bash
# Django 개발 서버 실행
python manage.py runserver

# 프론트엔드 개발 서버 실행 (별도 터미널)
cd frontend
npm start
```

## 🚀 운영 환경 배포

### 1. 서버 준비

#### Ubuntu/Debian 서버 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 설치
sudo apt install python3 python3-pip python3-venv -y

# PostgreSQL 설치
sudo apt install postgresql postgresql-contrib -y

# Redis 설치
sudo apt install redis-server -y

# Nginx 설치
sudo apt install nginx -y

# Git 설치
sudo apt install git -y
```

### 2. 프로젝트 배포

```bash
# 프로젝트 디렉토리 생성
sudo mkdir -p /var/www/dn_solution
sudo chown $USER:$USER /var/www/dn_solution

# 프로젝트 클론
cd /var/www/dn_solution
git clone <your-repository-url> .

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 운영 환경 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```env
# Django 설정
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# 데이터베이스 설정
DB_ENGINE=django.db.backends.postgresql
DB_NAME=dn_solution
DB_USER=dn_solution_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis 설정
REDIS_URL=redis://127.0.0.1:6379/1

# 이메일 설정
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# CORS 설정
FRONTEND_URL=https://yourdomain.com

# 보안 설정
SECURE_SSL_REDIRECT=True
```

### 4. 데이터베이스 설정

```bash
# PostgreSQL 사용자 생성
sudo -u postgres psql

CREATE DATABASE dn_solution;
CREATE USER dn_solution_user WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE dn_solution TO dn_solution_user;
\q
```

### 5. Django 설정

```bash
# 운영 환경 설정 사용
export DJANGO_SETTINGS_MODULE=dn_solution.settings_production

# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic --noinput

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 6. Gunicorn 설정

`gunicorn.conf.py` 파일 생성:

```python
# Gunicorn 설정
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### 7. Systemd 서비스 설정

`/etc/systemd/system/dn_solution.service` 파일 생성:

```ini
[Unit]
Description=DN Solution Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/dn_solution
Environment="PATH=/var/www/dn_solution/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=dn_solution.settings_production"
ExecStart=/var/www/dn_solution/venv/bin/gunicorn --config gunicorn.conf.py dn_solution.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

### 8. Nginx 설정

`/etc/nginx/sites-available/dn_solution` 파일 생성:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL 인증서 설정
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # SSL 보안 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # 정적 파일 서빙
    location /static/ {
        alias /var/www/dn_solution/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 미디어 파일 서빙
    location /media/ {
        alias /var/www/dn_solution/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Django 애플리케이션 프록시
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### 9. 서비스 시작

```bash
# Nginx 설정 활성화
sudo ln -s /etc/nginx/sites-available/dn_solution /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Django 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable dn_solution
sudo systemctl start dn_solution
sudo systemctl status dn_solution
```

## ☁️ 클라우드 배포

### AWS 배포

#### 1. EC2 인스턴스 설정

```bash
# EC2 인스턴스에 연결
ssh -i your-key.pem ubuntu@your-ec2-ip

# 위의 "운영 환경 배포" 단계를 따라 설정
```

#### 2. RDS PostgreSQL 설정

```bash
# RDS 인스턴스 생성 후 연결 정보를 .env 파일에 설정
DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
DB_PORT=5432
DB_NAME=dn_solution
DB_USER=dn_solution_user
DB_PASSWORD=your-secure-password
```

#### 3. ElastiCache Redis 설정

```bash
# ElastiCache Redis 클러스터 생성 후 연결 정보를 .env 파일에 설정
REDIS_URL=redis://your-redis-endpoint.region.cache.amazonaws.com:6379/1
```

### Docker 배포

#### 1. Dockerfile 생성

```dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# 포트 노출
EXPOSE 8000

# 실행 명령
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "dn_solution.wsgi:application"]
```

#### 2. Docker Compose 설정

`docker-compose.yml` 파일 생성:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=dn_solution.settings_production
    env_file:
      - .env
    depends_on:
      - db
      - redis
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=dn_solution
      - POSTGRES_USER=dn_solution_user
      - POSTGRES_PASSWORD=your-secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
```

## 🔒 보안 설정

### 1. 환경 변수 보안

```bash
# 민감한 정보는 환경 변수로 관리
export SECRET_KEY="your-very-secure-secret-key"
export DB_PASSWORD="your-secure-database-password"
```

### 2. 방화벽 설정

```bash
# UFW 방화벽 설정
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. SSL 인증서 설정

```bash
# Let's Encrypt SSL 인증서 설치
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 4. 보안 헤더 설정

Nginx 설정에 보안 헤더 추가:

```nginx
# 보안 헤더 추가
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

## 📊 모니터링 및 로깅

### 1. 로그 모니터링

```bash
# Django 로그 확인
tail -f /var/www/dn_solution/logs/django.log

# Nginx 로그 확인
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 시스템 로그 확인
journalctl -u dn_solution -f
```

### 2. 성능 모니터링

```bash
# 시스템 리소스 모니터링
htop
df -h
free -h

# 네트워크 연결 확인
netstat -tulpn
```

### 3. Sentry 에러 추적 설정

```bash
# Sentry DSN을 환경 변수에 설정
export SENTRY_DSN="https://your-sentry-dsn@sentry.io/project-id"
```

## 🔧 문제 해결

### 1. 일반적인 문제들

#### 데이터베이스 연결 오류
```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 데이터베이스 연결 테스트
psql -h localhost -U dn_solution_user -d dn_solution
```

#### 정적 파일 404 오류
```bash
# 정적 파일 수집 재실행
python manage.py collectstatic --noinput --clear

# 정적 파일 권한 확인
sudo chown -R www-data:www-data /var/www/dn_solution/staticfiles
```

#### 권한 오류
```bash
# 파일 권한 설정
sudo chown -R www-data:www-data /var/www/dn_solution
sudo chmod -R 755 /var/www/dn_solution
```

### 2. 로그 분석

```bash
# Django 에러 로그 확인
grep -i error /var/www/dn_solution/logs/django.log

# Nginx 에러 로그 확인
grep -i error /var/log/nginx/error.log
```

### 3. 서비스 재시작

```bash
# Django 서비스 재시작
sudo systemctl restart dn_solution

# Nginx 재시작
sudo systemctl restart nginx

# Redis 재시작
sudo systemctl restart redis
```

## 📝 체크리스트

### 배포 전 체크리스트
- [ ] 환경 변수 설정 완료
- [ ] 데이터베이스 마이그레이션 완료
- [ ] 정적 파일 수집 완료
- [ ] SSL 인증서 설정 완료
- [ ] 방화벽 설정 완료
- [ ] 로그 디렉토리 권한 설정 완료

### 배포 후 체크리스트
- [ ] 웹사이트 접속 확인
- [ ] API 엔드포인트 동작 확인
- [ ] 로그인 기능 확인
- [ ] 정적 파일 로딩 확인
- [ ] SSL 인증서 동작 확인
- [ ] 로그 파일 생성 확인

## 📞 지원

배포 과정에서 문제가 발생하면 다음을 확인하세요:

1. 로그 파일 확인
2. 환경 변수 설정 확인
3. 서비스 상태 확인
4. 네트워크 연결 확인
5. 파일 권한 확인

추가 지원이 필요한 경우 프로젝트 이슈를 생성하거나 문서를 참조하세요. 
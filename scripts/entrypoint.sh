#!/bin/sh
set -e
# 필요한 초기화 작업 수행
python manage.py migrate --noinput || true
python manage.py collectstatic --noinput || true
exec "$@"

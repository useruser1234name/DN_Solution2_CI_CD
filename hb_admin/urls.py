# hb_admin/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)

urlpatterns = [
    # Django Admin 페이지
    path('admin/', admin.site.urls),
    
    # API 엔드포인트들
    path('api/companies/', include('companies.urls')),
    path('api/policies/', include('policies.urls')),
    path('api/orders/', include('orders.urls')),
]

# 개발 환경에서 미디어 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    logger.info("개발 환경에서 정적 파일 및 미디어 파일 서빙 활성화")

# 관리자 사이트 제목 설정
admin.site.site_header = "HB Admin 관리자"
admin.site.site_title = "HB Admin"
admin.site.index_title = "HB Admin 대시보드"

logger.info("메인 URL 설정이 성공적으로 로드되었습니다")
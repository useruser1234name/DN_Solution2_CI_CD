# policies/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger('policies')


class PoliciesConfig(AppConfig):
    """
    Policies 앱 설정 클래스
    정책 관리 기능의 앱 구성을 담당
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'policies'
    verbose_name = '정책 관리'
    
    def ready(self):
        """
        앱이 준비되었을 때 실행되는 메서드
        시그널 등록이나 초기화 작업 수행
        """
        try:
            # 시그널 등록 (필요한 경우)
            # import policies.signals
            logger.info("Policies 앱이 성공적으로 초기화되었습니다")
        except Exception as e:
            logger.error(f"Policies 앱 초기화 중 오류 발생: {str(e)}")
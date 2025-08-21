from django.apps import AppConfig


class PoliciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'policies'
    
    def ready(self):
        """앱이 준비되면 시그널 등록"""
        import policies.signals  # noqa
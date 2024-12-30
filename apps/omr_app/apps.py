# apps/omr_app/apps.py
from django.apps import AppConfig

class OmrAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.omr_app' # 물리적인 파이썬 경로(점으로 구분)
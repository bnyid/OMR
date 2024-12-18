from django.apps import AppConfig
import atexit
import signal
import sys

class OmrAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'omr_app'

    def ready(self):
        # 여기서 임포트
        from .services.hwp_service import HwpProcessManager
        
        # 서버 종료 시 HWP 프로세스 정리
        atexit.register(HwpProcessManager.kill_hwp_processes)
        
        def signal_handler(signum, frame):
            HwpProcessManager.kill_hwp_processes()
            sys.exit(0)

        # SIGINT, SIGTERM 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
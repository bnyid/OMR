# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # (1) 루트("/") 로 들어왔을 때, "student_app:student_list" 이름공간으로 리다이렉트
    path('', lambda request: redirect('student_app:student_list'), name='root'),
    
    # (2) "/student/" 로 들어오는 경로 => student_app.urls
    path('student/', include('apps.student_app.urls', namespace='student_app')),
    
    # 예: omr_app URL 연결
    path('omr/', include('apps.omr_app.urls', namespace='omr_app')),
    
    # 예: exam_app URL 연결
    path('exam-sheet/', include('apps.exam_app.urls', namespace='exam_app')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
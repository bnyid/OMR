# exam_app/urls.py
from django.urls import path
from . import views

app_name = 'exam_app'

urlpatterns = [
    path('upload/', views.upload_exam_sheet, name='upload_exam_sheet'),
    path('upload-exam/', views.upload_exam, name='upload_exam'),
    path('finalize/', views.finalize_exam, name='finalize_exam'),
    
    # 기타 필요 뷰들...
]

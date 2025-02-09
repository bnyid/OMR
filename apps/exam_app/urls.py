# exam_app/urls.py
from django.urls import path
from apps.exam_app import views

app_name = 'exam_app'

urlpatterns = [
    path('upload/', views.upload_exam_sheet, name='upload_exam_sheet'),
    path('upload-exam/', views.upload_exam, name='upload_exam'),
    path('finalize/', views.finalize_exam, name='finalize_exam'),
    path('exam_sheet_list/', views.exam_sheet_list, name='exam_sheet_list'),
    path('exam_sheet_detail/<int:pk>/', views.exam_sheet_detail, name='exam_sheet_detail'),
    path('exam_sheet_bulk_delete/', views.exam_sheet_bulk_delete, name='exam_sheet_bulk_delete'),
    path('api/exam_sheets/', views.api_exam_sheets, name='api_exam_sheets'),
    # 기타 필요 뷰들...
]






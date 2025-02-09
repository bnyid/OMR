# apps/omr_app/urls.py
from django.urls import path
from . import views  # omr_app/views.py 임포트

app_name = 'omr_app'

urlpatterns = [
    # OMR 관련
    path('', views.omr_result_list, name='omr_result_list'),
    path('new/', views.show_omr_upload_page, name='omr_upload'),
    path('analyze/', views.omr_process, name='omr_process'),
    path('finalize/', views.finalize, name='finalize'),
    path('<int:result_id>/', views.omr_result_detail, name='omr_result_detail'),
    path('bulk-delete/', views.bulk_omr_delete, name='bulk_omr_delete'),
    
    # 업로드 전 앞,뒷면 이미지 확인
    path('get_essay_images/', views.get_essay_images, name='get_essay_images'),
    path('get-temp-front-image/', views.get_temp_front_image, name='get_temp_front_image'),
    
    # 시험별 답안지 페이지
    path('answer-sheets/', views.omr_answer_sheet_list, name='omr_answer_sheet_list'),
    path('answer-sheets/<str:exam_identifier>/', views.omr_result_grouped_detail, name='omr_result_detail_grouped'),
    
    
    path('match_and_auto_grade/', views.match_and_auto_grade, name='match_and_auto_grade'),
    path('fetch_essay_data/', views.fetch_essay_data, name='fetch_essay_data'),
    
    # 채점 목록
    path('grading_list/', views.omr_grading_list, name='omr_grading_list'),
    path('grading/<str:exam_identifier>/', views.omr_grading_detail, name='omr_grading_detail'),
    path('grade_essay/', views.grade_essay_update, name='grade_essay_update'),

    path('omr-result-detail/<int:result_id>/', views.omr_result_detail, name='omr_result_detail'),
]




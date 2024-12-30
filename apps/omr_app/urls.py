# omr_app/urls.py
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

    # 시험별 답안지 페이지
    path('answer-sheets/', views.omr_answer_sheet_list, name='omr_answer_sheet_list'),
    path('answer-sheets/<str:exam_identifier>/', views.omr_result_grouped_detail, name='omr_result_detail_grouped'),
]








'''
urlpatterns = [
    # 학생 관련 엔드포인트
    path('', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/update/', views.student_update, name='student_update'),
    path('students/search/', views.student_search, name='student_search'),
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    path('students/inactive/', views.inactive_student_list, name='inactive_student_list'),
    
    
    # OMR 관련 엔드포인트
    path('omr/', views.omr_result_list, name='omr_result_list'),
    path('omr/new/', views.show_omr_upload_page, name='omr_upload'),
    path('omr/analyze/', views.omr_process, name='omr_process'),
    path('omr/finalize/', views.finalize, name='finalize'),
    path('omr/<int:result_id>/', views.omr_result_detail, name='omr_result_detail'),
    path('omr/bulk-delete/', views.bulk_omr_delete, name='bulk_omr_delete'),

    # 시험별 답안지 리스트 페이지
    path('omr/answer-sheets/', views.omr_answer_sheet_list, name='omr_answer_sheet_list'),
    # 시험별 답안지 상세 페이지
    path('omr/answer-sheets/<str:exam_identifier>/', views.omr_result_grouped_detail, name='omr_result_detail_grouped'),
    
    
    
     # 시험지 업로드 페이지
    path('exam-sheet/upload/', views.upload_exam_sheet, name='upload_exam_sheet'),
    path('exam-sheet/upload-exam/', views.upload_exam, name='upload_exam'),
    path('exam-sheet/finalize/', views.finalize_exam, name='finalize_exam'),  # finalize_exam 엔드포인트 추가

    
    # 시험지 생성 처리 (추후 구현)
    #path('exam-sheet/upload/create_exam_sheet/', views.create_exam_sheet, name='create_exam_sheet'),
    

] 
'''
# student_app/urls.py
from django.urls import path
from . import views  # student_app/views.py 임포트

app_name = 'student_app'  # namespace로 사용될 문자열(중복 방지)

urlpatterns = [
    # 예: 학생 목록 / 추가 / 상세 등
    path('', views.student_list, name='student_list'),
    path('add/', views.student_add, name='student_add'),
    path('<int:student_id>/', views.student_detail, name='student_detail'),
    path('<int:student_id>/update/', views.student_update, name='student_update'),
    path('search/', views.student_search, name='student_search'),
    path('inactive/', views.inactive_student_list, name='inactive_student_list'),
    
    path('bulk-action/', views.bulk_action, name='bulk_action'),
]

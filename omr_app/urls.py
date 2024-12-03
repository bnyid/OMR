from django.urls import path
from . import views

app_name = 'omr_app'

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<str:student_id>/', views.student_detail, name='student_detail'),
    path('students/<str:student_id>/delete/', views.student_delete, name='student_delete'),
    path('omr/upload/', views.omr_upload, name='omr_upload'),
    path('omr/process/', views.omr_process, name='omr_process'),
    path('omr/results/', views.omr_result_list, name='omr_result_list'),
    path('omr/results/<int:result_id>/', views.omr_result_detail, name='omr_result_detail'),
] 
from django.contrib import admin
from .models import OMRResult, Student

@admin.register(OMRResult)
class OMRResultAdmin(admin.ModelAdmin):
    list_display = ('exam_date', 'class_code', 'student_id', 'student_name', 'created_at')
    list_filter = ('exam_date', 'class_code')
    search_fields = ('student_id', 'student_name')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'class_name', 'school_type', 'school_name', 'grade')
    list_filter = ('school_type', 'grade', 'class_name')
    search_fields = ('student_id', 'name', 'school_name')

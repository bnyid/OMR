# admin.py
from django.contrib import admin
from .models import OMRResult, Student

@admin.register(OMRResult)
class OMRResultAdmin(admin.ModelAdmin):
    list_display = ('exam_date', 'class_code', 'get_student_code', 'get_student_name', 'created_at')
    list_filter = ('exam_date', 'class_code')
    search_fields = ('student__student_code', 'student__name')

    def get_student_code(self, obj):
        return obj.student.student_code
    get_student_code.short_description = '학번'

    def get_student_name(self, obj):
        return obj.student.name
    get_student_name.short_description = '이름'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_code', 'name', 'class_name', 'school_type', 'school_name', 'grade')
    list_filter = ('school_type', 'grade', 'class_name')
    search_fields = ('student_code', 'name', 'school_name')


'''
get_student_code : 해당 모델에서 ForeignKey나 다른 관계를 통해 연결된 모델의 데이터를 가져올 수 있음 (주로 포맷팅,조건부 표시 등 용도)
student__student_code : 이것도 마찬가지 방식인데, 데이터베이스 검색, 필터링 용도로 사용함 (대충 둘이 비슷한 느낌)


'''
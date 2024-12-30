# student_app/services.py
from .models import Student

def update_students(
    selected_student_id_list, 
    new_class_name, 
    new_school_type, 
    new_school_name, 
    new_grade
):
    """
    다수의 Student 객체를 한 번에 업데이트
    """
    queryset = Student.objects.filter(id__in=selected_student_id_list)

    # 업데이트할 필드를 누적
    updates = {}
    if new_class_name:
        updates['class_name'] = new_class_name
    if new_school_type:
        updates['school_type'] = new_school_type
    if new_school_name:
        updates['school_name'] = new_school_name
    if new_grade:
        updates['grade'] = new_grade

    # 업데이트할 내용이 없다면 바로 종료
    if not updates:
        return 0

    # 실제 저장
    count = 0
    for student in queryset: # 학생들에 대하여 순회
        for field, value in updates.items(): # items()로 키-값 쌍을 순회
            setattr(student, field, value) # setattr(객체, 속성, 값) 설정하기
        student.save()  # save()로 모델 내부 로직 적용
        count += 1

    return count



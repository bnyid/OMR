from omr_app.models import Student


def update_students(selected_students, new_class_name, new_school_name, new_grade):
    queryset = Student.objects.filter(id__in=selected_students)
    # update()로 일괄 수정
    updates = {}
    if new_class_name:
        updates['class_name'] = new_class_name
    if new_school_name:
        updates['school_name'] = new_school_name
    if new_grade:
        updates['grade'] = new_grade
    
    if not updates:
        return 0

    count = 0
    for student in queryset:
        for field, value in updates.items():
            setattr(student, field, value)
        student.save()  # save() 호출로 모델 내부 로직 적용
        count += 1

    return count



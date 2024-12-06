from omr_app.models import Student

def generate_registration_number(reg_date, exclude_id=None):
    same_date_count = Student.objects.filter(registered_date=reg_date)
    if exclude_id:
        same_date_count = same_date_count.exclude(id=exclude_id)
    count = same_date_count.count()

    date_str = reg_date.replace('-', '')[2:]
    registration_number = f"{date_str}_{str(count + 1).zfill(2)}"

    # registration_number가 중복되는 지 확인
    while Student.objects.filter(registration_number=registration_number).exclude(id=exclude_id).exists():
        count += 1
        registration_number = f"{date_str}_{str(count + 1).zfill(2)}"

    return registration_number


def update_students(student_ids, class_name=None, school_name=None, grade=None):
    update_fields = {}
    if class_name:
        update_fields['class_name'] = class_name
    if school_name:
        update_fields['school_name'] = school_name
    if grade:
        update_fields['grade'] = grade

    if update_fields:
        return Student.objects.filter(id__in=student_ids).update(**update_fields) # **=딕셔너리언패킹 / Django의 QuerySet.update() 메서드는 업데이트된 행(row)의 개수를 정수(int)로 반환
    return 0
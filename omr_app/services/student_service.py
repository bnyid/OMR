from omr_app.models import Student

def generate_registration_number(reg_date, exclude_id=None):
    """
    등록일자를 입력받은 뒤, 일련번호2자리를 더해 고유한 학생 등록번호를 생성합니다.
    일련번호는 이미 존재하는 번호 중 가장 큰 번호를 찾아, 그 다음 번호를 할당합니다.
    즉, 중간에 빠진 번호를 재활용하지 않습니다.
    
    Args:
        reg_date (str): YYYY-MM-DD 형식의 등록일자
        exclude_id (int, optional): 중복 검사 시 제외할 학생 ID
    
    Returns:
        str: YYMMDD_XX 형식의 고유한 등록번호
    """
    # 해당 날짜의 학생 조회 (exclude_id 있을 경우 제외)
    students = Student.objects.filter(registered_date=reg_date) # 필터링 된게 없을경우 [] 빈 QuerySet 반환
    if exclude_id:
        students = students.exclude(id=exclude_id)

    date_str = reg_date.replace('-', '')[2:] # YYYY-MM-DD => YYMMDD

    # 이미 할당된 registration_number들 중 번호 부분을 추출
    existing_numbers = [] 
    for s in students:
        # registration_number는 YYMMDD_XX 형태
        # '_'로 split해서 두 번째 부분(XX)을 int로 변환
        if s.registration_number and '_' in s.registration_number:
            num_str = s.registration_number.split('_')[1] # _를 기준으로 두번째 부분[1] 추출
            try:
                existing_numbers.append(int(num_str))
            except ValueError:
                # 만약 parsing 불가능한 값이 있다면 무시
                pass

    # 최대 번호 찾아서 +1
    if existing_numbers:
        max_num = max(existing_numbers)
        next_num = max_num + 1
    else: # 해당 날짜에 등록된 학생이 없다면 1부터 시작
        next_num = 1

    registration_number = f"{date_str}_{str(next_num).zfill(2)}" # zfill(2) = [1 => 01] 두자리화
    
    return registration_number


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
    
    if updates:
        queryset.update(**updates)
        # 여기서 다시 queryset 가져와 save 호출
        for student in queryset:
            student.save()
        return queryset.count()
    else:
        return 0



def create_student(student_data):
    """
    학생 등록 데이터를 받아 새로운 학생 Student 모델 인스턴스를 생성합니다.

    Parameters
    ----------
    student_data : dict
        학생 정보를 담은 딕셔너리. 다음과 같은 키를 포함할 수 있습니다:
        - name (str): 학생 이름 (필수)
        - registered_date (str): 등록일자 (YYYY-MM-DD 형식)
        - school_name (str): 학교 이름 (선택)
        - grade (int): 학년 (선택)
        - class_name (str): 반 이름 (선택)
        - etc: Student 모델의 다른 필드들

    Returns
    -------
    Student: 생성된 Student 모델 인스턴스

    major features
    --------
    - 이름이 없는 경우 에러 발생
    - registered_date가 제공된 경우, registration_number('YYMMDD_XX')를 자동으로 생성됩니다.
    """
    # student_data 딕셔너리에 name은 필수
    if not student_data.get('name'):
        raise ValueError("이름은 필수 입력 항목입니다.")

    # registered_date가 제공된 경우, registration_number를 자동으로 생성
    if 'registered_date' in student_data and student_data['registered_date']: # student_data에 registered_date 키가 있음 & registered_date 값이 있음 (안전하게 이중검증)
        reg_date = student_data['registered_date']
        student_data['registration_number'] = generate_registration_number(reg_date)
    
    return Student.objects.create(**student_data)
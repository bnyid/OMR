from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import OMRResult, Student

from .omr_processors.main import process_omr_image
from .omr_processors.omr_data_processing import handle_image_file
from django.views.decorators.http import require_POST
from django.contrib import messages

def omr_upload(request):
    return render(request, 'omr_app/omr_upload.html')

@csrf_exempt
def omr_process(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            image = handle_image_file(image_file) # 이미지 파일이 pdf인 경우 BGR 이미지로 변환

            if image is None:
                return JsonResponse({'status': 'error', 'message': '이미지 변환 실패'}, status=400)

            try:
                result_df = process_omr_image(image)
            except Exception as e:
                print(f"process_omr_image 오류: {str(e)}")
                return JsonResponse({'status': 'error', 'message': f'OMR 처리 중 오류: {str(e)}'}, status=400)
            
            result = OMRResult.objects.create(
                exam_date=f"20{result_df['시행일'].iloc[0]}",
                class_code=result_df['반코드'].iloc[0],
                student_id=result_df['학번'].iloc[0],
                student_name=result_df['이름'].iloc[0],
                answer_sheet=image_file,
                answers=result_df.to_dict('records') # 전체 result_df를 딕셔너리로 변환하여 저장(시행일부터 답안까지) 
            )

            return JsonResponse({
                'status': 'success', # 성공적으로 처리되었음을 알리고
                'data': {
                    'id': result.id, # 생성된 OMRResult 객체의 id를 반환
                    'exam_date': f"20{result_df['시행일'].iloc[0]}",
                    'class_code': result_df['반코드'].iloc[0],
                    'student_id': result_df['학번'].iloc[0],
                    'student_name': result_df['이름'].iloc[0],
                    'answers': result_df.to_dict('records') # result_df를 딕셔너리로 변환하여 반환
                }
            })

        except Exception as e:
            print(f"전체 처리 오류: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)

def omr_result_list(request):
    results = OMRResult.objects.all().order_by('-exam_date', 'class_code', 'student_id')
    
    # 사용자가 페이지에 그냥 접속만 했을 경우에는 request.GET ={}로 비어 있고, 아래 3개 변수는 None으로 설정됨
    exam_date = request.GET.get('exam_date')  
    class_code = request.GET.get('class_code')
    student_name = request.GET.get('student_name')
    
    # 사용자가 검색 조건을 입력하고 검색 버튼을 눌렀을 경우에는 request.GET에 검색 조건이 담겨 있고, 아래 3개 변수는 검색 조건에 해당하는 값으로 설정됨
    if exam_date:
        results = results.filter(exam_date=exam_date)
    if class_code:
        results = results.filter(class_code=class_code)
    if student_name:
        results = results.filter(student_name__icontains=student_name)
    
    return render(request, 'omr_app/omr_result_list.html', {
        'results': results, # 전체 df를 테이블에 표시하기 위함
        'exam_dates': OMRResult.objects.dates('exam_date', 'day', order='DESC'), 
        'class_codes': OMRResult.objects.values_list('class_code', flat=True).distinct() # exam_dates와 class_code는 필터링 드롭다운 option 값으로 사용됨
    })

def omr_result_detail(request, result_id):
    result = get_object_or_404(OMRResult, id=result_id)
    return render(request, 'omr_app/omr_result_detail.html', {'result': result})



def student_list(request):
    try:
        # 기존 데이터 중 registered_date가 None이거나 잘못된 형식인 경우 처리
        students_without_date = Student.objects.all()
        print("전체 학생 수:", students_without_date.count())  # 디버깅용 출력
        
        for student in students_without_date:
            try:
                # registered_date 값이 유효한지 확인
                if student.registered_date:
                    str(student.registered_date)
            except (ValueError, TypeError):
                # 오류가 발생하면 None으로 설정
                student.registered_date = None
                student.save()
                print(f"학생 {student.student_id}의 등록일 초기화됨")  # 디버깅용 출력
        
        # 전체 학생 목록을 등록일, 학번 순으로 정렬
        students = Student.objects.all().order_by('registration_number')
        print("정렬 후 학생 수:", students.count())  # 디버깅용 출력
        
        return render(request, 'omr_app/student_list.html', {
            'students': students, # 전체 df를 테이블에 표시하기 위함
            'grades': [1, 2, 3], # 학년 드롭다운 option 값으로 사용됨
            'class_names': Student.objects.values_list('class_name', flat=True).distinct() # 반 드롭다운 option 값으로 사용됨 
        })
        
    except Exception as e:
        print(f"Error in student_list: {str(e)}")  # 디버깅용 출력
        import traceback
        print(traceback.format_exc())  # 상세 에러 메시지 출력
        # 오류가 발생해도 빈 목록이라도 보여주기
        return render(request, 'omr_app/student_list.html', {
            'students': Student.objects.none(),
            'grades': [1, 2, 3],
            'class_names': []
        })

''' class_names 설명
values_list() 모델의 특정 속성 값들을 리스트로 반환함. 
# flat=False 일 경우 (각요소가 튜플인 리스트 반환)
    # 결과: [('A반',), ('A반',), ('B반',), ('C반',), ('B반',)]
# flat=True 사용할 경우 (각 요소가 단일한 값으로 구성된 리스트 반환)
    # 결과: ['A반', 'A반', 'B반', 'C반', 'B반']

distinct() : unique()와 같은 기능 (중복된 값 제외)
'''        

    

def student_detail(request, student_code):
    student = get_object_or_404(Student, student_code=student_code)
    omr_results = OMRResult.objects.filter(student_code=student_code).order_by('-exam_date')
    
    return render(request, 'omr_app/student_detail.html', {
        'student': student,
        'omr_results': omr_results
    })

@require_POST
def student_add(request):
    if request.method == 'POST':
        try:
            # 필수 필드인 이름만 먼저 확인
            if not request.POST.get('name'):
                return JsonResponse({
                    'status': 'error',
                    'message': '이름은 필수 입력 항목입니다.'
                })
            
            # 기본 데이터 구성 (이름만 필수)
            student_data = {
                'name': request.POST['name']
            }
            
            # 선택적 필드들 처리
            optional_fields = [
                'student_id', 'class_name', 'school_type', 
                'school_name', 'grade', 'phone_number', 
                'parent_phone', 'note'
            ]
            
            # 입력된 선택적 필드만 student_data에 추가
            for field in optional_fields:
                if request.POST.get(field):
                    # grade는 정수형으로 변환 필요
                    if field == 'grade':
                        student_data[field] = int(request.POST[field])
                    else:
                        student_data[field] = request.POST[field]
            
            # 등록일이 입력된 경우 등록번호 생성
            if request.POST.get('registered_date'):
                reg_date = request.POST['registered_date']
                # 해당 날짜의 등록 건수 확인
                same_date_count = Student.objects.filter(
                    registered_date__date=reg_date
                ).count()
                
                # 등록번호 생성 (YYMMDD_XX 형식)
                date_str = reg_date.replace('-', '')[2:]
                registration_number = f"{date_str}_{str(same_date_count + 1).zfill(2)}"
                
                # 중복 확인 및 조정
                while Student.objects.filter(registration_number=registration_number).exists():
                    same_date_count += 1
                    registration_number = f"{date_str}_{str(same_date_count + 1).zfill(2)}"
                
                student_data['registration_number'] = registration_number
                student_data['registered_date'] = f"{reg_date} 00:00:00"
            
            student = Student.objects.create(**student_data)
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })


@require_POST
def student_delete(request, student_id):
    try:
        student = get_object_or_404(Student, student_id=student_id)
        student.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
def bulk_action(request):
    selected_students = request.POST.getlist('selected_students')
    action = request.POST.get('action')

    if not selected_students:
        messages.error(request, "선택된 학생이 없습니다.")
        return redirect('omr_app:student_list')

    if action == 'delete':
        Student.objects.filter(id__in=selected_students).delete()
        messages.success(request, "선택된 학생들이 삭제되었습니다.")
    elif action == 'update':
        new_class_name = request.POST.get('new_class_name')
        new_school_name = request.POST.get('new_school_name')
        new_grade = request.POST.get('new_grade')

        update_fields = {}
        if new_class_name:
            update_fields['class_name'] = new_class_name
        if new_school_name:
            update_fields['school_name'] = new_school_name
        if new_grade:
            update_fields['grade'] = new_grade

        if update_fields:
            Student.objects.filter(id__in=selected_students).update(**update_fields)
            messages.success(request, "선택된 학생들의 정보가 변경되었습니다.")
        else:
            messages.error(request, "변경할 정보를 입력하세요.")

    return redirect('omr_app:student_list')

@require_POST
def student_update(request, student_id): # url상의 <student_id> 변수를 받아오는 것임
    try:
        print("\n try문 진입")
        student = get_object_or_404(Student, id=student_id)
        
        # 업데이트할 필드들을 수집
        update_fields = {}
        fields = ['student_code', 'name', 'class_name', 'school_name', 'grade', 
                 'registered_date', 'phone_number', 'parent_phone', 'note']
        
        print("\n=== 학생 정보 업데이트 디버깅 ===")
        print(f"학생 ID: {student_id}")
        
        for field in fields:
            value = request.POST.get(field)
            current_value = getattr(student, field)
            
            # 날짜 필드의 경우 문자열 형식 통일
            if field == 'registered_date' and current_value:
                current_value = current_value.strftime('%Y-%m-%d')
            
            print(f"\n필드명: {field}")
            print(f"- POST로 전달된 값: '{value}'")
            print(f"- 현재 DB 값: '{current_value}'")
            print(f"- 값이 다른가?: {value != current_value}")
            
            # 현재 값과 다른 경우에만 업데이트 필드에 추가
            if value != current_value:
                if value == '':
                    update_fields[field] = None
                else:
                    update_fields[field] = value
        
        print("\n최종 업데이트될 필드들:")
        print(update_fields)
        print("================================\n")
        
        if update_fields:
            # registered_date가 실제로 변경된 경우에만 등록번호 처리
            if 'registered_date' in update_fields:
                if update_fields['registered_date'] is None:
                    update_fields['registration_number'] = None
                else:
                    reg_date = update_fields['registered_date']
                    same_date_count = Student.objects.filter(
                        registered_date__date=reg_date
                    ).count()
                    
                    date_str = reg_date.replace('-', '')[2:]
                    registration_number = f"{date_str}_{str(same_date_count + 1).zfill(2)}"
                    
                    while Student.objects.filter(
                        registration_number=registration_number
                    ).exclude(id=student_id).exists():
                        same_date_count += 1
                        registration_number = f"{date_str}_{str(same_date_count + 1).zfill(2)}"
                    
                    update_fields['registration_number'] = registration_number

            # 학생 정보 업데이트
            for field, value in update_fields.items():
                setattr(student, field, value)
            student.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '학생 정보가 성공적으로 수정되었습니다.'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '수정할 정보가 없습니다.'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

# Create your views here.

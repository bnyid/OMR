# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import OMRResult, Student
from django.db.models import Q, Count, Max


from .services.omr_service import process_pdf_and_extract_omr, extract_omr_data_from_image
from .services.student_service import update_students, generate_registration_number, create_student

from datetime import datetime
from django.views.decorators.http import require_POST
from django.db.models import F, Value, DateField
from django.db.models.functions import Coalesce

from pdf2image import convert_from_bytes
from django.views.decorators.http import require_POST
import json

## 시험별 답안지 상세 페이지
def omr_result_grouped_detail(request, exam_identifier):
    # exam_identifier를 키로 OMRResult들 가져오기
    results = OMRResult.objects.filter(exam_identifier=exam_identifier).order_by('-created_at')
    return render(request, 'omr_app/omr_result_grouped_detail.html', {
        'exam_identifier': exam_identifier,
        'results': results
    })



## 시험별 답안지 리스트 페이지
def omr_answer_sheet_list(request):
    # OMRResult를 exam_identifier, temp_exam_name으로 그룹화
    # annotate를 통해 해당 그룹 내 OMRResult 수(num_attendees)와 가장 최근 생성일(latest_created_at) 추출
    grouped_results = (
        OMRResult.objects
        .values('exam_identifier', 'temp_exam_name')
        .annotate(
            num_attendees=Count('id'),
            exam_sheet_matched=Max('exam_sheet_matched'), # 그룹 내 어느 한 레코드(최대값)로 표시 - 모두 동일하다고 가정
            latest_created_at=Max('created_at')
        )
        .order_by('-latest_created_at')  # 가장 최근 생성일이 위로
    )

    return render(request, 'omr_app/omr_answer_sheet_list.html', {
        'grouped_results': grouped_results
    })



@require_POST
def finalize(request):
    data = json.loads(request.body) # json 형태의 데이터를 파이썬 딕셔너리로 변환
    temp_exam_name = data.get('temp_exam_name')
    omr_list = data.get('omr_data', [])

    for omr in omr_list:
        exam_date_str = omr['exam_date'] # 'YYYY-MM-DD'
        teacher_code = omr['teacher_code']
        is_matched = omr['is_matched']
        student_code = omr['student_code']
        student_name = omr['student_name']
        answers = omr['answers']
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()

        # Student FK 매칭
        student_id = omr['student_id']
        student = None
        if is_matched:
            if student_id:
                # 수동매치된 경우 먼저 처리 (Student_id로 매칭)
                student = Student.objects.get(id=student_id)
            elif student_code:
                # 자동매치 처리 : student_code 매칭 (omr_process 에서 자동매치된 경우 student_id가 없음)
                try:
                    student = Student.objects.get(student_code=student_code)
                except Student.DoesNotExist:
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'학생DB에 없는 student_code가 omr에 입력되었습니다. {student_name}학생을 수동매칭 후 다시 시도하세요.'
                    }, status=400)

        else:
            return JsonResponse({
                'status': 'error', 
                'message': '학생과 매치되지 않은 omr이 있습니다. 매칭 후 다시 시도하세요.'
            }, status=400)
                
        OMRResult.objects.create(
            exam_date=exam_date,
            teacher_code=teacher_code,
            student=student if is_matched else None,
            is_matched=is_matched, # 여기까지 왔다면 is_matched는 항상 True
            unmatched_student_code=None,
            unmatched_student_name=None,
            answers=answers,
            temp_exam_name=temp_exam_name
        )

    return JsonResponse({'status':'success', 'redirect_url': reverse('omr_app:omr_answer_sheet_list')})


from django.db.models import Q

def student_search(request):
    q = request.GET.get('q', '')
    students = Student.objects.filter(
        Q(name__icontains=q) | Q(student_code__icontains=q)
    )[:50]
    data = []
    for st in students:
        data.append({
            'id': st.id,
            'student_code': st.student_code,
            'name': st.name,
            'class_name': st.class_name,
        })
    return JsonResponse(data, safe=False)


def show_omr_upload_page(request):
    return render(request, 'omr_app/omr_upload.html')

@csrf_exempt
def omr_process(request):
    if request.method == 'POST' and request.FILES.get('file'):
        print("omr_process 호출됨")
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name.lower() # 파일 확장자나 Content_Type으로 PDF vs Image 판별

        if file_name.endswith('.pdf'):  # PDF -> 여러 페이지가 포함될 수 있어 다르게 처리
            omr_results = process_pdf_and_extract_omr(uploaded_file)
        else: # 이미지 단일 처리
            omr_data = extract_omr_data_from_image(uploaded_file)
            omr_results = [omr_data]
            
        # 각 omr에 대해 student_code 매칭 여부 판단.
        for omr in omr_results:
            student_code = omr.get('student_code')  
            if student_code: # student_code가 있는 경우
                if Student.objects.filter(student_code=student_code).exists(): # DB 조회 성공시
                    omr['is_matched'] = True
        
        return JsonResponse({
            'status': 'success',
            'data': omr_results # 리스트 형태로 반환
        })
    
    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)


def omr_result_list(request):
    results = OMRResult.objects.all().order_by('-exam_date', 'teacher_code', 'student_id')
    
    # 사용자가 페이지에 그냥 접속만 했을 경우에는 request.GET ={}로 비어 있고, 아래 3개 변수는 None으로 설정됨
    exam_date = request.GET.get('exam_date')  
    teacher_code = request.GET.get('teacher_code')
    student_name = request.GET.get('student_name')
    
    # 사용자가 검색 조건을 입력하고 검색 버튼을 눌렀을 경우에는 request.GET에 검색 조건이 담겨 있고, 아래 3개 변수는 검색 조건에 해당하는 값으로 설정됨
    if exam_date:
        results = results.filter(exam_date=exam_date)
    if teacher_code:
        results = results.filter(teacher_code=teacher_code)
    if student_name:
        results = results.filter(student_name__icontains=student_name)
    
    return render(request, 'omr_app/omr_result_list.html', {
        'results': results, # 전체 df를 테이블에 표시하기 위함
        'exam_dates': OMRResult.objects.dates('exam_date', 'day', order='DESC'), 
        'teacher_codes': OMRResult.objects.values_list('teacher_code', flat=True).distinct() # exam_dates와 teacher_code는 필터링 드롭다운 option 값으로 사용됨
    })

def omr_result_detail(request, result_id):
    result = get_object_or_404(OMRResult, id=result_id)
    return render(request, 'omr_app/omr_result_detail.html', {'result': result})



def student_list(request):
    try:
        # 기존 데이터 중 registered_date가 None이거나 잘못된 형식인 경우 처리
        students_all = Student.objects.all()
        print("전체 학생 수:", students_all.count())  # 디버깅용 출력
        
        for student in students_all:
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
        students = Student.objects.annotate( # annotate는 기존 모델에 없는 새로운 필드를 임시로 추가함.
            sort_date=Coalesce( # Coalesce는 첫번째 인자가 None이면 두번째 인자를 반환함.
                'registered_date',
                Value('9999-12-31', output_field=DateField()) #9999-12-31은 문자열 이므로 date타입으로 바꿔서 두번째 인자로 전달함
            )
        ).order_by('sort_date', 'registration_number', 'id')
        print("정렬 후 학생 수:", students.count())  # 디버깅용 출력
        
        return render(request, 'omr_app/student_list.html', {
            'students': students, # 전체 df를 테이블에 표시하기 위함
            'grades': [1, 2, 3], # 학년 드롭다운 option 값으로 사용됨
            'schools': Student.objects.values_list('school_name', flat=True).distinct(), # 학교 드롭다운 option 값으로 사용됨
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

    

def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    omr_results = OMRResult.objects.filter(id=student_id).order_by('-exam_date')
    
    return render(request, 'omr_app/student_detail.html', {
        'student': student,
        'omr_results': omr_results
    })

@require_POST
def student_add(request):
    if request.method == 'POST':
        try:
            student_data = {'name': request.POST.get('name')}
            
            # 선택적 필드들 처리
            optional_fields = [
                'registered_date', 'student_id', 'class_name', 
                'school_type', 'school_name', 'grade', 
                'phone_number', 'parent_phone', 'note', 
            ]
            
            # 입력된 선택적 필드만 student_data에 추가
            for field in optional_fields:
                val = request.POST.get(field)
                if val:
                    # grade는 정수형으로 변환 필요
                    if field == 'grade':
                        student_data[field] = int(val)
                    else:
                        student_data[field] = val
            
            create_student(student_data)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error','message': str(e)})



@require_POST
def bulk_action(request):
    selected_students = request.POST.getlist('selected_students')
    action = request.POST.get('action')
    
    if not selected_students:
        return JsonResponse({
            'status': 'error',
            'message': "선택된 학생이 없습니다."
        })

    if action == 'delete':
        Student.objects.filter(id__in=selected_students).delete()
        return JsonResponse({'status': 'success'})
    
    elif action == 'update':
        new_class_name = request.POST.get('new_class_name')
        new_school_name = request.POST.get('new_school_name')
        new_grade = request.POST.get('new_grade')

        updated_count = update_students(selected_students, new_class_name, new_school_name, new_grade) # 업데이트 건수 반환
        if updated_count > 0:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': "변경할 정보를 입력하세요."})
    else:
        return JsonResponse({'status': 'error','message': "유효하지 않은 action입니다."})


@require_POST
def student_update(request, student_id): # url상의 <student_id> 변수를 받아오는 것임
    student = get_object_or_404(Student, id=student_id)
    fields = ['student_code', 'name', 'class_name', 'school_name', 'grade', 
                'registered_date', 'phone_number', 'parent_phone', 'note']

    update_fields = {}    

    for field in fields:
        new_val = request.POST.get(field)
        old_val = getattr(student, field)
        old_val_str = str(old_val) if old_val is not None else ''
        
        # 값이 달라진 필드에 대해서만 update_fields에 값을 업데이트
        if new_val != old_val_str:
            update_fields[field] = new_val if new_val != '' else None
    
    
    # registered_date가 업데이트 필드에 포함된 경우
    if 'registered_date' in update_fields:
        if update_fields['registered_date'] is None:
            update_fields['registration_number'] = None
        else:
            update_fields['registration_number'] = generate_registration_number(update_fields['registered_date'], exclude_id=student_id)

    # update_fields에 값이 있는 경우 학생 정보 업데이트
    if update_fields:
        for k, v in update_fields.items(): 
            setattr(student, k, v) # student 객체의 k속성에 v값을 설정함. (setattr = 객체의 속성을 동적으로 설정할 때 사용)
        student.save()
        return JsonResponse({'status': 'success','message': '학생 정보가 성공적으로 수정되었습니다.'})
    else:
        return JsonResponse({'status': 'error','message': '수정할 정보가 없습니다.'})
            

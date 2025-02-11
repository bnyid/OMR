# apps/student_app/views.py

from django.shortcuts import render, get_object_or_404
from django.db.models import Value, DateField, Q, Sum, Avg
from django.db.models.functions import Coalesce




from apps.omr_app.models import OMRResult
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.student_app.models import Student
from apps.student_app.services import update_students

from datetime import date, datetime


def student_list(request):
    try:
        # 전체 학생 목록을 등록일, 학번 순으로 정렬
        
        # 등록일이 없는 학생들을 후순위 배열하기
        students = Student.objects.filter(status='enrolled').annotate( # annotate는 기존 모델에 없는 새로운 필드(=sort_date)를 '임시'로 추가함.
            sort_date=Coalesce( # Coalesce는 첫번째 인자가 None이면 두번째 인자를 반환함. 
                'registered_date', # registered_date가 None이면
                Value('9999-12-31', output_field=DateField()) #9999-12-31를 반환, 문자열 이므로 date타입으로 바꿔서 전달함
            )
        ).order_by('sort_date', 'registration_number', 'id')
        
        # 전체 학생 리스트를 테이블에 표시하기 위해 전달
        return render(request, 'student_app/student_list.html', {
            'students': students, # 전체 df를 테이블에 표시하기 위함
            'grades': [1, 2, 3], # 학년 option 값으로 사용됨
            'schools': Student.objects.filter(status='enrolled').values_list('school_name', flat=True).distinct(), # 학교 드롭다운 option 값으로 사용됨
            'class_names': Student.objects.filter(status='enrolled').values_list('class_name', flat=True).distinct(), # 반 드롭다운 option 값으로 사용됨 
            'today': date.today() # 오늘 날짜를 표시하기 위함 
        })
        
    except Exception as e:
        print(f"Error in student_list: {str(e)}")  # 디버깅용 출력
        # 오류가 발생해도 빈 목록이라도 보여주기
        return render(request, 'student_app/student_list.html', {
            'students': Student.objects.none(),
            'error_message': "student_list 뷰 : 학생목록 로드 문제 발생"
        })


def inactive_student_list(request):
    # enrolled가 아닌 학생들(leave, dropout, graduated)을 필터링
    queryset = Student.objects.exclude(status='enrolled')
    
     # GET 파라미터로 status 필터 확인
    status_filter = request.GET.get('status', '')
    if status_filter in ['leave', 'dropout', 'graduated']:
        queryset = queryset.filter(status=status_filter)
    
    # 상태 변경일 오름차순 정렬
    # 상태변경일이 null일 수 있으므로 Coalesce를 사용하거나,
    # 아니면 null일 경우를 고려(기존 데이터가 없다면 모두 null일 수도 있음)
    # 여기서는 상태변경일이 없으면 9999-12-31 처리(가장 뒤로)

    
    queryset = queryset.annotate(
        sort_date=Coalesce('status_changed_date', Value('9999-12-31', output_field=DateField()))
    ).order_by('sort_date', 'name')

    return render(request, 'student_app/inactive_student_list.html', {
        'students': queryset
    })


''' class_names 설명
values_list() : 모델의 특정 속성 값들을 리스트로 반환함. 
# flat=False 일 경우 (각요소가 튜플인 리스트 반환)
    # 결과: [('A반',), ('A반',), ('B반',), ('C반',), ('B반',)]
# flat=True 사용할 경우 (각 요소가 단일한 값으로 구성된 리스트 반환)
    # 결과: ['A반', 'A반', 'B반', 'C반', 'B반']

distinct() : unique()와 같은 기능 (중복된 값 제외)
'''        


def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    omr_results = OMRResult.objects.filter(student=student).order_by('-exam_date')
    
    for omr in omr_results:
        same_identifier_omrs = OMRResult.objects.filter(exam_identifier=omr.exam_identifier)
        omr.average_score = same_identifier_omrs.aggregate(avg=Avg('total_score_earned'))['avg'] or 0
    # 각 OMR 결과에 대해 등수 계산
    for omr in omr_results:
        # 같은 시험을 본 OMR들을 점수 내림차순으로 정렬
        same_identifier_omrs = OMRResult.objects.filter(exam_identifier=omr.exam_identifier).order_by('-total_score_earned')
        
        # 현재 학생의 등수 계산
        rank = 1
        for other_omr in same_identifier_omrs:
            if other_omr.total_score_earned > omr.total_score_earned:
                rank += 1
        omr.rank = rank
        omr.omrs_count = same_identifier_omrs.count()
        
    return render(request, 'student_app/student_detail.html', {
        'student': student,
        'omr_results': omr_results
    })
    
        
    
    

@require_POST
def student_add(request):
    if request.method == 'POST':
        try:
            # 필수 필드 처리 (이름)
            student_data = {'name': request.POST.get('name')}
            
            # 선택적 필드 처리
            optional_fields = [
                'registered_date', 'student_id', 'student_code',
                'class_name', 'school_type', 'school_name', 'grade', 
                'phone_number', 'parent_phone', 'note', 
            ]
            
            # 값이 입력된 필드만 student_data에 추가
            for field in optional_fields:
                val = request.POST.get(field)
                if val:
                    # grade는 정수형으로 변환 필요
                    if field == 'grade':
                        student_data[field] = int(val)
                    else:
                        student_data[field] = val
            
            Student.objects.create(**student_data)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error','message': str(e)})
        
        
        
@require_POST
def bulk_action(request):
    selected_student_id_list = request.POST.getlist('selected_students')
    action = request.POST.get('action')
    
    if not selected_student_id_list:
        return JsonResponse({
            'status': 'error',
            'message': "선택된 학생이 없습니다."
        })

    if action == 'update':
        new_class_name = request.POST.get('new_class_name')   
        new_school_type = request.POST.get('new_school_type') 
        new_school_name = request.POST.get('new_school_name')
        new_grade = request.POST.get('new_grade')

        updated_count = update_students(selected_student_id_list, new_class_name, new_school_type, new_school_name, new_grade) # 업데이트 건수 반환
        if updated_count > 0:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': "변경할 정보를 입력하세요."})

    elif action == 'change_status':
        new_status = request.POST.get('new_status')
        new_status_date_str = request.POST.get('new_status_date')  # 추가
        new_status_reason = request.POST.get('new_status_reason','').strip()  # 추가
        
        if new_status not in ['leave', 'dropout', 'graduated']:
            return JsonResponse({'status': 'error', 'message': "유효한 상태가 아닙니다."})
    
        # 날짜 파싱
        if new_status_date_str:
            try:
                new_status_date = datetime.strptime(new_status_date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': "날짜 형식이 올바르지 않습니다."})
        else:
            new_status_date = date.today()
        Student.objects.filter(id__in=selected_student_id_list).update(status=new_status, status_changed_date=new_status_date, status_reason=new_status_reason)
        return JsonResponse({'status': 'success'})
    
    elif action == 're_enroll':
        # 등원 처리: status='enrolled', 상태변경일/사유 초기화
        Student.objects.filter(id__in=selected_student_id_list).update(
            status='enrolled',
            status_changed_date=None,
            status_reason=None
        )
        return JsonResponse({'status': 'success'})

    elif action == 'delete_permanently':
        # 완전 삭제
        Student.objects.filter(id__in=selected_student_id_list).delete()
        return JsonResponse({'status': 'success'})
    
    else:
        return JsonResponse({'status': 'error','message': "유효하지 않은 action입니다."})
    
    
    
@require_POST
def student_update(request, student_id): # url상의 <student_id> 변수를 받아오는 것임
    student = get_object_or_404(Student, id=student_id)
    fields = ['student_code', 'name', 'class_name', 'school_type', 'school_name', 'grade', 
                'registered_date', 'phone_number', 'parent_phone', 'note']

    update_fields = {}    

    for field in fields:
        new_val = request.POST.get(field)
        old_val = getattr(student, field)
        old_val_str = str(old_val) if old_val is not None else ''
        
        # 값이 달라진 필드에 대해서만 update_fields에 값을 업데이트
        if new_val != old_val_str:
            update_fields[field] = new_val if new_val != '' else None
    

    # update_fields에 값이 있는 경우 학생 정보 업데이트
    if update_fields:
        for k, v in update_fields.items(): 
            setattr(student, k, v) # student 객체의 k속성에 v값을 설정함. (setattr = 객체의 속성을 동적으로 설정할 때 사용)
        student.save()
        return JsonResponse({'status': 'success','message': '학생 정보가 성공적으로 수정되었습니다.'})
    else:
        return JsonResponse({'status': 'error','message': '수정할 정보가 없습니다.'})
    
    
    
    
    
    
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
            'class_name_by_school': st.class_name_by_school,
            'class_name': st.class_name,
        })
    return JsonResponse(data, safe=False)
# views.py
import json, os
from datetime import date, datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.urls import reverse

from django.conf import settings

from django.db.models import Q, Count, Max, Value, DateField
from django.db.models.functions import Coalesce

from .services.omr_service import process_pdf_and_extract_omr, extract_omr_data_from_image
from .services.student_service import update_students
from .services.hwp_service import HwpProcessManager
from .services.hwp_service_upgrade import extract_exam_sheet_data

from .models import OMRResult, Student, ExamSheet, OriginalText
from .models import (
    ExamSheet, ExamSheetQuestionMapping, 
    Question, Choice,Passage, QuestionTable, AnswerField
)




## 시험별 답안지 상세 페이지
def omr_result_grouped_detail(request, exam_identifier):
    # exam_identifier를 키로 OMRResult들 가져오기
    results = OMRResult.objects.filter(exam_identifier=exam_identifier).order_by('-created_at')
    return render(request, 'omr_app/omr_result_grouped_detail.html', {
        'exam_identifier': exam_identifier,
        'results': results
    })



def omr_answer_sheet_list(request):
    from django.db.models import Min

    unmatched_grouped_results = (
        OMRResult.objects.filter(exam_sheet__isnull=True)
        .values('exam_identifier', 'class_name','omr_name')
        .annotate(
            num_attendees=Count('id'),
            latest_created_at=Max('created_at'),
            exam_date=Min('exam_date')  
        )
        .order_by('-latest_created_at')
    )

    matched_grouped_results = (
        OMRResult.objects.filter(exam_sheet__isnull=False)
        .values('exam_identifier', 'class_name' , 'omr_name',)
        .annotate(
            num_attendees=Count('id'),
            latest_created_at=Max('created_at'),
            exam_date=Min('exam_date')  # exam_date 추가
        )
        .order_by('-latest_created_at')
    )

    return render(request, 'omr_app/omr_answer_sheet_list.html', {
        'unmatched_grouped_results': unmatched_grouped_results,
        'matched_grouped_results': matched_grouped_results
    })



@require_POST
def finalize(request):
    print("finalize 호출됨")
    data = json.loads(request.body) # json 형태의 데이터를 파이썬 딕셔너리로 변환
    class_name = data.get('class_name')
    omr_name = data.get('omr_name')
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
        student_id = omr.get('student_id')
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
            class_name=class_name,
            omr_name=omr_name
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
            'class_name_by_school': st.class_name_by_school,
            'class_name': st.class_name,
        })
    return JsonResponse(data, safe=False)


def show_omr_upload_page(request):
    # 재원중인 학생들 필터
    enrolled_students = Student.objects.filter(status='enrolled')
    
    # 소속반 목록 추출 (None이나 빈 문자열 제외)
    class_name_list = enrolled_students.values_list('class_name', flat=True).distinct()
    class_name_list = [cn for cn in class_name_list if cn and cn.strip()]

    # 학교반 목록 추출 (None이나 빈 문자열 제외)
    class_name_by_school_list = enrolled_students.values_list('class_name_by_school', flat=True).distinct()
    class_name_by_school_list = [cns for cns in class_name_by_school_list if cns and cns.strip()]

    return render(request, 'omr_app/omr_upload.html', {
        'class_name_list': class_name_list,
        'class_name_by_school_list': class_name_by_school_list,
    })

@csrf_exempt
def omr_process(request):
    if request.method == 'POST' and request.FILES.get('file'):
        print("omr_process 호출됨")
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name.lower() # 파일 확장자��� Content_Type으로 PDF vs Image 판별

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
        results = results.filter(student__name__icontains=student_name)
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
        students_all = Student.objects.filter(status='enrolled')
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
        students = Student.objects.filter(status='enrolled').annotate( # annotate는 기존 모델에 없는 새로운 필드를 임시로 추가함.
            sort_date=Coalesce( # Coalesce는 첫번째 인자가 None이면 두번째 인자를 반환함.
                'registered_date',
                Value('9999-12-31', output_field=DateField()) #9999-12-31은 문자열 이므로 date타입으로 바꿔서 두번째 인자로 전달함
            )
        ).order_by('sort_date', 'registration_number', 'id')
        print("정렬 후 학생 수:", students.count())  # 디버깅용 출력
        
        return render(request, 'omr_app/student_list.html', {
            'students': students, # 전체 df를 테이블에 표시하기 위함
            'grades': [1, 2, 3], # 학년 드롭다운 option 값으로 사용됨
            'schools': Student.objects.filter(status='enrolled').values_list('school_name', flat=True).distinct(), # 학교 드롭다운 option 값으로 사용됨
            'class_names': Student.objects.filter(status='enrolled').values_list('class_name', flat=True).distinct(), # 반 드롭다운 option 값으로 사용됨 
            'today': date.today()
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
    omr_results = OMRResult.objects.filter(student_id=student_id).order_by('-exam_date')

    
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
    selected_students = request.POST.getlist('selected_students')
    action = request.POST.get('action')
    
    if not selected_students:
        return JsonResponse({
            'status': 'error',
            'message': "선택된 학생이 없습니다."
        })

    if action == 'update':
        new_class_name = request.POST.get('new_class_name')
        new_school_name = request.POST.get('new_school_name')
        new_grade = request.POST.get('new_grade')

        updated_count = update_students(selected_students, new_class_name, new_school_name, new_grade) # 업데이트 건수 반환
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
        Student.objects.filter(id__in=selected_students).update(status=new_status, status_changed_date=new_status_date, status_reason=new_status_reason)
        return JsonResponse({'status': 'success'})
    
    elif action == 're_enroll':
        # 등원 처리: status='enrolled', 상태변경일/사유 초기화
        Student.objects.filter(id__in=selected_students).update(
            status='enrolled',
            status_changed_date=None,
            status_reason=None
        )
        return JsonResponse({'status': 'success'})

    elif action == 'delete_permanently':
        # 완전 삭제
        Student.objects.filter(id__in=selected_students).delete()
        return JsonResponse({'status': 'success'})
    
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
    

    # update_fields에 값이 있는 경우 학생 정보 업데이트
    if update_fields:
        for k, v in update_fields.items(): 
            setattr(student, k, v) # student 객체의 k속성에 v값을 설정함. (setattr = 객체의 속성을 동적으로 설정할 때 사용)
        student.save()
        return JsonResponse({'status': 'success','message': '학생 정보가 성공적으로 수정되었습니다.'})
    else:
        return JsonResponse({'status': 'error','message': '수정할 정보가 없습니다.'})
            


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

    return render(request, 'omr_app/inactive_student_list.html', {
        'students': queryset
    })
    
    
    
@require_POST
def bulk_omr_delete(request):
    print("bulk_omr_delete 호출됨")
    exam_identifiers = request.POST.getlist('selected_exam_identifier')
    omr_names = request.POST.getlist('selected_omr_name')
    class_names = request.POST.getlist('selected_class_name')

    if not exam_identifiers or not omr_names:
        return JsonResponse({'status': 'error', 'message': '선택된 시험지가 없습니다.'})
    
    if len(exam_identifiers) != len(omr_names):
        return JsonResponse({'status': 'error', 'message': '데이터 불일치가 발생했습니다.'})

     # 각각 (exam_identifier, omr_name, class_name) 쌍에 대해 삭제 수행
    for ident, oname, cname in zip(exam_identifiers, omr_names, class_names):
        OMRResult.objects.filter(exam_identifier=ident, omr_name=oname, class_name=cname).delete()

    return JsonResponse({'status': 'success'})


def upload_exam_sheet(request):
    """시험지 업로드 페이지를 렌더링"""
    return render(request, 'omr_app/upload_exam_sheet.html')



def upload_exam(request):
    print("upload_exam 함수 호출됨")
    if request.method == 'POST' and request.FILES.get('hwp_file'):
        hwp_file = request.FILES['hwp_file']
        
        if not os.path.exists(settings.TEMP_DIR):
            os.makedirs(settings.TEMP_DIR)
        
        temp_path = os.path.join(settings.TEMP_DIR, hwp_file.name)
        try:
            with open(temp_path, 'wb+') as destination:
                for chunk in hwp_file.chunks():
                    destination.write(chunk)
                    
            question_data = extract_exam_sheet_data(temp_path,visible=False)
            request.session['temp_question_data'] = question_data
            
            return JsonResponse({
                'status': 'success',
                'data': question_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
        finally:
            # 임시 파일과 HWP 프로세스 정리
            if os.path.exists(temp_path):
                os.remove(temp_path)
            HwpProcessManager.kill_hwp_processes()


@require_POST
def finalize_exam(request):
    """
    1) 시험지(ExamSheet) 생성
    2) 지문(OriginalText/ExternalText) 생성
    3) 문제(Question) 생성
    4) ExamSheetQuestionMapping 생성
    5) 필요한 경우, Choice(보기) 생성
    """
    try:
        # 1) 요청 데이터 파싱
        body = json.loads(request.body)
        exam_name = body.get("exam_name")  # 사용자가 입력한 시험명
        extracted_data = body.get("data", [])  # 지문/문제 추출 결과

        if not exam_name or not extracted_data:
            return JsonResponse({
                'status': 'error', 
                'message': '유효하지 않은 데이터입니다.'
            }, status=400)

        # 2) ExamSheet 생성
        #    - serial_number는 필요 시 자동 생성 로직 구현 가능.
        with transaction.atomic():  # DB 트랜잭션 보장
            exam_sheet = ExamSheet.objects.create(
                title=exam_name,
                total_questions=0  # 일단 0으로 저장 후, 이후에 업데이트
            )

            total_question_count = 0  # 누적 문항수

            # 3) extracted_data(지문들) 반복 처리
            for passage_dict in extracted_data:
                
                # 1) Passage 생성
                passage_obj = Passage.objects.create(
                    passage_source=passage_dict.get("passage_source",''), # 예: "고2 23년 6월 39번"
                    passage_text=passage_dict.get("passage_text", ''),
                    passage_table=passage_dict.get("passage_table", '')
                )
                
                # 2) question_list 순회
                question_list = passage_dict.get("question_list", [])
                for q_dict in question_list:
                    total_question_count += 1
                    q_type   = q_dict.get("question_type")    # "어법", "빈칸", "논술형(어법)" 등
                    is_essay = q_dict.get("is_essay", False) # 논술형 여부
                    answer_list   = q_dict.get("answer")       # 객관식의 경우 [2], [3], ...
                    explanation   = q_dict.get("explanation", "")

                    question_obj = Question.objects.create(
                        passage=passage_obj,  # 새로 만든 passage 연결
                        detail_type=Question.HWP_MAPPING_TO_DETAIL_TYPE.get(q_type, None),
                        answer_format='SA' if is_essay else 'MC',
                        answer=" / ".join(map(str, answer_list)) if answer_list else "",
                        explanation=explanation,
                        question_text=q_dict.get("question_text", ""),
                    )
                    
                    # (C) QuestionTable 생성
                    # 프론트엔드에서 question_table은 배열 (ex: ["<table>..</table>", "<table>..</table>"])
                    question_table_list = q_dict.get("question_table", [])
                    for idx, table_html in enumerate(question_table_list, start=1):
                        QuestionTable.objects.create(
                            question=question_obj,
                            content=table_html
                            # table_group=idx, ...
                        )
                    
                    
                    # Choice(객관식 보기) 생성
                    choice_list = q_dict.get("choice_list", [])
                    if not is_essay and choice_list:
                        for idx, choice_obj in enumerate(choice_list, start=1):
                            Choice.objects.create(
                                question=question_obj,
                                choice_number=idx,
                                text_content=choice_obj.get('choice_text', "")
                            )
                    
                    # (C) 주관식 작성란(AnswerField) - is_essay=True 인 경우
                    answer_field_list = q_dict.get("answer_field_list", [])
                    if is_essay and answer_field_list:
                        for f_idx, field_text in enumerate(answer_field_list, start=1):
                            AnswerField.objects.create(
                                question=question_obj,
                                text_format=field_text
                            )
                    
                    # 시험지 - 문제 매핑
                    question_number = q_dict.get("question_number") or total_question_count # 문서 내 문항번호가 없으면 누적 문항수로 매핑
                    ExamSheetQuestionMapping.objects.create(
                        exam_sheet=exam_sheet,
                        question=question_obj,
                        question_number=question_number
                    )
                    
            # (모든 passage 처리 후) total_questions 갯수 업데이트
            exam_sheet.total_questions = total_question_count
            exam_sheet.save()

        # 모든 등록 성공 시
        return JsonResponse({
            'status': 'success', 
            'redirect_url': '/omr_app/exam-sheet/list'  # 혹은 원하는 URL
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
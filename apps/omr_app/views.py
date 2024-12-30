# views.py
import json
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.urls import reverse

from django.db.models import Q, Count, Max

from apps.omr_app.services.omr_service import process_pdf_and_extract_omr, extract_omr_data_from_image

from apps.omr_app.models import OMRResult
from apps.student_app.models import Student




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


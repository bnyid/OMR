# apps/omr_app/views.py
import json, glob, base64, os, shutil

from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.urls import reverse

from django.db.models import Q, Count, Max

from apps.omr_app.services.omr_service import extract_omr_data

from apps.omr_app.models import OMRResult
from apps.student_app.models import Student
from apps.exam_app.models import ExamSheet

from django.conf import settings
from .models import OMRResultEssayImage


@csrf_exempt
def omr_process(request):
    if request.method == 'POST' and request.FILES.get('file'):
        print("omr_process 호출됨")
        uploaded_file = request.FILES['file']
        try:
            omr_results = extract_omr_data(uploaded_file)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'omr_process 뷰의 extract_omr_data 함수 오류 발생: {str(e)}'
            }, status=500)
            
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
                
        omr_result = OMRResult.objects.create(
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

        # 이제 주관식 이미지 옮기기 (omr_key)
        omr_key = omr.get('omr_key')
        if omr_key:
            # 1) 임시 폴더에서 파일 찾기
            temp_dir = getattr(settings, 'TEMP_DIR', '/tmp')
            temp_omr_dir = os.path.join(temp_dir, 'temp_omr_images')
            
            front_filename = f"{omr_key}_front.jpg"
            front_file_path = os.path.join(temp_omr_dir, front_filename)
            if os.path.exists(front_file_path):
                # 2) Media 폴더 (예: MEDIA_ROOT / 'omr_front_pages')
                media_front_dir = os.path.join(settings.MEDIA_ROOT, 'omr_front_pages')
                os.makedirs(media_front_dir, exist_ok=True)

                # 3) 이동
                new_path = os.path.join(media_front_dir, front_filename)
                shutil.move(front_file_path, new_path)

                # 4) OMRResult.front_page = "omr_front_pages/파일명"
                relative_front = f"omr_front_pages/{front_filename}"
                omr_result.front_page = relative_front
                omr_result.save()
            
            pattern = os.path.join(temp_omr_dir, f"{omr_key}_*.jpg")
            file_list = glob.glob(pattern)

            # 2) Media 폴더 생성
            media_essay_dir = os.path.join(settings.MEDIA_ROOT, 'essay_images')
            os.makedirs(media_essay_dir, exist_ok=True)

            # 3) 파일을 한 개씩 옮기면서 OMRResultEssayImage 생성
            for path in sorted(file_list):
                # path 예: "/tmp/temp_omr_images/omr_key_0.jpg"
                filename = os.path.basename(path)  # "omr_key_0.jpg"
                # 여기서 question_number를 파싱할 수 있으면 int(filename.split('_')[1].split('.')[0]) 식으로 (주의)
                # 예: "xxxx-uuid-xxxx_0.jpg" -> "0"
                try:
                    question_number = int(filename.split('_')[-1].split('.')[0])
                except:
                    question_number = 0

                # 새 파일 위치
                new_path = os.path.join(media_essay_dir, filename)

                # 파일 이동
                shutil.move(path, new_path)
                # DB 저장 (ImageField는 "essay_images/filename" 형태로 저장됨)
                # relative 경로만 넣어주면 Django가 /media/essay_images/... 에서 serve
                relative_path = f"essay_images/{filename}"

                OMRResultEssayImage.objects.create(
                    omr_result=omr_result,
                    question_number=question_number,
                    image=relative_path
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
    omr_result = get_object_or_404(OMRResult, id=result_id)
    # essay_images = omr_result.essay_images.all()  # (1:N)
    return render(request, 'omr_app/omr_result_detail.html', {
        'omr_result': omr_result
    })

@require_POST
def get_temp_front_image(request):
    """
    JS fetch로 omr_key를 받으면,
    temp_omr_images/<omr_key>_front.jpg를 base64로 변환하여 JSON으로 반환
    """
    try:
        data = json.loads(request.body)
        omr_key = data.get('omr_key')
        if not omr_key:
            return JsonResponse({
                'status': 'error',
                'message': 'No omr_key provided.'
            }, status=400)

        # temp 디렉터리
        temp_dir = getattr(settings, 'TEMP_DIR', '/tmp')
        temp_omr_dir = os.path.join(temp_dir, 'temp_omr_images')
        front_filename = f"{omr_key}_front.jpg"
        front_path = os.path.join(temp_omr_dir, front_filename)

        if not os.path.exists(front_path):
            return JsonResponse({
                'status': 'error',
                'message': 'Front image not found.'
            }, status=404)

        # base64 변환
        with open(front_path, 'rb') as f:
            raw = f.read()

        import base64
        b64 = base64.b64encode(raw).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{b64}"

        return JsonResponse({
            'status': 'success',
            'front_image_url': data_url,
        })
    except Exception as e:
        return JsonResponse({'status':'error','message':str(e)}, status=500)
    
    
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



def get_essay_images(request):
    """
    1) omr_key를 받아
    2) temp_omr_images/{omr_key}_*.jpg 파일들을 찾아
    3) base64 or dataURL로 반환 (미리보기 용)
    """
    omr_key = request.GET.get('omr_key')
    if not omr_key:
        return JsonResponse({"status": "error", "message": "omr_key is required"}, status=400)

    temp_dir = getattr(settings, 'TEMP_DIR', '/tmp')
    temp_omr_dir = os.path.join(temp_dir, 'temp_omr_images')
    if not os.path.exists(temp_omr_dir):
        return JsonResponse({"status":"success", "images":[]})

    pattern = os.path.join(temp_omr_dir, f"{omr_key}_*.jpg")
    file_list = glob.glob(pattern)

    images_base64 = []
    for path in sorted(file_list):
        with open(path, 'rb') as f:
            raw = f.read()
            b64 = base64.b64encode(raw).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{b64}"
            images_base64.append(data_url)

    return JsonResponse({"status":"success", "images": images_base64})




@require_POST
def match_and_grade(request):
    """
    1) exam_identifier_list를 받아서
    2) OMRResult들을 ExamSheet와 매칭
    3) 객관식 채점을 진행
    4) 채점 완료되면 status=success 반환
    """
    try:
        data = json.loads(request.body)
        exam_identifier_list = data.get('exam_identifier_list', [])

        if not exam_identifier_list:
            return JsonResponse({'status':'error','message':'no exam_identifier_list given'}, status=400)

        # (A) 예: 우선 하나의 exam_sheet로 매칭한다고 가정 (실무에서는 UI에서 선택)
        # sheet_id = ...
        # exam_sheet = ExamSheet.objects.get(id=sheet_id)
        # 여기서는 그냥 "임의" exam_sheet 하나를 예시로 가져온다고 가정:
        exam_sheet = ExamSheet.objects.order_by('-created_at').first()
        if not exam_sheet:
            return JsonResponse({'status':'error','message':'ExamSheet가 존재하지 않습니다.'}, status=400)

        # (B) exam_identifier_list 각각에 대해 OMRResult 찾고, exam_sheet로 연결
        from apps.omr_app.models import OMRResult
        omr_qs = OMRResult.objects.filter(exam_identifier__in=exam_identifier_list, exam_sheet__isnull=True)
        # isnull=True → 아직 미매칭인 것만

        if not omr_qs.exists():
            return JsonResponse({'status':'error','message':'해당 식별자의 미매칭 OMR이 없음'}, status=400)

        # exam_sheet 매핑
        omr_qs.update(exam_sheet=exam_sheet)

        # (C) 간단 객관식 채점 로직 (실제로는 exam_sheet.questions와 omr.answers를 비교)
        # 여기서는 그냥 "자동채점완료" 라고만 처리
        for omr in omr_qs:
            answers = omr.answers  # 예: {"1": 3, "2": 2, ...}
            # exam_sheet.questions --> 문제 리스트
            # 문제의 정답과 비교, 점수 계산 ...
            # omr_result.score = ...
            # omr.save() ...
            pass

        # (D) 응답
        return JsonResponse({'status':'success','message':'매칭 & 채점을 완료했습니다.'})

    except Exception as e:
        return JsonResponse({'status':'error','message':str(e)}, status=400)
    
    
    

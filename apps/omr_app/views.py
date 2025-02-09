# apps/omr_app/views.py
import json, glob, base64, os, shutil
from itertools import groupby
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.urls import reverse

from django.db.models import Count, Max, Sum, Min, F

from apps.omr_app.services.omr_service import extract_omr_data


from apps.omr_app.models import OMRResult
from apps.student_app.models import Student
from apps.exam_app.models import ExamSheet, Question


from django.conf import settings
from .models import OMRResultEssayImage, OMRStudentAnswer

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
                    omr['student_is_matched'] = True
        
        return JsonResponse({
            'status': 'success',
            'data': omr_results # 리스트 형태로 반환
        })
    
    return JsonResponse({
        'status': 'error',
        'message': '잘못된 요청입니다.'
    }, status=400)


## 시험별 답안지 목록 페이지
def omr_answer_sheet_list(request):
    from django.db.models import Min

    unmatched_grouped_results = (
        OMRResult.objects.filter(exam_sheet__isnull=True)
        .values('exam_identifier', 'class_name','omr_name') # values() : Django ORM에서 특정 필드만 선택하여 딕셔너리 형태로 반환
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

## 시험별 답안지 상세 페이지
def omr_result_grouped_detail(request, exam_identifier):
    # exam_identifier를 키로 OMRResult들 가져오기
    results = OMRResult.objects.filter(exam_identifier=exam_identifier).order_by('-created_at')
    return render(request, 'omr_app/omr_result_grouped_detail.html', {
        'exam_identifier': exam_identifier,
        'results': results
    })


@require_POST
def finalize(request):
    print("finalize 호출됨")
    data = json.loads(request.body) # json 형태의 데이터를 파이썬 딕셔너리로 변환
    class_name = data.get('class_name')
    omr_name = data.get('omr_name')
    omr_list = data.get('omr_data', [])

    for omr in omr_list:
        teacher_code = omr['teacher_code']
        student_is_matched = omr['student_is_matched']
        student_code = omr['student_code']
        student_name = omr['student_name']
        answers = omr['answers']

        exam_date_str = omr['exam_date'] # 'YYYY-MM-DD'
        try:
            exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': f'시험일 data를 알맞게 수정하세요. {student_name}학생의 입력값: {exam_date_str}'
            }, status=400)
        

        # Student FK 매칭
        student_id = omr.get('student_id')
        student = None
        if student_is_matched:
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
            student=student if student_is_matched else None,
            unmatched_student_code=None,
            unmatched_student_name=None,
            answers=answers,
            class_name=class_name,
            omr_name=omr_name
        )

        # 이미지 temp에서 Media로 저장 (omr_key 기준)
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
            
            # 뒷면 이미지 처리
            pattern = os.path.join(temp_omr_dir, f"{omr_key}_*.jpg")
            file_list = glob.glob(pattern)

            # 2) Media 폴더 생성
            media_essay_dir = os.path.join(settings.MEDIA_ROOT, 'essay_images')
            os.makedirs(media_essay_dir, exist_ok=True)

            # 3) 파일을 한 개씩 옮기면서 각각 OMRResultEssayImage 생성
            for path in sorted(file_list):
                # path 예: "/tmp/temp_omr_images/omr_key_0.jpg"
                filename = os.path.basename(path)  # "omr_key_0.jpg"
                # 저장된 뒷면 이미지의 파일명 omr_key_0.jpg 에서 논술형 문항번호 추출
                # 예: "xxxx-uuid-xxxx_0.jpg" -> "0"
                try:
                    question_number = int(filename.split('_')[-1].split('.')[0])+1
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
def match_and_auto_grade(request):
    """
    1) exam_sheet_id, exam_identifier_list(OMR 식별자들) 를 받아
    2) 해당 OMRResult에 exam_sheet 연결 (이 때, is_matched=True로 설정)
    3) 객관식 문항 자동 채점 + 논술형(주관식) 채점 객체를 미리 생성 (채점 전 score_earned는 None)
    4) 연결된 exam_sheet의 논술형 문제 개수를 기반으로, 개수 초과된 주관식 이미지 삭제
    5) 완료 후 omr_grading_detail 페이지로 redirect
    """
    data = json.loads(request.body)
    exam_sheet_id = data.get('exam_sheet_id')
    exam_identifiers = data.get('exam_identifier_list', [])

    if not exam_sheet_id or not exam_identifiers:
        return JsonResponse({"status": "error", "message": "필요한 정보가 누락되었습니다."}, status=400)

    # 1) ExamSheet 가져오기
    exam_sheet = get_object_or_404(ExamSheet, id=exam_sheet_id)

    # 2) OMRResult update
    omr_qs = OMRResult.objects.filter(exam_identifier__in=exam_identifiers, exam_sheet=None)
    print(f"매칭되지 않은 OMRResult {omr_qs.count()}개를 찾았습니다..")
    omr_list = list(omr_qs)
    omr_qs.update(exam_sheet=exam_sheet)

    # 3) 객관식 문항 목록
    multi_qs = exam_sheet.questions.filter(multi_or_essay='객관식')
    print(f"{multi_qs.count()}개의 객관식 문항이 있습니다.")

    # 4) 각 OMRResult마다 answers(JSON) 파싱 → OMRStudentAnswer 생성/업데이트
    for omr in omr_list:
        answers_dict = omr.answers or {}
        for question in multi_qs:
            qnum = str(question.number) # n번 문항에 대해서
            student_answer = answers_dict.get(qnum)  # 학생이 고른 답(1개, 혹은 여러개 가능)
            if student_answer is None:
                continue  # 해당 문항에 응답 없는 경우 건너 뛰기
            selected = [student_answer] if not isinstance(student_answer, list) else student_answer  # 리스트가 아닌 경우 리스트로 (정답이 1개건 2개건 상관없이 리스트로 처리하기 위함)
            
            print(f"OMR {omr.id}의 객관식 {question.number}번 문항에 대한 학생 응답: {student_answer}")

            # OMRStudentAnswer 생성/갱신
            OMRStudentAnswer.objects.get_or_create( #get_or_create는 존재하지 않으면 생성, 존재하면 갱신(만약 생성의 경우, defaults로 전달하는 필드들을 업데이트)
                omr_result=omr,
                question=question,
                defaults={
                    'selected_answers': selected
                }
            )
            
    # 4) 논술형(주관식) 문항에 대해 미리 OMRStudentAnswer 객체 생성 (score_earned 필드는 나중에 사용자가 직접 채점하며 업데이트)
    essay_qs = exam_sheet.questions.filter(multi_or_essay='논술형').order_by('number')
    print(f"{essay_qs.count()}개의 논술형 문항이 있습니다.")
    for omr in omr_list:
        for question in essay_qs:
            OMRStudentAnswer.objects.get_or_create(
                omr_result=omr,
                question=question,
                defaults={
                    'selected_answers': None,   
                    'score_earned': None,
                    'total_score': question.score,
                }
            )
            print(f"OMR {omr.id}의 {omr.student.name}의 논술형 {question.number}번 문항에 대한 OMRStudentAnswer 객체 생성/갱신 완료")
        # 5) OMRResult에 연결된 주관식 이미지(OMRResultEssayImage) 중,
        # 시험지의 논술형 문항 수보다 초과된 이미지 삭제
        required_count = essay_qs.count()  # 실제 논술형 문항 수 (예: 6)
        extra_images = omr.essay_images.filter(question_number__gt=required_count)
        for extra_img in extra_images:
            # (선택 사항) 실제 파일도 삭제
            if extra_img.image:
                extra_img.image.delete(save=False)
            extra_img.delete()

    # 매칭된 exam_identifier 중 첫 번째로 채점 페이지 이동(혹은 첫 항목)
    first_identifier = exam_identifiers[0]
    redirect_url = reverse("omr_app:omr_grading_detail", args=[first_identifier])
    return JsonResponse({"status": "success", "redirect_url": redirect_url})



def omr_grading_detail(request, exam_identifier):
    # 1) exam_identifier를 받아서 exam_sheet가 연결된 OMRResult 찾기
    omrs = OMRResult.objects.filter(exam_identifier=exam_identifier, exam_sheet__isnull=False)
    if not omrs.exists():
        return render(request, 'omr_app/omr_grading_detail.html', {
            'error_message': '해당 식별자의 OMR이 없거나 시험지 미매칭 상태입니다.'
        })
    exam_sheet = omrs.first().exam_sheet

    for omr in omrs:
        objective_answers = omr.student_answers.filter(question__multi_or_essay='객관식')

        omr.objective_count = objective_answers.count()
        omr.objective_correct_count = objective_answers.filter(is_correct=True).count()
        
        omr.objective_score_earned_sum = objective_answers.aggregate(sum=Sum('score_earned'))['sum'] or 0.0
        omr.objective_score_total_sum = objective_answers.aggregate(sum=Sum('total_score'))['sum'] or 0.0
        
        essay_answers = omr.student_answers.filter(question__multi_or_essay='논술형')
        omr.essay_score_earned_sum = essay_answers.aggregate(sum=Sum('score_earned'))['sum'] or 0.0
        omr.essay_score_total_sum = essay_answers.aggregate(sum=Sum('total_score'))['sum'] or 0.0
        
        omr.total_score_earned = omr.objective_score_earned_sum + omr.essay_score_earned_sum
    
    # 총점을 기준으로 내림차순 정렬한 후, groupby를 이용해 같은 총점을 가진 OMR들을 그룹화
    sorted_omrs = sorted(omrs, key=lambda o: o.total_score_earned, reverse=True)
    
    total_omr_count = len(omrs)
    rank = 1
    
    for total_score, group in groupby(sorted_omrs, key=lambda o: o.total_score_earned):
        group_list = list(group)
        group_size = len(group_list)
        # 그룹에 2명 이상이면 공동 순위 표시
        for omr in group_list:
            if group_size > 1:
                omr.total_rank_str = f"{rank} (동석차 {group_size}명) / {total_omr_count}명"
            else:
                omr.total_rank_str = f"{rank} / {total_omr_count}명"
        rank += group_size
        

    # 2) 논술형 문항들만 별도 리스트
    essay_questions = exam_sheet.questions.filter(multi_or_essay='논술형').order_by('number')

    # 3) context로 전달
    return render(request, 'omr_app/omr_grading_detail.html', {
        'exam_identifier': exam_identifier,
        'exam_sheet': exam_sheet,
        'omrs': omrs,  # 이 omr에는 임시로 추가한 correct_count, earned_sum, total_sum 추가되어 있음
        'essay_questions': essay_questions,
    })
    
    

def fetch_essay_data(request):
    """
    exam_identifier를 받아,
    1) 해당되는 OMRResult들(학생들)과
    2) 시험지의 논술형 문항들
    3) 각 OMRResult에 연결된 주관식 이미지(OMRResultEssayImage)
    4) OMRStudentAnswer(논술형) 점수
    등을 JSON으로 반환
    """
    exam_identifier = request.GET.get('exam_identifier')
    if not exam_identifier:
        return JsonResponse({"status": "error", "message": "exam_identifier가 필요합니다."}, status=400)

    omrs = OMRResult.objects.filter(exam_identifier=exam_identifier, exam_sheet__isnull=False) # 파이썬의 None은 django db에서 null로 저장되므로, exam_sheet__isnull=False로 조회
    if not omrs.exists():
        return JsonResponse({"status": "error", "message": "OMR이 없거나 시험지 미매칭."}, status=404)

    exam_sheet = omrs.first().exam_sheet
    essay_questions = exam_sheet.questions.filter(multi_or_essay='논술형').order_by('number')

    # (A) questions JSON
    question_list = []
    for q in essay_questions:
        question_list.append({
            "id": q.id,
            "order_number": q.order_number,
            "number": q.number,
            "score": q.score,
            "question_text": q.question_text
        })

    # (B) omrs JSON
    omr_list = []
    for omr in omrs:
        # essay_images
        # OMRResultEssayImage (omr_result=omr, question_number=N)
        images = []
        for img in omr.essay_images.all():
            images.append({
                "question_number": img.question_number,
                # 이미지 접근: /media/essay_images/filename.jpg
                "image_url": img.image.url if img.image else ""
            })
        # answers
        # OMRStudentAnswer 중 multi_or_essay='논술형' 인 것만
        #   → question_id, score_earned, total_score
        answers = []
        # 대신 omr.student_answers.select_related('question') 해서 가져온 뒤 필터
        # 간단히 하기 위해 all()에서 논술형만 걸러내기
        for sa in omr.student_answers.all():
            if sa.question.multi_or_essay == '논술형':
                answers.append({
                    "question_id": sa.question.id,
                    "score_earned": sa.score_earned,
                    "total_score": sa.total_score
                })

        omr_list.append({
            "id": omr.id,
            "student_name": omr.student.name if omr.student else (omr.unmatched_student_name or "미매칭"),
            "essay_images": images,
            "answers": answers,
        })

    return JsonResponse({
        "status": "success",
        "essay_questions": question_list,
        "omr_list": omr_list,
    })
    
    
    
@require_POST
def grade_essay_update(request):
    """
    omr_result_id, question_id, new_score 를 받아
    OMRStudentAnswer의 score_earned를 업데이트
    """
    data = json.loads(request.body)
    omr_result_id = data.get('omr_result_id')
    question_id = data.get('question_id')
    new_score = data.get('new_score')
    
    omr_result = get_object_or_404(OMRResult, id=omr_result_id)
    print(f"OMRResult {omr_result.id} / {omr_result.student.name}를 찾았습니다.")
    question = get_object_or_404(Question, id=question_id)
    
    if not all([omr_result_id, question_id]) :
        return JsonResponse({"status": "error", "message": "omr_result의 id 혹은 문항의 id가 grade_essay_update뷰에 전달되지 않았습니다."}, status=400)
    if new_score is None:
        return JsonResponse({"status": "error", "message": "점수가 입력되지 않았습니다."}, status=400)

    if float(new_score) > float(question.score):
        return JsonResponse({
            "status": "error", 
            "message": f"입력된 점수({new_score})가 최대 점수({question.score})를 초과합니다."
        }, status=400)
    
    print("try문 직전")
    try:
        # 이미 채점이 진행된 경우 score_earned만 업데이트
        if OMRStudentAnswer.objects.filter(omr_result=omr_result, question=question).exists():
            print(f"OMR {omr_result.id}의 논술형 {question.number}번 문항에 대한 OMRStudentAnswer 객체가 이미 존재합니다. 점수 업데이트 진행")
            OMRStudentAnswer.objects.filter(omr_result=omr_result, question=question).update(score_earned=float(new_score))
            print(f"OMR {omr_result.id}의 논술형 {question.number}번 문항에 대한 OMRStudentAnswer 객체의 score_earned 필드가 업데이트되었습니다.")
        else:
            print(f"OMR {omr_result.id}의 논술형 {question.number}번 문항에 대한 OMRStudentAnswer 객체가 존재하지 않습니다.")
            
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    
def omr_grading_list(request):
    """
    매칭완료 OMR 목록 페이지
    """
    # 시험지와 매치된 OMR 필터링 (exam_sheet가 null이 아닌 것)
    matched_grouped_results = (
        OMRResult.objects.filter(exam_sheet__isnull=False)
        .values('exam_identifier', 'class_name' , 'omr_name',)
        .annotate(
            num_omrs=Count('id'),
            latest_created_at=Max('created_at'),
            exam_date=Min('exam_date'),
            teacher_code=F('teacher_code'),
            exam_sheet_title=F('exam_sheet__title')
        )
        .order_by('-latest_created_at')



    )

    return render(request, 'omr_app/omr_grading_list.html', {
        'matched_grouped_results': matched_grouped_results
    })

    

    

# apps/exam_app/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.exam_app.services.hwp_services import HwpProcessManager
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.urls import reverse
import os
from django.conf import settings
import json

from apps.exam_app.models import ExamSheet, Question
from apps.exam_app.services import extract_exam_sheet_info

def upload_exam_sheet(request):
    """시험지 업로드 페이지를 렌더링"""
    return render(request, 'exam_app/upload_exam_sheet.html')



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
                    
            question_dict_list = extract_exam_sheet_info(temp_path,visible=False)
            
            return JsonResponse({
                'status': 'success',
                'data': question_dict_list
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
    """시험지를 최종 등록하는 뷰.
    1) 클라이언트에서 전달한 JSON 데이터에서 exam_name과 문제 데이터(extractedData)를 파싱합니다.
    2) exam_name을 이용하여 ExamSheet 객체를 생성합니다.
    3) 전달받은 문제 데이터를 순회하며 각 문제에 대해 Question 객체를 생성하고,
       해당 시험지(ExamSheet)에 연결합니다.
    
    예상 input JSON 구조:
    
        {
            "exam_name": "중간고사",
            "data": [
                {
                    "order_number": 1,
                    "multi_or_essay": "객관식",
                    "number": 1,
                    "detail_type": "어법",
                    "question_text": "문제 내용...",
                    "answer": "정답",
                    "score": 2,
                },
                {
                    "order_number": 2,
                    "multi_or_essay": "논술형",
                    "number": 1,
                    "detail_type": "논술형(요약)",
                    "question_text": "다른 문제 내용...",
                    "answer": "정답",
                    "score": 5
                },
                ...
            ]
        }
    
    Returns:
        JsonResponse: 성공 시 redirect_url을 포함한 JSON 응답,
                      실패 시 에러 메시지를 포함한 JSON 응답.
    """
    try:
        # request.body 는 bytes 타입이므로 decode 후 파싱
        data = json.loads(request.body.decode('utf-8'))
        exam_name = data.get("exam_name")
        question_data_list = data.get("data", [])

        if not exam_name:
            return JsonResponse({
                "status": "error",
                "message": "시험명이 전달되지 않았습니다."
            }, status=400)

        # 데이터 정합성 검사: 문제 데이터가 없으면 오류
        if not question_data_list:
            return JsonResponse({
                "status": "error",
                "message": "문제 데이터가 존재하지 않습니다."
            }, status=400)

        # 트랜잭션 내에서 시험지와 문제들을 생성
        with transaction.atomic():
            # ExamSheet 생성 (total_questions는 question_data_list의 길이)
            exam_sheet = ExamSheet.objects.create(
                title=exam_name,
                total_questions=len(question_data_list)
            )
            
            # 각 문제 생성
            question_instances = []
            for qd in question_data_list:
                question_instance = Question(
                    exam_sheet=exam_sheet,
                    order_number=qd.get("order_number"),
                    multi_or_essay=qd.get("multi_or_essay"),
                    number=qd.get("number"),
                    detail_type=qd.get("detail_type"),
                    question_text=qd.get("question_text"),
                    answer=qd.get("answer"),
                    score=qd.get("score")
                )
                question_instances.append(question_instance)
            
            # bulk_create 로 한 번에 저장
            Question.objects.bulk_create(question_instances)
        
        # 성공 응답: 등록된 시험지의 detail page URL 등을 함께 리턴
        redirect_url = reverse('exam_app:exam_sheet_detail', args=[exam_sheet.id])
        return JsonResponse({
            "status": "success",
            "redirect_url": redirect_url
        })
            
    except Exception as e:
        # 에러 발생 시 traceback 을 기록하는 등의 처리를 할 수 있음
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)
        

def exam_sheet_detail(request, pk):
    exam_sheet = get_object_or_404(ExamSheet, pk=pk)
    return render(request, 'exam_app/exam_sheet_detail.html', {
        'exam_sheet': exam_sheet
    })

        
        
def exam_sheet_list(request):
    """
    - exam_sheets: 각 시험지의
       1) objective_count: 객관식 문제 수
       2) essay_count: 논술형 문제 수
       3) omr_count: 연결된 OMR 결과 수
         (여기서는 예시로 "OMRResult" 모델의 related_name이 'omrresults' 라고 가정)
    - 정렬은 "OMR=0개"인 시험지가 위, 나머지는 최근 생성 순
      (Case/When 이용 or 다른 로직)
    """

    # 예: 필드가 Question에 is_essay가 있으므로, 집계방식은 다음과 같이 가능
    exam_sheets = (ExamSheet.objects
        .annotate(
            # 객관식 문제(is_essay=False) 수
            objective_count=Count('questions', filter=Q(questions__multi_or_essay='객관식')),
            # 논술형 문제(is_essay=True) 수
            essay_count=Count('questions', filter=Q(questions__multi_or_essay='논술형')),
            omr_count=Count('omr_results', distinct=True), # related_name='omr_results'
        )
    )

    # 정렬 규칙: OMR=0개 → 위쪽, 이후 created_at DESC
    from django.db.models import Case, When, IntegerField
    exam_sheets = exam_sheets.annotate(
        zero_flag=Case(
            When(omr_count=0, then=0),
            default=1,
            output_field=IntegerField()
        )
    ).order_by('zero_flag', '-created_at')

    return render(request, 'exam_app/exam_sheet_list.html', {
        'exam_sheets': exam_sheets,
    })


def exam_sheet_bulk_delete(request):
    """
    - POST 요청으로 넘어온 sheet_ids(JSON)들을 받아 일괄 삭제
    - 예시 코드
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sheet_ids = data.get('sheet_ids', [])
            if not sheet_ids:
                return JsonResponse({'status': 'error', 'message': 'No IDs provided.'})

            ExamSheet.objects.filter(id__in=sheet_ids).delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
    
    
    
def api_exam_sheets(request):
    # 1) GET 파라미터에서 'q' (시험명 검색어)만 받는다.
    q = request.GET.get('q', '').strip()
    
    # 2) 기본적으로 created_at 내림차순 정렬 (최신 생성 시험지가 먼저)
    exam_sheets = ExamSheet.objects.all().order_by('-created_at')
    
    # 3) q가 있으면 제목(title)에 검색
    if q:
        exam_sheets = exam_sheets.filter(title__icontains=q)

    # 4) JSON 변환
    data = []
    for e in exam_sheets:
        data.append({
            "id": e.id,
            "title": e.title,
            "total_questions": e.total_questions,
            # 날짜/시간 형식 포맷
            "created_at": e.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    return JsonResponse(data, safe=False)
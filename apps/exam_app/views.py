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

from apps.exam_app.models import OriginalText, Passage, Question, Choice, ExamSheet, ExamSheetQuestionMapping
from apps.exam_app.services import extract_exam_sheet_data


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
                    
            exam_sheet_data = extract_exam_sheet_data(temp_path,visible=False)
            
            return JsonResponse({
                'status': 'success',
                'data': exam_sheet_data
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
        body = json.loads(request.body) # json데이터를 파싱하여 딕셔너리로 변환함.
        exam_name = body.get("exam_name")  # 사용자가 입력한 시험명
        extracted_data = body.get("data", [])  # 지문/문제 추출 결과
        print("[Debug] finalize_exam / extracted_data =", json.dumps(extracted_data, indent=2, ensure_ascii=False))

        if not exam_name or not extracted_data:
            return JsonResponse({
                'status': 'error', 
                'message': '시험지 이름이 없거나, 문제 데이터가 없습니다.'
            }, status=400)

        # 2) ExamSheet 생성
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
                )
                
                # 2) question_list 순회
                question_list = passage_dict.get("question_list", [])
                for q_dict in question_list:
                    total_question_count += 1 # 누적 문항수 증가
                    is_essay = q_dict.get("is_essay") # 논술형 여부
                    q_type   = q_dict.get("question_type")    # "어법", "빈칸", "논술형(어법)" 등
                    answer   = q_dict.get("answer")
                    explanation   = q_dict.get("explanation", "")
                    q_text        = q_dict.get("question_text")
                    q_text_extra  = q_dict.get("question_text_extra", "")
                    
                    print(f"[Debug] 문항 {total_question_count} - is_essay={is_essay}, q_type={q_dict.get('question_type')}")

                    
                    # 공통 필드 설정
                    question_obj = Question.objects.create(
                        passage=passage_obj,  # 새로 만든 passage 연결
                        detail_type=Question.HWP_MAPPING_TO_DETAIL_TYPE.get(q_type, None),
                        answer=answer,
                        question_text=q_text,
                        question_text_extra=q_text_extra,
                        is_essay=is_essay,
                    )
                    
                    print(f"[Debug] DB에 저장된 question_obj.id={question_obj.id}, is_essay={question_obj.is_essay}")
                    
                    # 객관식인 경우 Choice 객체연결 및 explanation 필드 설정
                    choice_list = q_dict.get("choice_list", [])
                    if not is_essay and choice_list:
                        for idx, choice_obj in enumerate(choice_list, start=1):
                            Choice.objects.create(
                                question=question_obj,
                                choice_number=idx,
                                text_content=choice_obj.get('choice_text', "")
                            )
                        question_obj.explanation = explanation
                        question_obj.save()
                    
                    # 주관식인 경우 answer_format 필드 설정
                    answer_format = q_dict.get("answer_format", "")
                    if is_essay and answer_format:
                        question_obj.answer_format = answer_format
                        question_obj.save()
                    

                    # 시험지 - 문제 매핑
                    question_number = q_dict.get("question_number") or total_question_count # 문서 내 문항번호가 없으면 누적 문항수로 매핑
                    ExamSheetQuestionMapping.objects.create(
                        exam_sheet=exam_sheet,
                        question=question_obj,
                        question_number=question_number,
                        order_number=total_question_count
                    )
                    
            # (모든 passage 처리 후) total_questions 갯수 업데이트
            exam_sheet.total_questions = total_question_count
            exam_sheet.save()

        # 모든 등록 성공 시
        return JsonResponse({
            'status': 'success', 
            'redirect_url': reverse('exam_app:exam_sheet_list')
        })
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
        
        
        
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
            objective_count=Count('questions', filter=Q(questions__is_essay=False)),
            # 논술형 문제(is_essay=True) 수
            essay_count=Count('questions', filter=Q(questions__is_essay=True)),
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


def exam_sheet_detail(request, pk):
    exam_sheet = get_object_or_404(ExamSheet, pk=pk)

    passages = Passage.objects.filter(questions__exam_sheets=exam_sheet).distinct()

    passage_list = []
    
    for passage in passages:
        # passage에 연결된 question(현재 exam_sheet에 속한 것만)
        q_list = passage.questions.filter(exam_sheets=exam_sheet).order_by('id')
        # 만약 2문항인지(is_double) 여부를 구분하고 싶다면:
        is_double = (q_list.count() == 2)
        print(f"[Debug] passage.id={passage.id}, passage.passage_source={passage.passage_source}, q_list.count={q_list.count()}")
        # 여기서 question 정보를 좀 더 가공해서, 
        # choices도 가져온 뒤 list로 넣어준다
        question_data_list = []
        passage_label_list = []    
        for q in q_list:
            
            label = None
            question_number = ExamSheetQuestionMapping.objects.get(question=q).question_number
            if q.is_essay:
                label = f"논술형{question_number}"
            else: 
                label = question_number
                
            passage_label_list.append(label)
            
            
            choices = q.choices.all().order_by('choice_number')  # 객체 리스트
            # 필요한 데이터를 dict로 만들어 append
            question_data_list.append({
                'question_text': q.question_text,
                'question_text_extra': q.question_text_extra,
                'question_is_essay': q.is_essay,
                'question_number': question_number,
                'answer': q.answer,               # 객관식 [2], 주관식 str
                'explanation': q.explanation,     # 객관식 해설
                'answer_format': q.answer_format, # 논술형 답안형식
                'choices': choices,               # 객체 리스트
            })

        passage_list.append({
            'passage': passage,
            'question_list': question_data_list,
            'is_double': is_double,
            'passage_label_list': passage_label_list,
        })

    context = {
        'exam_sheet': exam_sheet,
        'passage_list': passage_list,
    }
    return render(request, 'exam_app/exam_sheet_detail.html', context)
    
    
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
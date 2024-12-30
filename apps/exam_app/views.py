from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST


from django.db import transaction
from django.core.exceptions import ValidationError

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
                    
                    
                    
                    # 공통 필드 설정
                    question_obj = Question.objects.create(
                        passage=passage_obj,  # 새로 만든 passage 연결
                        detail_type=Question.HWP_MAPPING_TO_DETAIL_TYPE.get(q_type, None),
                        answer=answer,
                        question_text=q_text,
                        question_text_extra=q_text_extra,
                    )
                    
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
            'redirect_url': '/omr_app/exam-sheet/list'  # 혹은 원하는 URL
        })
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
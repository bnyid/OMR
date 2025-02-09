논술형 문항의 채점의 플로우.

1. 먼저, omr_service.py의 extract_omr_data 함수가 OMR의 앞면과 뒷면 데이터들을 인식하는데, 하나의 omr에 대해 omr_data라는 딕셔너리에 저장하고 있어. 이 omr_data 딕셔너리는 고유하게 부여된 omr_key와 앞면의 시험일, 강사코드, 학생코드, 학생이름, 답안, 매칭여부가 저장되어 있어.

2. 추가로, omr_service.py는 뒷면의 10개의 주관식 답안 이미지(1번~10번)를 인식하여 각각 temp_dir에 저장하고 있어. 주관식 이미지의 파일이름에 omr_key와 번호 인덱스(0~9)를 넣어서 추후에 주관식 이미지 10개를 OMR에 연결할 수 있도록 하고 있어

3. 프론트엔드에서 간단하게 omr 정보를 검수한 뒤에, finalize를 호출하며 백엔드로 omrResultsList를 넘겨줘. 이때, student_id와 student_is_matched가 추가되어서 넘어가게 되는데, 여기서 student_is_matched는 OmrResult 모델의 is_matched필드(=시험지 매칭에 사용됨)가 아니라, 학생 매칭을 위해 사용되는거야. (추후 발생할 혼동을 막기 위해, 너한테 코드를 제시한 이후에 is_matched를 student_is_matched로 변수명을 수정했어)

4. finalize는 omrResultsList를 넘겨받고, 넘겨받은 student_id를 비롯한 정보들로 OMRResult 객체를 생성해. 또한, omr_key를 이용하여 백엔드에 저장된 앞면 이미지와 뒷면 이미지를 불러와서 임시폴더가 아닌 media 폴더에 저장하고, 생성된 OMRResult 객체와 연결된OMRResultEssayImage 객체도 생성해.

5. 이후에 시험지도 업데이트가 되었고, omr_answer_sheet_list에서 시험지의 id와 exam_identifier를 match_and_auto_grade 뷰로 넘겨주면, ExamSheet 객체와 OMRResult객체를 연결하고, OMRStudentAnswer객체를 생성하여 객관식 채점을 진행하게돼.

6. 그다음 프론트에서(=omr_grading_detail.html에서) updateEssayScore를 하면 body에 omr_result_id, question_id, new_score 를 담아서 백엔드(=omr_app/views.py)의 grade_essay_update를 호출하게되고,

7. grade_essay_update 뷰에서는 프론트에서 전송된 omr_result_id와 question_id로 일치하는 omr_result 객체와 question객체를 찾게돼.

8. 이 때, 해당 omr_result, question 객체와 연결된 OMRStudentAnswer 객체가 있는지를 검색하고, 만약 있다면 해당 OMRStudentAnswer객체의 score_earned 필드의 값만 전송된 new_score로 업데이트 해주고, 없다면 객체를 새로 생성하도록 하고 있어.

---

위 논리에서 내가 수정하고 싶은 부분은, 주관식 문제에 대한 채점 객체(OMRStudentAnswer)의 생성 시기야. 객관식은 ExamSheet와 OMRResult가 연결되는 즉시 채점 객체가 생성되고 채점이 완료되는데, 주관식은 그렇지 않은 상태야.

주관식의 경우, 채점이 이루어지지 않더라도 일단 ExamSheet와 OMRResult가 연결되는 순간(5번에 해당) score_earned는 비어있는 채로 객체가 생성되게 하고 싶어.
이 때, 만약 ExamSheet의 주관식 문항의 개수가 6개라면, OMRResult에 연결된 10개의 OMRResultEssayImage 중 뒤의 4개는 삭제돼야해.

이후에 실제 user가 채점을 진행하는 8번 단계에서는, 이미 생성된 OMRStudentAnswer객체에 대해 score_earned만 조정하는 방식으로 진행하는거지!

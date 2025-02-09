# apps/omr_app/services/omr_service.py
import cv2
import uuid
import numpy as np
import pandas as pd
from ._omr_service_sub import get_coordinates_from_large_contours, get_omr_area_image, extract_marking_area, analyze_omr_grid, convert_marking_to_number, convert_marking_to_hangul, find_markers_for_omr, warp_to_standard_view, split_backside_into_equal_regions
import logging
from pdf2image import convert_from_bytes
from django.conf import settings
import os

logger = logging.getLogger(__name__)


def extract_omr_data(pdf_file):
    """
    PDF로 스캔된 OMR(앞면 + 뒷면)을 처리하여, 각 OMR 카드의 정보를 추출하고 딕셔너리 형태로 반환합니다.

        :returns:
        OMR 결과를 담은 딕셔너리들의 리스트. 각 딕셔너리는 다음과 같은 키를 가집니다:
        * **omr_key** (str): 임시 식별자(문자열) - 저장된 essay_images와 연결될 때 식별자로 사용
        * **exam_date** (str): YYYY-MM-DD 형식의 시험일
        * **teacher_code** (str): 2자리 강사코드
        * **student_code** (str): 8자리 학번
        * **student_name** (str): 한글 이름
        * **answers** (list): 객관식 답안 정보가 담긴 리스트. 예:  
          ``[{'question_number': 1, 'answer': '2'}, {'question_number': 2, 'answer': 'X'}, ...]``
        * **is_matched** (bool): 학생코드가 DB Student와 매칭되었는지 여부 (기본값 False)

    :rtype: list of dict
    
    본 함수는 다음 과정을 거칩니다:

    1. 업로드된 PDF 파일을 바이트로 읽은 뒤, PIL 이미지로 변환합니다.
    2. PDF가 짝수 장이라고 가정하고, 한 쌍(앞면, 뒷면)씩 처리합니다.
    3. **앞면**에서는:
       - 시험일(YYMMDD → YYYY-MM-DD 변환)
       - 강사코드(2자리)
       - 학번(8자리)
       - 이름(OMR로 인식된 한글 이름)
       - 객관식 답안(1-5 또는 'X')  
       를 추출합니다.
    4. **뒷면**에서는:
       - 이미지를 좌우로 나눈 뒤, 각각의 컨투어를 y축 순서로 탐색하여 주관식 영역을 10개 검출합니다.
       - 각 영역을 잘라낸 이미지를 리스트로 저장합니다.
    5. 추출된 데이터를 딕셔너리 형태로 반환합니다.

    :param pdf_file:
        업로드된 PDF 파일 객체 (예: ``request.FILES['file']``).
        내부적으로 PDF → PIL.Image 변환이 이루어지며, OMR 인식 과정에 사용됩니다.
    :type pdf_file: django.core.files.uploadedfile.InMemoryUploadedFile

    :raises ValueError:
        - PDF 변환에 실패한 경우
        - PDF의 페이지 수가 홀수여서 짝이 맞지 않는 경우
        - 원하는 영역(마커, 컨투어 등)을 찾지 못해 최소 개수를 만족하지 못한 경우



    .. note::

       - 본 함수는 단순히 OMR 정보를 추출하여 반환만 수행합니다.  
         DB에 저장하거나, 매칭 로직 등을 실행하는 작업은 별도 뷰나 로직에서 처리해야 합니다.
       - 뒷면 주관식 영역 이미지는 별도의 채점이나 DB 저장 과정을 통해 활용 가능합니다.
    """
    
    # 1) PDF -> PIL 이미지로 변환
    pdf_bytes = pdf_file.read()
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)  # PDF -> PIL 이미지 변환
    except Exception as e:
        raise ValueError(f"omr_process 뷰의 extract_omr_data 함수 오류 발생: PDF를 PIL 이미지로 변환 중 오류 발생: {e}")
    
    # 2) 각 페이지별 OMR 파싱
    results = []
    num_pages = len(images)
    
    for i in range(0, num_pages, 2):
        front_pil_image = images[i]
        
        if i + 1 < num_pages:
            back_pil_image = images[i+1]    
        else:
            raise ValueError("OMR 이미지를 양면으로 스캔하세요.")


        ### 앞면 처리
        image = cv2.cvtColor(np.array(front_pil_image), cv2.COLOR_RGB2BGR) # PIL -> OpenCV 변환
        try:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # 이미지를 회색조로 변환
            markers = find_markers_for_omr(gray_image, min_area=800, show_result=False)                    # 마커 찾기
            warped_image = warp_to_standard_view(gray_image,markers, show_result=False)             # 이미지 크기 표준화
            front_warped_image = warped_image
            contours = get_coordinates_from_large_contours(warped_image, 200000, show_result=False) # 큰 외곽선 좌표 추출
            
            # 시행일+강사코드 처리
            date_teacher_area = get_omr_area_image(contours[0], warped_image, show_result=False) # 시행일+강사코드 영역 추출
            date_teacher_marking_area = extract_marking_area(date_teacher_area,                  # 마킹 영역 추출
                                                skip_x=(False, 0, 0, 0),
                                                skip_y=(True, 150, 60000, 10000),                 # (스킵여부, 시작y좌표, 1차임계값(상), 2차임계값(하)) 1차 임계값 충족 이후 2차 임계값 아래로 내려오는 지점을 인식
                                                show_result=False)
            
            date_teacher_marking_result = analyze_omr_grid(date_teacher_marking_area,            # 마킹 인식
                                    start_point=(20,1),                                       # 시작 좌표 (y,x)
                                    rows=10, cols=8,                                         # 8자리 (시행일 6자 + 강사코드 2자)
                                    cell_size=(89.5, 61.2),                                  # 셀 크기 (y,x)
                                    first_row_height=89.5,                                     # 첫 행 높이
                                    first_row_gap=0,                                        # 첫 행 간격
                                    roi_size=(25,18),                                        # 관심영역 크기 (y,x)
                                    threshold=0.2,                                           # 임계값
                                    show_result=False)

            date_teacher_number = convert_marking_to_number(date_teacher_marking_result, read_by_column=True) # 마킹 -> 데이터 변환
            exam_date = date_teacher_number[:6]  # 앞 6자리는 시행일
            teacher_code = date_teacher_number[6:]  # 뒤 2자리는 강사코드
            
            # 학번 영역 처리
            id_area = get_omr_area_image(contours[1], warped_image, show_result=False)     # 학번 영역 추출
            id_marking_area = extract_marking_area(id_area,                                # 마킹 영역 추출
                                                skip_x=(False, 0, 0, 0),
                                                skip_y=(True, 150, 60000, 10000),
                                                show_result=False) 
            
            id_marking_result = analyze_omr_grid(id_marking_area,                          # 마킹 인식
                                    start_point=(20,1),                                       # 시작 좌표 (y,x)
                                    rows=10, cols=8,                                         # 8자리 (시행일 6자 + 강사코드 2자)
                                    cell_size=(89.5, 61.2),                                  # 셀 크기 (y,x)
                                    first_row_height=89.5,                                     # 첫 행 높이
                                    first_row_gap=0,                                        # 첫 행 간격
                                    roi_size=(25,18),                                        # 관심영역 크기 (y,x)
                                    threshold=0.2,                                           # 임계값
                                    show_result=False)
            
            student_code = convert_marking_to_number(id_marking_result, read_by_column=True) # 마킹 -> 데이터 변환

            # 이름 영역 처리
            name_area = get_omr_area_image(contours[2], warped_image, show_result=False)     # 이름 영역 추출
            name_marking_area = extract_marking_area(name_area,                              # 마킹 영역 추출
                                                    skip_x=(False, 0, 0, 0),
                                                    skip_y=(True, 175, 80000, 18000),
                                                    show_result=False)
            name_marking_result = analyze_omr_grid(name_marking_area,                        # 마킹 인식
                                    start_point=(6,2),
                                    rows=21, cols=12,
                                    cell_size=(59.3,54.3),
                                    first_row_height=59.3,
                                    first_row_gap=0,
                                    roi_size=(28,22),
                                    threshold=0.2,
                                    show_result=False)
            student_name = convert_marking_to_hangul(name_marking_result)                    # 마킹 -> 데이터 변환
            
            # 답안 영역 처리
            all_answers = [] # 답안 저장 객체
            question_numbers = [] # 문항 번호 저장 객체
            total_questions_processed = 0 # 총 처리된 문항 수
            for i in range(2): # 답안 영역 2개 합치기  + 답안의 문항번호 생성
                area = get_omr_area_image(contours[i+3], warped_image, show_result=False)
                marking_area = extract_marking_area(area,
                                                    skip_x=(True, 50, 200000, 35000), 
                                                    skip_y=(True,50,50000,8000), 
                                                    show_result=False)
                marking_result = analyze_omr_grid(marking_area,
                                            start_point=(19,16),
                                            rows=20, cols=5,
                                            cell_size=(78.23, 54.3),
                                            first_row_height=78.23,
                                            first_row_gap=0,
                                            roi_size=(28,22),
                                            threshold=0.2,
                                            show_result=False)
                
                answers = convert_marking_to_number(marking_result)
                all_answers.extend(list(answers))
                start_num = total_questions_processed + 1
                question_numbers.extend(range(start_num, start_num + len(answers)))
                total_questions_processed += len(answers)

            # exam_date 필드는 YYYY-MM-DD 형태로 변환해야 할 수도 있음.
            # 현재 exam_date_6는 YYMMDD 형태.
            # 여기서는 20YY-MM-DD로 가정(2000년대만 처리한다고 가정)
            year = "20" + exam_date[:2]
            month = exam_date[2:4]
            day = exam_date[4:6]
            exam_date_str = f"{year}-{month}-{day}"
            
            # answers를 JSON 형태로 변환
            answers_dict = {}
            for q_num, ans in zip(question_numbers, all_answers):
                answers_dict[str(q_num)] = ans
        except Exception as e:
            print(f"OMR 데이터 추출 실패(앞면). 오류: {e}")
            continue
        
        ########################## 뒷면 처리

        try:
            # PIL -> OpenCV 변환
            back_image = cv2.cvtColor(np.array(back_pil_image), cv2.COLOR_RGB2BGR) 
            # 이미지를 회색조로 변환
            gray_image = cv2.cvtColor(back_image, cv2.COLOR_BGR2GRAY) 
            
            # 마커 찾기
            back_markers = find_markers_for_omr(gray_image, show_result=False)                    # 마커 찾기
            # 이미지 크기 표준화
            back_warped_image = warp_to_standard_view(gray_image,back_markers, show_result=False)             
            
            height, width = back_warped_image.shape[:2]
            left_img = back_warped_image[:, :width//2]
            right_img = back_warped_image[:, width//2:]

            try:
                left_splits = split_backside_into_equal_regions(left_img,
                                                                    top_margin=180,
                                                                    bottom_margin=140,
                                                                    left_margin=10,
                                                                    right_margin=5,
                                                                    num_segments=5,
                                                                    show_result=False
                                                                    )
            except Exception as e:
                print(f"OMR 뒷면 처리 실패(왼쪽 영역). 오류: {e}")
                left_contours = []

            try:
                right_splits = split_backside_into_equal_regions(right_img,
                                                                    top_margin=180,
                                                                    bottom_margin=140,
                                                                    left_margin=0,
                                                                    right_margin=40,
                                                                    num_segments=5,
                                                                    show_result=False
                                                                    )
            except Exception as e:
                print(f"OMR 뒷면 처리 실패(오른쪽 영역). 오류: {e}")
                right_contours = []
            
            
            # 최종 분할 이미지 목록
            final_images = left_splits + right_splits
            omr_key = str(uuid.uuid4()) # 임시 식별자(문자열)
            
            
            # 파일 시스템 저장
            temp_dir = settings.TEMP_DIR
            temp_save_path = os.path.join(temp_dir, "temp_omr_images")
            os.makedirs(temp_save_path, exist_ok=True)

            # 앞면 이미지 저장
            front_filename = f"{omr_key}_front.jpg"
            front_filepath = os.path.join(temp_save_path, front_filename)
            cv2.imwrite(front_filepath, front_warped_image)

            # [3] 뒷면 이미지 저장 (뒷면 실제 파일로 저장)
            for cidx, split_img in enumerate(final_images):

                # 파일명 예) {omr_key}_0.jpg, {omr_key}_1.jpg ...
                filename = f"{omr_key}_{cidx}.jpg"
                filepath = os.path.join(temp_save_path, filename)

                # OpenCV로 jpg 저장
                cv2.imwrite(filepath, split_img)

        except Exception as be:
            print(f"OMR 뒷면 처리 실패 : {be}")
            omr_key = None
        
        
        
        # 반환할 딕셔너리 구성
        omr_data = {
            'omr_key': omr_key,
            'exam_date': exam_date_str, # YYYY-MM-DD 형식 문자열
            'teacher_code': teacher_code, # '01', '02' 등 2자리 문자열
            'student_code': student_code,
            'student_name': student_name,
            'answers': answers_dict,
            'student_is_matched': False,
        }

        results.append(omr_data)

    return results
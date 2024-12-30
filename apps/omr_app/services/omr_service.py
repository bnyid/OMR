# omr_service.py
import cv2
import numpy as np
import pandas as pd
from ._omr_service_sub import convert_to_bgr_image, correct_skew, get_coordinates_from_large_contours, get_omr_area_image, extract_marking_area, analyze_omr_grid, convert_marking_to_number, convert_marking_to_hangul, find_markers_for_omr, warp_to_standard_view
import logging
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)



def process_pdf_and_extract_omr(file):
    """
    주어진 PDF 파일을 페이지 단위로 이미지로 변환한 뒤,
    각 이미지에 대해 OMR 데이터를 추출하여 반환하는 함수.

    Parameters
    ----------
    file : InMemoryUploadedFile
        업로드된 PDF 파일 객체.

    Returns
    -------
    list of dict
        각 페이지별 OMR 처리 결과를 담은 딕셔너리의 리스트.
        각 딕셔너리는 다음과 같은 키를 포함한다.
        - exam_date (str): 'YYYY-MM-DD' 형식의 시험 날짜
        - teacher_code (str): '01', '02' 형태의 시험 순번
        - student_code (str): 추출된 학생 코드 (학번)
        - student_name (str): 추출된 학생 이름
        - answers (list): 각 문항별로 {'문항': int, '답': str} 형태의 딕셔너리를 담은 리스트

    Raises
    ------
    ValueError
        OMR 처리 중 필요한 영역을 찾지 못하거나 이미지 처리에 실패한 경우.

    Notes
    -----
    이 함수는 다음 단계를 수행한다.
    1. 업로드된 PDF를 바이트로 읽는다.
    2. pdf2image 라이브러리를 사용해 PDF를 페이지별 PIL 이미지로 변환한다.
    3. 각 PIL 이미지를 OpenCV용 numpy 배열(BGR)로 변환한다.
    4. 변환된 이미지 배열을 extract_omr_data_from_image 함수에 전달하여 OMR 데이터를 추출한다.
    5. 모든 페이지에 대해 추출된 OMR 데이터를 리스트에 담아 반환한다.

    예시
    ----
    >>> results = process_pdf_and_extract_omr(uploaded_pdf_file)
    >>> print(results)
    [
        {
            'exam_date': '2024-03-15',
            'teacher_code': '01',
            'student_code': '20240001',
            'student_name': '홍길동',
            'answers': [{'문항': 1, '답': '2'}, {'문항': 2, '답': '5'}, ...]
        },
        {
            'exam_date': '2024-03-15',
            'teacher_code': '01',
            'student_code': '20240002',
            'student_name': '김철수',
            'answers': [{'문항': 1, '답': '3'}, {'문항': 2, '답': '1'}, ...]
        }
    ]
    """
    pdf_bytes = file.read()
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)  # PDF -> PIL 이미지 변환
        print(f"PDF 변환 성공: {len(images)} 페이지 변환됨.")
        # 디버깅을 위해 중간 과정 이미지 저장
        def save_debug_image(image, name):
            cv2.imwrite(f'debug_{name}.jpg', image)
    except Exception as e:
        raise ValueError(f"PDF를 이미지로 변환하는 중 오류 발생: {e}")

    results = []
    for page_number, pil_image in enumerate(images, start=1):
        try:
            # PIL -> OpenCV 변환
            open_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            print(f"페이지 {page_number}: OpenCV 이미지로 변환 성공.")
            
            # np.ndarray 이미지를 OMR 처리 함수에 전달
            omr_data = extract_omr_data_from_image(open_cv_image)
            results.append(omr_data)
        except Exception as e:
            print(f"페이지 {page_number}: OMR 데이터 추출 실패. 오류: {e}")
            continue

    if not results:
        raise ValueError("OMR 데이터를 추출하지 못했습니다. PDF 파일이 올바른지 확인하세요.")

    return results


def extract_omr_data_from_image(image):
    """OMR 이미지를 처리하여 OMR 결과 데이터를 딕셔너리 형태로 반환하는 함수
    Parameters
    ----------
    image : numpy.ndarray
        처리할 OMR 이미지 (BGR 형식의 OpenCV 이미지)

    Returns (수정 필요)
    -------
    dict
        다음과 같은 열을 포함하는 딕셔너리:
        - 시행일 (str): 시험 시행일 6자리 (예: '240315')
        - 강사코드 (str): 2자리 반 코드 (예: '01')
        - 학번 (str): 8자리 학번
        - 이름 (str): 학생 이름 (한글)
        - 문항 (int): 문항 번호 (1부터 시작)
        - 답 (str): 각 문항의 답안 (1-5 또는 'X')

    Raises
    ------
    ValueError
        필요한 영역을 찾을 수 없을 때 발생
        (최소 5개의 contour가 필요함)

    Notes
    -----
    - 시행일은 앞 6자리, 강사코드는 뒤 2자리로 구성
    - 답안이 마킹되지 않은 경우 'X'로 표시
    - 각 문항별로 별도의 행으로 구성됨
    - 반환되는 DataFrame은 문항 순서대로 정렬되어 있음

    Examples
    --------
    >>> image = cv2.imread('omr_sample.jpg')
    >>> df = process_omr_image(image)
    >>> print(df.head())
       시행일  강사코드     학번   이름  문항  답
    0  240315   01  20240001  홍길동    1   2
    1  240315   01  20240001  홍길동    2   5
    2  240315   01  20240001  홍길동    3   1
    3  240315   01  20240001  홍길동    4   3
    4  240315   01  20240001  홍길동    5   4
    """
    
        # 여기서 image는 이미 np.ndarray (OpenCV BGR 이미지) 상태라고 가정합니다.
    if image is None:
        raise ValueError("이미지가 None 입니다.")
        
        # 이미지 전처리
        
    markers, gray_image = find_markers_for_omr(image,show_result=False)
    warped_image = warp_to_standard_view(gray_image,markers, show_result=False)
    
    contours = get_coordinates_from_large_contours(warped_image, 200000, show_result=False)

    # contours 개수 검증
    if len(contours) < 5:  # 필요한 최소 contour 개수를 5개로 수정
        raise ValueError(f"필요한 영역을 찾을 수 없습니다. (발견된 영역: {len(contours)}개, 필요한 영역: 5개)")
    
    
    # 시행일+강사코드 처리
    date_teacher_area = get_omr_area_image(contours[0], warped_image, show_result=False)
    date_teacher_marking_area = extract_marking_area(date_teacher_area, 
                                        skip_x=(False, 0, 0, 0),
                                        skip_y=(True, 150, 40000, 8000),
                                        show_result=False)
    date_teacher_marking_result = analyze_omr_grid(date_teacher_marking_area,
                            start_point=(0,1),
                            rows=10, cols=8,  # 8자리 (시행일 6자 + 강사코드 2자)
                            cell_size=(85.2, 53.8),
                            first_row_height=55,
                            first_row_gap=15,
                            roi_size=(25,18),
                            threshold=0.3,
                            show_result=False)
    
    date_teacher_number = convert_marking_to_number(date_teacher_marking_result, read_by_column=True)
    exam_date = date_teacher_number[:6]  # 앞 6자리는 시행일
    teacher_code = date_teacher_number[6:]  # 뒤 2자리는 강사코드
    
    # 학번 영역 처리
    id_area = get_omr_area_image(contours[1], warped_image, show_result=False)
    id_marking_area = extract_marking_area(id_area, 
                                        skip_x=(False, 0, 0, 0),
                                        skip_y=(True, 150, 40000, 8000),
                                        show_result=False) 
    
    id_marking_result = analyze_omr_grid(id_marking_area,
                            start_point=(0,1),
                            rows=10, cols=8,  # 8자리
                            cell_size=(85.1, 54),
                            first_row_height=57,
                            first_row_gap=13,
                            roi_size=(27,18),
                            threshold=0.3,
                            show_result=False)
    
    student_code = convert_marking_to_number(id_marking_result, read_by_column=True)

    # 이름 영역 처리
    name_area = get_omr_area_image(contours[2], warped_image, show_result=False)
    name_marking_area = extract_marking_area(name_area, 
                                            skip_x=(False, 0, 0, 0),
                                            skip_y=(True, 120, 60000, 10000),
                                            show_result=False)
    name_marking_result = analyze_omr_grid(name_marking_area,
                            start_point=(18,2),
                            rows=21, cols=12,
                            cell_size=(42.5,53.95),
                            first_row_height=42.5,
                            first_row_gap=0,
                            roi_size=(25,18),
                            threshold=0.3,
                            show_result=False)
    student_name = convert_marking_to_hangul(name_marking_result)
    
    # 답안 영역 처리
    all_answers = [] # 답안 저장 객체
    question_numbers = [] # 문항 번호 저장 객체
    total_questions_processed = 0 # 총 처리된 문항 수
    for i in range(2): # 답안 영역 2개 합치기  + 답안의 문항번호 생성
        area = get_omr_area_image(contours[i+3], warped_image, show_result=False)
        marking_area = extract_marking_area(area,
                                            skip_x=(True, 50, 150000, 20000), 
                                            skip_y=(True,50,30000,8000), 
                                            show_result=False)
        marking_result = analyze_omr_grid(marking_area,
                                    start_point=(5,13),
                                    rows=20, cols=5,
                                    cell_size=(84.9, 53.5),
                                    first_row_height=65,
                                    first_row_gap=10,
                                    roi_size=(25,19),
                                    threshold=0.3,
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
    answers_list = []
    for q_num, ans in zip(question_numbers, all_answers):
        answers_list.append({
            'question_number': q_num,
            'answer': ans
        })

    # 반환할 딕셔너리 구성
    result_data = {
        'exam_date': exam_date_str, # YYYY-MM-DD 형식 문자열
        'teacher_code': teacher_code, # '01', '02' 등 2자리 문자열
        'student_code': student_code,
        'student_name': student_name,
        'answers': answers_list,
        'is_matched': False,
    }

    # 6개 열을 가진 df 생성
    result_df = pd.DataFrame({
        '시행일': exam_date,
        '강사코드': teacher_code,
        '학번': student_code,
        '이름': student_name,
        '문항': question_numbers,
        '답': all_answers
    })
    
    return result_data

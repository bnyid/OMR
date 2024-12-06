import cv2
import numpy as np
import pandas as pd
from omr_app.models import OMRResult, Student
from ._omr_service_sub import convert_to_bgr_image, correct_skew, get_coordinates_from_large_contours, get_omr_area_image, extract_marking_area, analyze_omr_grid, convert_marking_to_number, convert_marking_to_hangul

def omr_image_to_OMRResult(image_file):
    """OMR 이미지를 처리하여 OMRResult 객체를 반환하는 함수

    Parameters
    ----------
    image : numpy.ndarray
        처리할 OMR 이미지 (BGR 형식의 OpenCV 이미지)

    Returns
    -------
    pandas.DataFrame
        다음과 같은 열을 포함하는 DataFrame:
        - 시행일 (str): 시험 시행일 6자리 (예: '240315')
        - 반코드 (str): 2자리 반 코드 (예: '01')
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
    - 시행일은 앞 6자리, 반코드는 뒤 2자리로 구성
    - 답안이 마킹되지 않은 경우 'X'로 표시
    - 각 문항별로 별도의 행으로 구성됨
    - 반환되는 DataFrame은 문항 순서대로 정렬되어 있음

    Examples
    --------
    >>> image = cv2.imread('omr_sample.jpg')
    >>> df = process_omr_image(image)
    >>> print(df.head())
       시행일  반코드     학번   이름  문항  답
    0  240315   01  20240001  홍길동    1   2
    1  240315   01  20240001  홍길동    2   5
    2  240315   01  20240001  홍길동    3   1
    3  240315   01  20240001  홍길동    4   3
    4  240315   01  20240001  홍길동    5   4
    """
    
    image = convert_to_bgr_image(image_file)
    if image is None:
        raise ValueError("이미지 변환 실패")
    
    # 이미지 전처리
    corrected_image = correct_skew(image)
    gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
    contours = get_coordinates_from_large_contours(gray_image, 200000, show_result=False)
    
    # contours 개수 검증
    if len(contours) < 5:  # 필요한 최소 contour 개수를 5개로 수정
        raise ValueError(f"필요한 영역을 찾을 수 없습니다. (발견된 영역: {len(contours)}개, 필요한 영역: 5개)")
    
    
    # 시행일+반코드 처리
    date_class_area = get_omr_area_image(contours[0], gray_image, show_result=False)
    date_class_marking_area = extract_marking_area(date_class_area, 
                                         skip_x=(False, 0, 0),
                                         skip_y=(True, 150, 60000),
                                         show_result=False)
    date_class_marking_result = analyze_omr_grid(date_class_marking_area,
                            start_point=(5,1),
                            rows=10, cols=8,  # 8자리 (시행일 6자 + 반코드 2자)
                            cell_size=(66.75, 40),
                            first_row_height=40,
                            first_row_gap=13,
                            roi_size=(25,15),
                            threshold=0.5,
                            show_result=False)
    date_class_number = convert_marking_to_number(date_class_marking_result, read_by_column=True)
    exam_date = date_class_number[:6]  # 앞 6자리는 시행일
    class_code = date_class_number[6:]  # 뒤 2자리는 반코드
    
    '''이전 파라미터 기록 (삭제금지)
                            start_point=(5,5),
                            rows=10, cols=8,  # 8자리 (시행일 6자 + 반코드 2자)
                            cell_size=(100.25, 60),
                            first_row_height=60,
                            first_row_gap=20,
                            roi_size=(30,23),
    '''

    
    # 학번 영역 처리
    id_area = get_omr_area_image(contours[1], gray_image, show_result=False)
    id_marking_area = extract_marking_area(id_area, 
                                         skip_x=(False, 0, 0),
                                         skip_y=(True, 150, 60000),
                                         show_result=False) 
    id_marking_result = analyze_omr_grid(id_marking_area,
                            start_point=(5,0),
                            rows=10, cols=8,
                             cell_size=(66.75, 40),
                            first_row_height=40,
                            first_row_gap=13,
                            roi_size=(25,15),
                            threshold=0.5,
                            show_result=False)
    student_code = convert_marking_to_number(id_marking_result, read_by_column=True)
    
    '''이전 파라미터 기록 (삭제금지)
                            start_point=(5,5),
                            rows=10, cols=10,
                            cell_size=(100, 60.5),
                            first_row_height=60,
                            first_row_gap=20,
                            roi_size=(30,23),
    '''

    # 이름 영역 처리
    name_area = get_omr_area_image(contours[2], gray_image, show_result=False)
    name_marking_area = extract_marking_area(name_area, 
                                           skip_x=(False, 0, 0),
                                           skip_y=(True, 100, 60000),
                                           show_result=False)
    name_marking_result = analyze_omr_grid(name_marking_area,
                            start_point=(17,1),
                            rows=21, cols=12,
                            cell_size=(33.35,40),
                            roi_size=(22,15),
                            threshold=0.5,
                            show_result=False)
    student_name = convert_marking_to_hangul(name_marking_result)
    ''' 이전 파라미터 기록 (삭제금지)
                            start_point=(24,2),
                            rows=21, cols=12,
                            cell_size=(50,60),
                            first_row_height=50,
                            first_row_gap=0,
                            roi_size=(33,20),
    '''
    
    # 답안 영역 처리
    answer_params = [  # 답안 영역 처리 파라미터 설정
        {
            'start_point': (4.5,8),
            'rows': 20, 'cols': 5,
            'cell_size': (66.6, 40),
            'roi_size': (20,15),
            'first_row_height': 55,
            'first_row_gap': 5,
            'skip_y_params': (True, 0, 45000),
            'skip_x_params': (True, 50, 150000),
            'start_number': 1,  # 1번부터 시작
            'threshold': 0.5
        },
    ]
    all_answers = [] # 답안 저장 객체
    question_numbers = [] # 문항 번호 저장 객체
    for i in range(2): # 답안 영역 2개 합치기  + 답안의 문항번호 생성
        area = get_omr_area_image(contours[i+3], gray_image, show_result=False)
        marking_area = extract_marking_area(area, skip_x=answer_params[0]['skip_x_params'], skip_y=answer_params[0]['skip_y_params'], show_result=False)
        marking_result = analyze_omr_grid(marking_area,
                                    start_point=answer_params[0]['start_point'],
                                    rows=answer_params[0]['rows'],
                                    cols=answer_params[0]['cols'],
                                    cell_size=answer_params[0]['cell_size'],
                                    first_row_height=answer_params[0]['first_row_height'],
                                    first_row_gap=answer_params[0]['first_row_gap'],
                                    roi_size=answer_params[0]['roi_size'],
                                    threshold=answer_params[0]['threshold'],
                                    show_result=False)
        
        answers = convert_marking_to_number(marking_result)
        all_answers.extend(list(answers))
        
        # 해당 영역의 문항 번호 생성
        start_num = answer_params[0]['start_number']
        question_numbers.extend(range(start_num, start_num + len(answers)))

    # 6개 열을 가진 df 생성
    result_df = pd.DataFrame({
        '시행일': exam_date,
        '반코드': class_code,
        '학번': student_code,
        '이름': student_name,
        '문항': question_numbers,
        '답': all_answers
    })
    
    # df로 부터 OMRResult 객체 생성 파라미터 추출
    student = Student.objects.get(student_code=result_df['학번'].iloc[0]) # result_df의 student_code를 통해 Student객체 찾는 로직)
    exam_date = f"20{result_df['시행일'].iloc[0]}"
    class_code = result_df['반코드'].iloc[0]
    answers = result_df.to_dict('records')
    answer_sheet = image_file
    
    # OMRResult 생성
    omr_result_obj = OMRResult.objects.create(
        student=student,
        exam_date=exam_date,
        class_code=class_code,
        answers=answers,
        answer_sheet=answer_sheet,
    )
    
    return omr_result_obj   

    



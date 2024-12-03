import cv2
import numpy as np
import pandas as pd
from omr_app.omr_processors.get_omr_area import get_coordinates_from_large_contours, get_omr_area_image, extract_marking_area
from omr_app.omr_processors.skew_correction import correct_skew
from omr_app.omr_processors.recognize_marking import recognize_marking
from omr_app.omr_processors.omr_data_processing import convert_marking_to_number, convert_marking_to_hangul, convert_pdf_to_image, create_student_dataframe

def process_omr_image(image):
    """OMR 이미지를 처리하여 DataFrame으로 결과를 반환하는 함수"""
    
    # 이미지 전처리
    corrected_image = correct_skew(image)
    gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
    contours = get_coordinates_from_large_contours(gray_image, 200000, show_result=False)
    
    # contours 개수 확인
    if len(contours) < 5:  # 필요한 최소 contour 개수를 5개로 수정
        raise ValueError(f"필요한 영역을 찾을 수 없습니다. (발견된 영역: {len(contours)}개, 필요한 영역: 5개)")
    
    # 시험 시행일과 반코드 영역 처리
    date_class_area = get_omr_area_image(contours[0], gray_image, show_result=False)
    date_class_marking_area = extract_marking_area(date_class_area, 
                                         skip_x=(False, 0, 0),
                                         skip_y=(True, 150, 60000),
                                         show_result=False)
    
    date_class_marking_result = recognize_marking(date_class_marking_area,
                            start_point=(5,1),
                            rows=10, cols=8,  # 8자리 (시행일 6자 + 반코드 2자)
                            cell_size=(66.75, 40),
                            first_row_height=40,
                            first_row_gap=13,
                            roi_size=(25,15),
                            threshold=0.5,
                            show_result=False)
    
    '''이전 파라미터 기록 (삭제금지)
                            start_point=(5,5),
                            rows=10, cols=8,  # 8자리 (시행일 6자 + 반코드 2자)
                            cell_size=(100.25, 60),
                            first_row_height=60,
                            first_row_gap=20,
                            roi_size=(30,23),
    '''
    
    date_class_number = convert_marking_to_number(date_class_marking_result, read_by_column=True)
    exam_date = date_class_number[:6]  # 앞 6자리는 시행일
    class_code = date_class_number[6:]  # 뒤 2자리는 반코드
    
    # 학번 영역 처리
    id_area = get_omr_area_image(contours[1], gray_image, show_result=False)
    id_marking_area = extract_marking_area(id_area, 
                                         skip_x=(False, 0, 0),
                                         skip_y=(True, 150, 60000),
                                         show_result=False)
    
    id_marking_result = recognize_marking(id_marking_area,
                            start_point=(5,0),
                            rows=10, cols=8,
                             cell_size=(66.75, 40),
                            first_row_height=40,
                            first_row_gap=13,
                            roi_size=(25,15),
                            threshold=0.5,
                            show_result=False)
    
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
    
    name_marking_result = recognize_marking(name_marking_area,
                            start_point=(17,1),
                            rows=21, cols=12,
                            cell_size=(33.35,40),
                            roi_size=(22,15),
                            threshold=0.5,
                            show_result=True)
    
    ''' 이전 파라미터 기록 (삭제금지)
                            start_point=(24,2),
                            rows=21, cols=12,
                            cell_size=(50,60),
                            first_row_height=50,
                            first_row_gap=0,
                            roi_size=(33,20),
    '''

    # 답안 영역 처리
    answer_params = [
        {
            'start_point': (4.5,17.5),
            'rows': 15, 'cols': 5,
            'cell_size': (99.9, 60),
            'first_row_height': 85.5,
            'first_row_gap': 6.5,
            'skip_params': (False, 0, 0),
            'start_number': 1  # 1번부터 시작
        },
        {
            'start_point': (4.5,15),
            'rows': 15, 'cols': 5,
            'cell_size': (99.9, 60),
            'first_row_height': 85.5,
            'first_row_gap': 6.5,
            'skip_params': (False, 0, 0),
            'start_number': 16  # 16번부터 시작
        }
    ]

    # 답안 처리 결과를 하나의 문자열로 합치기
    all_answers = []
    question_numbers = []  # 문항 번호를 저장할 리스트
    
    for i, params in enumerate(answer_params):
        area = get_omr_area_image(contours[i+3], gray_image, show_result=False)
        marking_area = extract_marking_area(area, skip_x=params['skip_params'])
        marking_result = recognize_marking(marking_area,
                                    start_point=params['start_point'],
                                    rows=params['rows'],
                                    cols=params['cols'],
                                    cell_size=params['cell_size'],
                                    first_row_height=params['first_row_height'],
                                    first_row_gap=params['first_row_gap'],
                                    roi_size=(33,18),
                                    threshold=0.3,
                                    show_result=False)
        
        answers = convert_marking_to_number(marking_result)
        all_answers.extend(list(answers))
        
        # 해당 영역의 문항 번호 생성
        start_num = params['start_number']
        question_numbers.extend(range(start_num, start_num + len(answers)))

    # DataFrame 생성 및 반환
    student_id = convert_marking_to_number(id_marking_result, read_by_column=True)
    student_name = convert_marking_to_hangul(name_marking_result)
    
    # 6개 열을 가진 최종 df 반환
    result_df = pd.DataFrame({
        '시행일': exam_date,
        '반코드': class_code,
        '학번': student_id,
        '이름': student_name,
        '문항': question_numbers,
        '답': all_answers
    })
    
    return result_df


import cv2
import numpy as np
import pandas as pd
from find_contours import find_large_contours
from get_area import get_omr_area_image, extract_marking_area
from skew_correction import correct_skew
from analyze_id_marking import analyze_fixed_id_marking
from convert_data import convert_marking_to_number, convert_marking_to_hangul, convert_pdf_to_image, create_student_dataframe

# 파일 경로
file_path = 'OMR_TEST.PDF'

# 파일 확장자 확인
if file_path.lower().endswith('.pdf'):
    # PDF 파일인 경우 이미지로 변환
    image = convert_pdf_to_image(file_path)
    if image is None:
        print("PDF 변환에 실패했습니다.")
        exit()
else:
    # PNG 등 이미지 파일인 경우 직접 로드
    image = cv2.imread(file_path)
    if image is None:
        print("이미지를 불러올 수 없습니다.")
        exit()

print(f"이미지 크기: {image.shape[1]} x {image.shape[0]} 픽셀")  # 너비 x 높이 순으로 출력

corrected_image = correct_skew(image)  # 기울임 보정
gray_image = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)  # 이미지를 그레이 스케일로(회색으로) 변환
contours = find_large_contours(gray_image, 200000, show_result=False)  # 보정된 회색 이미지와 설정된 최소 면적(100000)을 기준으로 주요 외곽선 추출


# 외곽선을 영역별로 매칭
id_contour = contours[0]      # 학번 영역
name_contour = contours[1]    # 이름 영역
answer_contours_1 = contours[2]  # 답안표시영역1
answer_contours_2 = contours[3]  # 답안표시영역2
answer_contours_3 = contours[4]  # 답안표시영역5

#학번 영역 처리
id_area = get_omr_area_image(id_contour, gray_image, show_result=False) # OMR 카드에서 해당 외곽선에 해당하는 영역만 이미지로 추출하는 함수
id_marking_area = extract_marking_area(id_area, 
                                     skip_x=(False, 0, 0),
                                     skip_y=(True, 170, 80000),
                                     show_result=False) # 순수 마킹 영역만 추출하는 함수

#마킹 결과 인식
id_marking_result = analyze_fixed_id_marking(id_marking_area,
                        start_point=(5,5), #시작 좌표
                        rows=10,cols=10, cell_size=(100.25, 60),  # 행x열 & 셀 크기
                        first_row_height=60, first_row_gap=20,  # 첫 행 높이 & 첫 행과 두 번째 행 사이의 여백
                        roi_size=(30,23),
                        show_result=False,    
                    )

print(id_marking_result)

id_result = convert_marking_to_number(id_marking_result, read_by_column=True)
print(id_result)


# 이름 영역 처리
name_area = get_omr_area_image(name_contour, gray_image, show_result=False) # OMR 카드에서 해당 외곽선에 해당하는 영역만 이미지로 추출하는 함수
name_marking_area = extract_marking_area(name_area, 
                                         skip_x=(False, 0, 0),
                                         skip_y=(True, 150, 80000),
                                         show_result=False) # 순수 마킹 영역만 추출하는 함수


name_marking_result = analyze_fixed_id_marking(name_marking_area,    # 실제 체크된 영역 인식 함수
                        start_point=(24,2), #시작 좌표(y,x) * OpenCV에서는 이미지 좌표계가 y,x 순임
                        rows=21,cols=12, cell_size=(50,60),  # 행x열 & 셀 크기(y,x)
                        first_row_height=50, first_row_gap=0,  # 첫 행 높이 & 첫 행과 두 번째 행 사이의 여백
                        roi_size=(33,20),
                        threshold=0.3,
                        show_result=False,    
                    )
name_result = convert_marking_to_hangul(name_marking_result)
print(name_result)


# 정답 영역1 처리
answer_1_area = get_omr_area_image(answer_contours_1, gray_image, show_result=False) # 외곽선 좌표를 받아 이미지 영역 추출
answer_1_marking_area = extract_marking_area(answer_1_area, show_result=False) # 이미지에서 순수 마킹 영역만 추출
answer_1_marking_result = analyze_fixed_id_marking(answer_1_marking_area, # 마킹 영역에 대해서 격자 및 ROI 설정하여 마킹된 부분을 인식
                        start_point=(4.5,17.5),
                        rows=15,cols=5, cell_size=(99.9, 60),
                        first_row_height=85.5, first_row_gap=6.5,
                        roi_size=(33,18),
                        threshold=0.3,
                        show_result=False,    
                    )
answer_1_result = convert_marking_to_number(answer_1_marking_result)
print(answer_1_result)



# 정답 영역2 처리
answer_2_area = get_omr_area_image(answer_contours_2, gray_image, show_result=False) # 외곽선 좌표를 받아 이미지 영역 추출
answer_2_marking_area = extract_marking_area(answer_2_area, show_result=False) # 이미지에서 순수 마킹 영역만 추출
answer_2_marking_result = analyze_fixed_id_marking(answer_2_marking_area, # 마킹 영역에 대해서 격자 및 ROI 설정하여 마킹된 부분을 인식
                        start_point=(4.5,15),
                        rows=15,cols=5, cell_size=(99.9, 60),
                        first_row_height=85.5, first_row_gap=6.5,
                        roi_size=(33,18),
                        threshold=0.3,
                        show_result=False,    
                    )
answer_2_result = convert_marking_to_number(answer_2_marking_result)
print(answer_2_result)  


## 정답 영역3 처리
# 외곽선 좌표를 받아 이미지 영역 추출  
answer_3_area = get_omr_area_image(answer_contours_3, gray_image, show_result=False) 
# 이미지에서 순수 마킹 영역만 추출
answer_3_marking_area = extract_marking_area(answer_3_area,
                                           skip_x=(True, 50, 100000),
                                           skip_y=(True, 50, 50000),
                                           show_result=False) 

# 마킹 영역에 대해서 격자 및 ROI 설정하여 마킹된 부분을 인식
answer_3_marking_result = analyze_fixed_id_marking(answer_3_marking_area, # 마킹 영역에 대해서 격자 및 ROI 설정하여 마킹된 부분을 인식
                        start_point=(4.5,15),
                        rows=5,cols=5, cell_size=(100, 60.5),
                        first_row_height=90, first_row_gap=5,
                        roi_size=(33,18),
                        threshold=0.3,
                        show_result=False,    
                    )
answer_3_result = convert_marking_to_number(answer_3_marking_result)
print(answer_3_result)



# DataFrame 생성
df = create_student_dataframe(id_result, name_result, answer_1_result, answer_2_result, answer_3_result)
print(df)


# exam_info = 시험날짜 6자리 + 반코드 2자리 총 8자리
# id_result = 학번 8자리로 변경할 예정

